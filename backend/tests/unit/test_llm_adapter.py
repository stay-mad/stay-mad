"""Unit tests for Gemini Client Adapter and DEC-0006 Production Startup Guard.

Authority: DEC-0006, ADR-007
"""

from __future__ import annotations

import pytest

from backend.staymad.llm.deterministic_client import DeterministicGeminiClient
from backend.staymad.llm.factory import (
    StartupConfigurationError,
    get_llm_client,
    validate_production_startup,
)
from backend.staymad.llm.gemini_client import GeminiClient
from backend.staymad.llm.schemas import ExtractInput


def test_factory_returns_deterministic_adapter_in_dev_mode(monkeypatch):
    monkeypatch.delenv("STAYMAD_ENV", raising=False)
    monkeypatch.setenv("DATA_MODE", "DEMO")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    client = get_llm_client(data_mode="DEMO", use_mock=True)
    assert isinstance(client, DeterministicGeminiClient)


def test_production_startup_fails_if_fixture_active(monkeypatch):
    monkeypatch.setenv("STAYMAD_ENV", "production")
    monkeypatch.setenv("DATA_MODE", "LIVE")
    monkeypatch.setenv("GEMINI_API_KEY", "test-api-key")

    with pytest.raises(StartupConfigurationError) as exc_info:
        validate_production_startup(data_mode="LIVE", use_fixture=True)
    assert "Fixture/mock adapter is strictly forbidden" in str(exc_info.value)


def test_production_startup_fails_if_api_key_missing(monkeypatch):
    monkeypatch.setenv("STAYMAD_ENV", "production")
    monkeypatch.setenv("DATA_MODE", "LIVE")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(StartupConfigurationError) as exc_info:
        validate_production_startup(data_mode="LIVE", use_fixture=False)
    assert "requires a valid GEMINI_API_KEY" in str(exc_info.value)


def test_production_startup_succeeds_with_api_key(monkeypatch):
    monkeypatch.setenv("STAYMAD_ENV", "production")
    monkeypatch.setenv("DATA_MODE", "LIVE")
    monkeypatch.setenv("GEMINI_API_KEY", "valid-gemini-key")

    client = get_llm_client(data_mode="LIVE", use_mock=False)
    assert isinstance(client, GeminiClient)
    assert client.api_key == "valid-gemini-key"


def test_passive_data_prompt_containment():
    client = DeterministicGeminiClient()
    input_payload = ExtractInput(
        article_version_id="uuid-1",
        source_id="src-1",
        source_tier="TIER_1",
        source_family="GOV_BMKG",
        title="Peringatan Dini Cuaca",
        excerpt="Hujan lebat disertai kilat diprakirakan terjadi di Jakarta.",
        source_url="https://bmkg.go.id/cuaca",
    )
    user_prompt = client.build_extract_user_prompt(input_payload)
    assert "<article_content>" in user_prompt
    assert "</article_content>" in user_prompt
    assert "Peringatan Dini Cuaca" in user_prompt


def test_cache_key_determinism():
    client = DeterministicGeminiClient()
    art_id = "test-article-version-uuid"
    key1 = client.compute_extract_cache_key(art_id)
    key2 = client.compute_extract_cache_key(art_id)
    assert key1 == key2
    assert len(key1) == 64  # SHA-256
