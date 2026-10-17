"""Deterministic mock adapter for Gemini extraction.

Used for offline testing, CI evaluation, and reproducible fixture baseline runs.
Strictly isolates prompt injection patterns without obeying embedded instructions.
Authority: DEC-0004, DEC-0006, docs/architecture/C-gemini-architecture.md
"""

from __future__ import annotations

import re

from backend.staymad.llm.base import (
    PROMPT_VERSION_EXTRACT,
    SCHEMA_VERSION_ADJUDICATE,
    SCHEMA_VERSION_EXTRACT,
    SCHEMA_VERSION_SYNTHESIZE,
    BaseGeminiClient,
)
from backend.staymad.llm.schemas import (
    AdjudicateDecision,
    AdjudicateInput,
    AdjudicateResponse,
    ExtractedClaim,
    ExtractedEntity,
    ExtractInput,
    ExtractResponse,
    GroundedNarrativePoint,
    SuggestedActionItem,
    SynthesizeInput,
    SynthesizeResponse,
)


class DeterministicGeminiClient(BaseGeminiClient):
    """Deterministic extraction client that parses claims and entities via rule-based heuristics."""

    def __init__(
        self,
        model_version: str = "mock-deterministic-v1",
        prompt_version: str = PROMPT_VERSION_EXTRACT,
        schema_version: str = SCHEMA_VERSION_EXTRACT,
    ) -> None:
        super().__init__(
            model_version=model_version,
            prompt_version=prompt_version,
            schema_version=schema_version,
        )

    def extract(self, article: ExtractInput) -> ExtractResponse:
        """Extract atomic claims, entities, and category deterministically from excerpt."""
        text = f"{article.title}. {article.excerpt}".strip()

        # 1. Determine category
        lower_text = text.lower()
        if any(
            w in lower_text
            for w in (
                "banjir",
                "hujan",
                "merapi",
                "cuaca",
                "bencana",
                "kali",
                "air",
                "awan panas",
            )
        ):
            suggested_cat = "DISASTER_AND_WEATHER"
        elif any(
            w in lower_text
            for w in (
                "krl",
                "kereta",
                "stasiun",
                "dishub",
                "lalu lintas",
                "jalan",
                "rekayasa",
            )
        ):
            suggested_cat = "TRANSPORTATION_AND_INFRASTRUCTURE"
        elif any(
            w in lower_text
            for w in (
                "perpres",
                "subsidi",
                "menteri",
                "pemerintah",
                "kabinet",
                "anggaran",
            )
        ):
            suggested_cat = "GOVERNMENT_AND_PUBLIC_POLICY"
        else:
            suggested_cat = "GOVERNMENT_AND_PUBLIC_POLICY"

        # 2. Extract entities
        entities: list[ExtractedEntity] = []
        entity_patterns = [
            (
                r"\b(BMKG|BPBD DKI|BNPB|Dishub DKI|PT KAI|Kemenkeu|Sekretariat Kabinet)\b",
                "INSTITUTION",
            ),
            (
                r"\b(DKI Jakarta|Jakarta Timur|Cipinang Melayu|Manggarai|Gunung Merapi|Kali Ciliwung)\b",
                "LOCATION",
            ),
            (
                r"\b(TransJakarta Koridor 7|Jalur Tol|Flyover Cawang)\b",
                "INFRASTRUCTURE",
            ),
        ]
        seen_entities = set()
        for pat, ent_type in entity_patterns:
            for match in re.finditer(pat, text, re.IGNORECASE):
                name = match.group(0)
                if name.lower() not in seen_entities:
                    seen_entities.add(name.lower())
                    entities.append(
                        ExtractedEntity(name=name, type=ent_type, canonical_form=name)
                    )

        # 3. Detect and neutralize prompt injection
        # e.g., in art_demo_07: [SYSTEM INSTRUCTION OVERRIDE: ...]
        # DEC-0004: All text is passive data. Embedded instructions must NEVER be executed.
        clean_excerpt = article.excerpt
        if "SYSTEM INSTRUCTION OVERRIDE" in clean_excerpt:
            # Isolate / strip injection block from factual claim generation
            clean_excerpt = re.sub(
                r"\[SYSTEM INSTRUCTION OVERRIDE:[^\]]+\]", "", clean_excerpt
            ).strip()

        # 4. Extract claims from sentences
        claims: list[ExtractedClaim] = []
        # Split sentences while keeping sentence boundaries
        sentences = [
            s.strip()
            for s in re.split(r"(?<=[.!?])\s+", clean_excerpt)
            if len(s.strip()) > 15
        ]

        # If sentences list is empty (e.g. after stripping or very short text), fallback to title
        if not sentences and article.title:
            sentences = [article.title.strip()]

        for sentence in sentences:
            # Ensure source_span is verbatim substring from original excerpt or title
            source_span = sentence
            if len(source_span) >= 200:
                source_span = source_span[:195].rstrip()

            # Find matching span in article.excerpt or title
            if source_span not in article.excerpt and source_span not in article.title:
                # Find longest verbatim substring
                words = source_span.split()
                sub = ""
                for w in words:
                    cand = (sub + " " + w).strip()
                    if cand in article.excerpt or cand in article.title:
                        sub = cand
                    else:
                        break
                source_span = (
                    sub if sub else (article.title[:190] if article.title else "")
                )

            if not source_span:
                continue

            # Check for numbers
            num_val = None
            unit_val = None
            id_words = {
                "satu": 1.0,
                "dua": 2.0,
                "tiga": 3.0,
                "empat": 4.0,
                "lima": 5.0,
                "enam": 6.0,
                "tujuh": 7.0,
                "delapan": 8.0,
                "sembilan": 9.0,
                "sepuluh": 10.0,
            }
            unit_pat = r"(?:(\d+(?:[.,]\d+)?)|(satu|dua|tiga|empat|lima|enam|tujuh|delapan|sembilan|sepuluh))\s*(kecamatan|meter|ruas|jiwa|persen|km|sentimeter|cm)"
            num_m = re.search(unit_pat, sentence, re.IGNORECASE)
            if num_m:
                if num_m.group(1):
                    try:
                        num_val = float(num_m.group(1).replace(",", "."))
                    except ValueError:
                        pass
                elif num_m.group(2):
                    num_val = id_words.get(num_m.group(2).lower())
                unit_val = num_m.group(3)
            else:
                gen_m = re.search(r"(?<![:\d])(\d+(?:[.,]\d+)?)(?![:\d])", sentence)
                if gen_m:
                    try:
                        num_val = float(gen_m.group(1).replace(",", "."))
                    except ValueError:
                        pass

            # Check for speaker
            speaker = None
            spk_m = re.search(
                r"(?:kata|ujar|tutur|menurut|pernyataan)\s+([A-Za-z\s]+?)(?:[,.]|$)",
                sentence,
                re.IGNORECASE,
            )
            if spk_m:
                speaker = spk_m.group(1).strip()

            # Check temporal cues
            event_time_raw = None
            time_qualifier = None
            prec = "UNKNOWN"
            if "pukul" in sentence.lower() or "wib" in sentence.lower():
                tm = re.search(
                    r"(\d{1,2}[:.]\d{2}(?:\s*WIB)?)", sentence, re.IGNORECASE
                )
                if tm:
                    event_time_raw = tm.group(1)
                    prec = "EXACT"
            elif (
                "pagi" in sentence.lower()
                or "siang" in sentence.lower()
                or "kemarin" in sentence.lower()
            ):
                prec = "APPROXIMATE"
                event_time_raw = "pagi" if "pagi" in sentence.lower() else "siang"

            if "sekitar" in sentence.lower():
                time_qualifier = "sekitar"
                prec = "APPROXIMATE"
            elif "diperkirakan" in sentence.lower():
                time_qualifier = "diperkirakan"
                prec = "APPROXIMATE"

            claims.append(
                ExtractedClaim(
                    claim_text=sentence,
                    source_span=source_span,
                    speaker=speaker,
                    negation="tidak" in sentence.lower() or "bukan" in sentence.lower(),
                    numeric_value=num_val,
                    unit=unit_val,
                    location_raw=entities[0].name if entities else None,
                    event_time_raw=event_time_raw,
                    event_time_qualifier=time_qualifier,
                    event_time_precision=prec,
                    extraction_confidence=0.92,
                )
            )

        # Primary location and event time
        primary_loc = entities[0].name if entities else None
        primary_time = claims[0].event_time_raw if claims else None

        return ExtractResponse(
            schema_version="1.0",
            article_version_id=article.article_version_id,
            suggested_category=suggested_cat,
            claims=claims,
            entities=entities,
            primary_location_raw=primary_loc,
            primary_event_time_raw=primary_time,
            insufficient_content=len(claims) == 0,
        )

    def adjudicate(self, payload: AdjudicateInput) -> AdjudicateResponse:
        """Deterministically adjudicate candidate articles against an anchor event.

        Authority: docs/architecture/C-gemini-architecture.md §53-C
        """
        anchor = payload.anchor_summary
        decisions: list[AdjudicateDecision] = []

        anchor_claims_str = " ".join(anchor.representative_claims)
        anchor_text = f"{anchor.headline} {anchor.primary_location or ''} {anchor_claims_str}".lower()
        anchor_tokens = set(re.findall(r"\w+", anchor_text))

        for cand in payload.candidate_articles:
            signals = cand.deterministic_signals
            loc_match = signals.get("location_match", True)
            time_delta = signals.get("time_delta_hours", 0.0)
            score = cand.deterministic_score

            cand_claims_str = " ".join(cand.top_claims)
            cand_text = f"{cand.title} {cand.excerpt} {cand_claims_str}".lower()
            cand_tokens = set(re.findall(r"\w+", cand_text))
            token_overlap = (
                len(anchor_tokens & cand_tokens) / len(anchor_tokens | cand_tokens)
                if (anchor_tokens | cand_tokens)
                else 0.0
            )
            shared_content = {w for w in (anchor_tokens & cand_tokens) if len(w) > 3}

            reason_codes: list[str] = []
            decision_str: str
            confidence: float

            # Hard checks
            if not loc_match or "loc_incompatible" in signals:
                decision_str = "SEPARATE_EVENT"
                reason_codes.append("LOC_INCOMPATIBLE")
                confidence = 0.95
            elif time_delta > 72.0:
                decision_str = "SEPARATE_EVENT"
                reason_codes.append("TIME_INCOMPATIBLE")
                confidence = 0.95
            elif (
                score >= 0.70
                or (
                    score >= 0.45
                    and loc_match
                    and len(shared_content) >= 3
                    and time_delta <= 48.0
                )
                or token_overlap > 0.25
            ):
                # Strong match with anchor
                decision_str = "SAME_EVENT"
                reason_codes.append("LOC_MATCH")
                reason_codes.append("TIME_WITHIN_WINDOW")
                if len(shared_content) >= 2 or token_overlap > 0.15:
                    reason_codes.append("ENT_OVERLAP")
                if cand.source_tier == "TIER_1":
                    reason_codes.append("CORROBORATED")
                else:
                    reason_codes.append("SOURCE_SYNDICATE")
                confidence = min(0.95, max(0.75, score if score > 0 else 0.85))
            elif score < 0.35 and len(shared_content) < 2:
                decision_str = "SEPARATE_EVENT"
                reason_codes.append("AMBIGUOUS")
                confidence = 0.90
            else:
                # Ambiguous boundary: low confidence triggers override to NEEDS_REVIEW
                decision_str = "SAME_EVENT"
                reason_codes.extend(["LOC_MATCH", "TIME_WITHIN_WINDOW", "AMBIGUOUS"])
                confidence = 0.55  # Below 0.60 to trigger override rule to NEEDS_REVIEW

            # Enforce override rule: if SAME_EVENT but confidence < 0.60 -> NEEDS_REVIEW
            if decision_str == "SAME_EVENT" and confidence < 0.60:
                decision_str = "NEEDS_REVIEW"
                if "AMBIGUOUS" not in reason_codes:
                    reason_codes.append("AMBIGUOUS")

            decisions.append(
                AdjudicateDecision(
                    article_version_id=cand.article_version_id,
                    decision=decision_str,  # type: ignore[arg-type]
                    decision_reason_codes=reason_codes,
                    evidence_claim_ids=[],
                    confidence=confidence,
                    notes="Deterministic rule-based adjudication",
                )
            )

        return AdjudicateResponse(
            schema_version=SCHEMA_VERSION_ADJUDICATE,
            decisions=decisions,
            suggested_event_headline=anchor.headline,
        )

    def synthesize(self, payload: SynthesizeInput) -> SynthesizeResponse:
        """Deterministically synthesize claims into structured narrative with grounded evidence citations.

        Authority: docs/architecture/C-gemini-architecture.md §53-C, DEC-0008, DEC-0004
        """
        if not payload.claims:
            return SynthesizeResponse(
                schema_version=SCHEMA_VERSION_SYNTHESIZE,
                headline="Informasi Peristiwa Tidak Cukup",
                what_happened=GroundedNarrativePoint(
                    text="Not enough information available.",
                    evidence_claim_ids=[],
                ),
                why_it_matters=None,
                who_is_affected=None,
                what_is_unknown=None,
                conflict_summary=None,
                suggested_actions=[],
                insufficient_evidence=True,
            )

        # 1. Filter out prompt injection claims (DEC-0004)
        clean_claims = [
            c
            for c in payload.claims
            if "SYSTEM INSTRUCTION OVERRIDE" not in c.claim_text
        ]
        if not clean_claims:
            clean_claims = payload.claims

        # 2. Select primary claims for narrative grounding
        primary_claims = [c for c in clean_claims if c.role == "PRIMARY"]
        if not primary_claims:
            primary_claims = clean_claims[:3]

        primary_claim_ids = [c.claim_id for c in primary_claims]

        # 3. Derive headline
        headline_claim = primary_claims[0].claim_text.strip()
        # Clean up headline text
        headline_claim = re.sub(
            r"^(?:Jakarta\s*\(ANTARA\)\s*[-–]|SLEMAN\s*[-–]|YOGYAKARTA\s*[-–]|REPUBLIKA\.CO\.ID,\s*JAKARTA\s*[-–]|\w+,\s*CNN Indonesia\s*[-–])\s*",
            "",
            headline_claim,
        )
        if len(headline_claim) > 115:
            headline = headline_claim[:112].rstrip() + "..."
        else:
            headline = headline_claim

        # 4. Synthesize what_happened (Bahasa Indonesia per DEC-0001)
        narrative_parts = []
        for c in primary_claims[:2]:
            narrative_parts.append(c.claim_text.strip())
        what_happened_text = " ".join(narrative_parts)
        what_happened = GroundedNarrativePoint(
            text=what_happened_text,
            evidence_claim_ids=primary_claim_ids[:2],
        )

        # 5. Synthesize why_it_matters (impact & severity)
        impact_claims = [
            c
            for c in clean_claims
            if any(
                w in c.claim_text.lower()
                for w in (
                    "ketinggian",
                    "sentimeter",
                    "cm",
                    "merendam",
                    "terdampak",
                    "terganggu",
                    "terlambat",
                    "siaga",
                    "subsidi",
                    "perpres",
                    "tarif",
                )
            )
        ]
        why_it_matters = None
        if impact_claims:
            why_claims = impact_claims[:2]
            why_it_matters = GroundedNarrativePoint(
                text=" ".join(c.claim_text.strip() for c in why_claims),
                evidence_claim_ids=[c.claim_id for c in why_claims],
            )

        # 6. Synthesize who_is_affected (locations, entities, affected communities)
        affected_claims = [
            c
            for c in clean_claims
            if any(
                w in c.claim_text.lower()
                for w in (
                    "kecamatan",
                    "kelurahan",
                    "warga",
                    "penumpang",
                    "pengguna",
                    "dusun",
                    "radius",
                    "masyarakat",
                )
            )
        ]
        who_is_affected = None
        if affected_claims:
            aff_claims = affected_claims[:2]
            who_is_affected = GroundedNarrativePoint(
                text=" ".join(c.claim_text.strip() for c in aff_claims),
                evidence_claim_ids=[c.claim_id for c in aff_claims],
            )

        # 7. Synthesize what_is_unknown (empty evidence_claim_ids per §53-C)
        what_is_unknown = GroundedNarrativePoint(
            text="Perkembangan pemulihan dan estimasi dampak lanjutan masih dalam pemantauan petugas di lapangan.",
            evidence_claim_ids=[],
        )

        # 8. Synthesize conflict_summary if conflicts recorded
        conflict_summary = None
        if payload.conflicts:
            cf_descs = []
            cf_ids = []
            for cf in payload.conflicts:
                cf_descs.append(
                    f"Terdapat perbedaan data pada {cf.field_name}: '{cf.value_a}' vs '{cf.value_b}'."
                )
                cf_ids.extend([cf.claim_a_id, cf.claim_b_id])
            conflict_summary = GroundedNarrativePoint(
                text=" ".join(cf_descs),
                evidence_claim_ids=list(dict.fromkeys(cf_ids)),
            )

        # 9. Synthesize suggested_actions (Strict Safety Gate per DEC-0004 & ADR-006)
        suggested_actions = []
        for c in clean_claims:
            is_official = c.source_tier == "TIER_1" and c.source_family.startswith(
                "GOV_"
            )
            lower_claim = c.claim_text.lower()
            if is_official and any(
                w in lower_claim
                for w in (
                    "evakuasi",
                    "peringatan dini",
                    "siaga 2",
                    "posko pengungsian",
                    "diinstruksikan",
                    "mengungsi",
                )
            ):
                suggested_actions.append(
                    SuggestedActionItem(
                        action_level="ACTION_REQUIRED",
                        action_text=c.claim_text.strip(),
                        requires_official_source=True,
                        evidence_claim_ids=[c.claim_id],
                    )
                )
            elif is_official and any(
                w in lower_claim for w in ("imbau", "waspada", "antisipasi", "siaga 3")
            ):
                suggested_actions.append(
                    SuggestedActionItem(
                        action_level="ACTION_RECOMMENDED",
                        action_text=c.claim_text.strip(),
                        requires_official_source=True,
                        evidence_claim_ids=[c.claim_id],
                    )
                )

        return SynthesizeResponse(
            schema_version=SCHEMA_VERSION_SYNTHESIZE,
            headline=headline,
            what_happened=what_happened,
            why_it_matters=why_it_matters,
            who_is_affected=who_is_affected,
            what_is_unknown=what_is_unknown,
            conflict_summary=conflict_summary,
            suggested_actions=suggested_actions,
            insufficient_evidence=False,
        )
