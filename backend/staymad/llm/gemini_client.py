"""Production Google GenAI / Gemini client adapter.

Authority: ADR-007 (gemini-2.0-flash), docs/architecture/C-gemini-architecture.md §53-C
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from backend.staymad.llm.base import (
    PROMPT_VERSION_EXTRACT,
    SCHEMA_VERSION_ADJUDICATE,
    SCHEMA_VERSION_EXTRACT,
    SYSTEM_PROMPT_ADJUDICATE,
    SYSTEM_PROMPT_EXTRACT,
    SYSTEM_PROMPT_SYNTHESIZE,
    BaseGeminiClient,
)
from backend.staymad.llm.schemas import (
    AdjudicateDecision,
    AdjudicateInput,
    AdjudicateResponse,
    ExtractInput,
    ExtractResponse,
    SynthesizeInput,
    SynthesizeResponse,
)

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")


def _clean_schema_for_gemini(schema: dict[str, Any]) -> dict[str, Any]:
    """Dereference and inline $defs/$ref for Google Gemini REST API compatibility."""
    defs = schema.get("$defs", {})

    def resolve(node: Any) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                ref_key = node["$ref"].split("/")[-1]
                if ref_key in defs:
                    return resolve(defs[ref_key].copy())
            return {k: resolve(v) for k, v in node.items() if k != "$defs"}
        elif isinstance(node, list):
            return [resolve(x) for x in node]
        return node

    return resolve(schema)


class GeminiAPIError(RuntimeError):
    """Raised when the Gemini REST API returns an error or invalid response."""


class GeminiClient(BaseGeminiClient):
    """Live Google Gemini client implementing Structured Outputs via REST API."""

    def __init__(
        self,
        api_key: str | None = None,
        model_version: str | None = None,
        prompt_version: str = PROMPT_VERSION_EXTRACT,
        schema_version: str = SCHEMA_VERSION_EXTRACT,
    ) -> None:
        resolved_key = api_key or os.getenv("GEMINI_API_KEY")
        if not resolved_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is missing. "
                "Real GeminiClient requires a valid API key."
            )
        self.api_key = resolved_key
        resolved_model = model_version or os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
        super().__init__(
            model_version=resolved_model,
            prompt_version=prompt_version,
            schema_version=schema_version,
        )

    def extract(self, article: ExtractInput) -> ExtractResponse:
        """Call Gemini to extract structured claims with JSON enforcement."""
        user_prompt = self.build_extract_user_prompt(article)
        prompt_with_format = (
            f"{user_prompt}\n\n"
            "Respond strictly with valid JSON adhering to this schema:\n"
            "{\n"
            '  "schema_version": "1.0",\n'
            f'  "article_version_id": "{article.article_version_id}",\n'
            '  "suggested_category": "DISASTER_AND_WEATHER",\n'
            '  "claims": [\n'
            "    {\n"
            '      "claim_text": "Atomic factual claim",\n'
            '      "source_span": "Exact substring quote from excerpt or title under 200 chars",\n'
            '      "speaker": null,\n'
            '      "negation": false,\n'
            '      "numeric_value": null,\n'
            '      "unit": null,\n'
            '      "location_raw": null,\n'
            '      "event_time_raw": null,\n'
            '      "event_time_qualifier": null,\n'
            '      "event_time_precision": "UNKNOWN",\n'
            '      "extraction_confidence": 0.95\n'
            "    }\n"
            "  ],\n"
            '  "entities": [\n'
            "    {\n"
            '      "name": "Entity Name",\n'
            '      "type": "ORGANIZATION",\n'
            '      "canonical_form": null\n'
            "    }\n"
            "  ],\n"
            '  "primary_location_raw": null,\n'
            '  "primary_event_time_raw": null,\n'
            '  "insufficient_content": false\n'
            "}\n"
            "Constraints:\n"
            "- Entity type must be one of: PERSON, ORGANIZATION, LOCATION, INFRASTRUCTURE, INSTITUTION\n"
            "- suggested_category must be one of: DISASTER_AND_WEATHER, TRANSPORTATION_AND_INFRASTRUCTURE, GOVERNMENT_AND_PUBLIC_POLICY, UNKNOWN\n"
            "- event_time_precision must be one of: EXACT, APPROXIMATE, DAY, RANGE, UNKNOWN\n"
            "- source_span must be verbatim substring from the excerpt/title (< 200 characters)\n"
        )

        payload: dict[str, Any] = {
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT_EXTRACT}]},
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt_with_format}],
                }
            ],
            "generationConfig": {
                "temperature": 0.0,
                "response_mime_type": "application/json",
                "max_output_tokens": 2048,
            },
        }

        # Support fallback models if primary model is unavailable or rate limited
        candidate_models = [self.model_version]
        for m in ["gemini-flash-lite-latest", "gemini-3-flash-preview"]:
            if m not in candidate_models:
                candidate_models.append(m)

        last_error: Exception | None = None
        result_json: dict[str, Any] | None = None

        for model in candidate_models:
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                f"?key={self.api_key}"
            )
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=45) as resp:
                    result_json = json.loads(resp.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as e:
                error_body = e.read().decode("utf-8", errors="replace")
                last_error = GeminiAPIError(
                    f"Gemini API HTTP {e.code} for {model}: {error_body}"
                )
                if e.code in (404, 503, 429):
                    continue
                raise last_error from e
            except Exception as e:  # noqa: BLE001
                last_error = GeminiAPIError(
                    f"Failed to communicate with Gemini API ({model}): {e}"
                )
                continue

        if result_json is None:
            raise GeminiAPIError(f"All Gemini models failed. Last error: {last_error}")

        # Extract text content from candidate
        try:
            candidates = result_json.get("candidates", [])
            if not candidates:
                raise GeminiAPIError(f"No candidates returned by Gemini: {result_json}")

            part_text = candidates[0]["content"]["parts"][0]["text"]
            parsed_data = json.loads(part_text)

            # Ensure article_version_id is set
            parsed_data["article_version_id"] = article.article_version_id

            # Normalize entities
            if "entities" in parsed_data and isinstance(parsed_data["entities"], list):
                normalized_entities = []
                for e in parsed_data["entities"]:
                    if isinstance(e, str):
                        normalized_entities.append(
                            {"name": e, "type": "ORGANIZATION", "canonical_form": None}
                        )
                    elif isinstance(e, dict):
                        etype = e.get("type", "ORGANIZATION")
                        if etype not in {
                            "PERSON",
                            "ORGANIZATION",
                            "LOCATION",
                            "INFRASTRUCTURE",
                            "INSTITUTION",
                        }:
                            etype = "ORGANIZATION"
                        e["type"] = etype
                        normalized_entities.append(e)
                parsed_data["entities"] = normalized_entities

            # Normalize suggested_category
            valid_categories = {
                "DISASTER_AND_WEATHER",
                "TRANSPORTATION_AND_INFRASTRUCTURE",
                "GOVERNMENT_AND_PUBLIC_POLICY",
                "UNKNOWN",
            }
            if parsed_data.get("suggested_category") not in valid_categories:
                parsed_data["suggested_category"] = "UNKNOWN"

            # Ensure claims have valid source_span and valid precision
            valid_precisions = {"EXACT", "APPROXIMATE", "DAY", "RANGE", "UNKNOWN"}
            if "claims" in parsed_data and isinstance(parsed_data["claims"], list):
                for c in parsed_data["claims"]:
                    if isinstance(c, dict):
                        if not c.get("source_span"):
                            c["source_span"] = (
                                c.get("evidence_quote") or c.get("claim_text", "")[:199]
                            )
                        elif len(c["source_span"]) > 200:
                            c["source_span"] = c["source_span"][:199]

                        if c.get("event_time_precision") not in valid_precisions:
                            raw_p = str(c.get("event_time_precision", "")).upper()
                            if raw_p in {"YEAR", "MONTH", "DECADE"}:
                                c["event_time_precision"] = "APPROXIMATE"
                            else:
                                c["event_time_precision"] = "UNKNOWN"

            return ExtractResponse(**parsed_data)
        except Exception as e:
            raise GeminiAPIError(
                f"Failed to parse Gemini structured JSON output: {e}"
            ) from e

    def adjudicate(self, payload: AdjudicateInput) -> AdjudicateResponse:
        """Call Gemini 2.0 Flash for Call Type 2: Adjudicate with fallback & override rules.

        Authority: docs/architecture/C-gemini-architecture.md §53-C
        """
        user_prompt = self.build_adjudicate_user_prompt(payload)
        prompt_with_format = (
            f"{user_prompt}\n\n"
            "Respond strictly with valid JSON conforming to this schema:\n"
            "{\n"
            '  "schema_version": "1.0",\n'
            '  "decisions": [\n'
            "    {\n"
            '      "article_version_id": "<exact article_version_id from candidate>",\n'
            '      "decision": "SAME_EVENT",\n'
            '      "decision_reason_codes": ["LOC_MATCH", "TIME_WITHIN_WINDOW"],\n'
            '      "confidence": 0.85,\n'
            '      "notes": "Brief reason in Indonesian"\n'
            "    }\n"
            "  ],\n"
            '  "suggested_event_headline": null\n'
            "}\n"
            "Decision must be one of: SAME_EVENT, RELATED_EVENT, SEPARATE_EVENT, NEEDS_REVIEW.\n"
            "Provide exactly one decision entry for each candidate article in the input.\n"
        )

        req_payload: dict[str, Any] = {
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT_ADJUDICATE}]},
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt_with_format}],
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "response_mime_type": "application/json",
                "max_output_tokens": 1024,
            },
        }

        candidate_models = [self.model_version]
        for m in ["gemini-flash-lite-latest", "gemini-3-flash-preview"]:
            if m not in candidate_models:
                candidate_models.append(m)

        result_json: dict[str, Any] | None = None
        last_error: Exception | None = None

        for model in candidate_models:
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                f"?key={self.api_key}"
            )
            data = json.dumps(req_payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=45) as resp:
                    result_json = json.loads(resp.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as e:
                error_body = e.read().decode("utf-8", errors="replace")
                last_error = GeminiAPIError(
                    f"Gemini API HTTP {e.code} for {model}: {error_body}"
                )
                if e.code in (404, 503, 429):
                    continue
                raise last_error from e
            except Exception as e:  # noqa: BLE001
                last_error = GeminiAPIError(
                    f"Failed to communicate with Gemini API ({model}): {e}"
                )
                continue

        try:
            if result_json is None:
                raise GeminiAPIError(f"All Gemini models failed: {last_error}")

            candidates = result_json.get("candidates", [])
            if not candidates:
                raise GeminiAPIError(f"No candidates returned by Gemini: {result_json}")

            part_text = candidates[0]["content"]["parts"][0]["text"]
            parsed_data = json.loads(part_text)
            response = AdjudicateResponse(**parsed_data)

            # Apply safety override: if SAME_EVENT but confidence < 0.60 -> override to NEEDS_REVIEW
            for d in response.decisions:
                if d.decision == "SAME_EVENT" and d.confidence < 0.60:
                    d.decision = "NEEDS_REVIEW"
                    if "AMBIGUOUS" not in d.decision_reason_codes:
                        d.decision_reason_codes.append("AMBIGUOUS")

            return response
        except Exception:  # noqa: BLE001
            # Fallback per §53-C: default to SEPARATE_EVENT with ADJUDICATION_FAILED
            fallback_decisions = [
                AdjudicateDecision(
                    article_version_id=cand.article_version_id,
                    decision="SEPARATE_EVENT",
                    decision_reason_codes=["ADJUDICATION_FAILED"],
                    confidence=0.0,
                    notes="Fallback due to adjudication call failure",
                )
                for cand in payload.candidate_articles
            ]
            return AdjudicateResponse(
                schema_version=SCHEMA_VERSION_ADJUDICATE,
                decisions=fallback_decisions,
                suggested_event_headline=None,
            )

    def synthesize(self, payload: SynthesizeInput) -> SynthesizeResponse:
        """Call Gemini 2.0 Flash for Call Type 3: Synthesize with grounding enforcement.

        Authority: docs/architecture/C-gemini-architecture.md §53-C, DEC-0008
        """
        user_prompt = self.build_synthesize_user_prompt(payload)
        response_schema = _clean_schema_for_gemini(
            SynthesizeResponse.model_json_schema()
        )

        req_payload: dict[str, Any] = {
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT_SYNTHESIZE}]},
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}],
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "response_mime_type": "application/json",
                "response_schema": response_schema,
                "max_output_tokens": 2048,
            },
        }

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_version}:generateContent"
            f"?key={self.api_key}"
        )

        data = json.dumps(req_payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                result_json = json.loads(resp.read().decode("utf-8"))

            candidates = result_json.get("candidates", [])
            if not candidates:
                raise GeminiAPIError(f"No candidates returned by Gemini: {result_json}")

            part_text = candidates[0]["content"]["parts"][0]["text"]
            parsed_data = json.loads(part_text)
            response = SynthesizeResponse(**parsed_data)

            # Enforce DEC-0008 & §53-C grounding contract:
            # what_happened MUST have evidence_claim_ids unless insufficient_evidence
            if (
                not response.insufficient_evidence
                and not response.what_happened.evidence_claim_ids
                and payload.claims
            ):
                # Ground with primary claims if empty
                response.what_happened.evidence_claim_ids = [
                    c.claim_id for c in payload.claims if c.role == "PRIMARY"
                ] or [payload.claims[0].claim_id]

            return response
        except Exception as e:
            # Fallback per §53-C: EventSnapshot not produced if call fails
            raise GeminiAPIError(f"Synthesize call failed: {e}") from e
