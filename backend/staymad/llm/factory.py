"""LLM Client Factory and Production Startup Guard.

Authority: DEC-0006, ADR-007
"""

from __future__ import annotations

import os

from backend.staymad.db.models.enums import DataMode
from backend.staymad.llm.base import BaseGeminiClient
from backend.staymad.llm.deterministic_client import DeterministicGeminiClient
from backend.staymad.llm.gemini_client import GeminiClient


class StartupConfigurationError(RuntimeError):
    """Raised when environment or adapter configuration violates production safety rules."""


def validate_production_startup(
    data_mode: DataMode | str | None = None, use_fixture: bool = False
) -> None:
    """Enforce DEC-0006 startup guard rules.

    In production mode:
    1. Fixture / mock adapter MUST NOT be active.
    2. GEMINI_API_KEY MUST NOT be empty or missing.
    """
    env = os.getenv("STAYMAD_ENV", "").lower()
    norm_mode = str(data_mode or os.getenv("DATA_MODE", "DEMO")).upper()
    is_prod = env == "production" or norm_mode == DataMode.LIVE.value

    if is_prod:
        if use_fixture:
            raise StartupConfigurationError(
                "DEC-0006 Violation: Fixture/mock adapter is strictly forbidden in production mode. "
                "System startup halted."
            )
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise StartupConfigurationError(
                "DEC-0006 Violation: Production mode requires a valid GEMINI_API_KEY in environment. "
                "System startup halted."
            )


def get_llm_client(
    data_mode: DataMode | str | None = None,
    use_mock: bool = False,
    api_key: str | None = None,
    model_version: str | None = None,
) -> BaseGeminiClient:
    """Factory creating Gemini client with production startup guard.

    Authority: DEC-0006
    """
    env = os.getenv("STAYMAD_ENV", "").lower()
    norm_mode = str(data_mode or os.getenv("DATA_MODE", "DEMO")).upper()
    is_prod = env == "production" or norm_mode == DataMode.LIVE.value

    # Run startup verification
    validate_production_startup(data_mode=norm_mode, use_fixture=use_mock)

    if is_prod:
        return GeminiClient(api_key=api_key, model_version=model_version)

    # In dev/demo/test mode:
    resolved_key = api_key or os.getenv("GEMINI_API_KEY")
    if use_mock or not resolved_key:
        return DeterministicGeminiClient(
            model_version=model_version or "mock-deterministic-v1"
        )

    return GeminiClient(api_key=resolved_key, model_version=model_version)
