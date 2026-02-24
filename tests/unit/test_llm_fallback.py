"""Unit tests for MultiLLMClient fallback behaviour and provider health tracking."""
from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.utils.llm_client import LLMResponse, MultiLLMClient, ProviderHealth


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_settings(
    *,
    anthropic_api_key: str = "sk-ant-test",
    gemini_api_key: str = "gemini-test",
    openai_api_key: str = "openai-test",
    anthropic_model: str = "claude-sonnet-4-6",
    gemini_model: str = "gemini-2.0-flash-001",
    openai_model: str = "gpt-4o",
    llm_provider_priority: list[str] | None = None,
    llm_fallback_enabled: bool = True,
    llm_provider_failure_threshold: int = 3,
    llm_provider_cooldown_seconds: int = 60,
) -> MagicMock:
    settings = MagicMock()
    settings.anthropic_api_key = anthropic_api_key
    settings.gemini_api_key = gemini_api_key
    settings.openai_api_key = openai_api_key
    settings.anthropic_model = anthropic_model
    settings.gemini_model = gemini_model
    settings.openai_model = openai_model
    settings.llm_provider_priority = llm_provider_priority or ["claude", "gemini", "openai"]
    settings.llm_fallback_enabled = llm_fallback_enabled
    settings.llm_provider_failure_threshold = llm_provider_failure_threshold
    settings.llm_provider_cooldown_seconds = llm_provider_cooldown_seconds
    return settings


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_claude_primary_success():
    """When Claude succeeds, it should be used and gemini/openai never called."""
    settings = make_settings()
    client = MultiLLMClient(settings)

    with patch.object(client, "_call_claude", new=AsyncMock(return_value="claude reply")):
        with patch.object(client, "_call_gemini", new=AsyncMock()) as mock_gemini:
            with patch.object(client, "_call_openai", new=AsyncMock()) as mock_openai:
                response = await client.call("sys", "user msg")

    assert response.text == "claude reply"
    assert response.provider_used == "claude"
    assert response.model_used == "claude-sonnet-4-6"
    mock_gemini.assert_not_called()
    mock_openai.assert_not_called()


@pytest.mark.asyncio
async def test_fallback_to_gemini_when_claude_fails():
    """When Claude raises, client should fall back to Gemini."""
    settings = make_settings()
    client = MultiLLMClient(settings)

    with patch.object(client, "_call_claude", new=AsyncMock(side_effect=RuntimeError("API error"))):
        with patch.object(client, "_call_gemini", new=AsyncMock(return_value="gemini reply")):
            with patch.object(client, "_call_openai", new=AsyncMock()) as mock_openai:
                response = await client.call("sys", "user msg")

    assert response.text == "gemini reply"
    assert response.provider_used == "gemini"
    assert response.model_used == "gemini-2.0-flash-001"
    mock_openai.assert_not_called()


@pytest.mark.asyncio
async def test_fallback_to_openai_when_claude_and_gemini_fail():
    """When Claude and Gemini both fail, client should fall back to OpenAI."""
    settings = make_settings()
    client = MultiLLMClient(settings)

    with patch.object(client, "_call_claude", new=AsyncMock(side_effect=RuntimeError("claude down"))):
        with patch.object(client, "_call_gemini", new=AsyncMock(side_effect=RuntimeError("gemini down"))):
            with patch.object(client, "_call_openai", new=AsyncMock(return_value="openai reply")):
                response = await client.call("sys", "user msg")

    assert response.text == "openai reply"
    assert response.provider_used == "openai"
    assert response.model_used == "gpt-4o"


@pytest.mark.asyncio
async def test_all_fail_raises_runtime_error():
    """When all providers fail, a RuntimeError should be raised."""
    settings = make_settings()
    client = MultiLLMClient(settings)

    with patch.object(client, "_call_claude", new=AsyncMock(side_effect=RuntimeError("claude down"))):
        with patch.object(client, "_call_gemini", new=AsyncMock(side_effect=RuntimeError("gemini down"))):
            with patch.object(client, "_call_openai", new=AsyncMock(side_effect=RuntimeError("openai down"))):
                with pytest.raises(RuntimeError, match="All LLM providers failed"):
                    await client.call("sys", "user msg")


@pytest.mark.asyncio
async def test_provider_health_tracking():
    """After threshold failures, provider should be marked unhealthy."""
    threshold = 3
    settings = make_settings(llm_provider_failure_threshold=threshold, llm_provider_cooldown_seconds=3600)
    client = MultiLLMClient(settings)
    health = client._provider_health["claude"]

    assert health.is_healthy is True

    for _ in range(threshold):
        health.record_failure(threshold, cooldown=3600)

    assert health.is_healthy is False
    assert health.consecutive_failures == threshold


@pytest.mark.asyncio
async def test_provider_recovery_after_cooldown():
    """Provider marked unhealthy should recover once cooldown has elapsed."""
    settings = make_settings(llm_provider_cooldown_seconds=1)
    client = MultiLLMClient(settings)
    health = client._provider_health["claude"]

    # Push past threshold so it becomes unhealthy
    for _ in range(3):
        health.record_failure(threshold=3, cooldown=1)

    assert health.is_healthy is False

    # Simulate cooldown elapsed
    health.last_failure_time = time.monotonic() - 2  # 2 seconds ago, cooldown is 1 s

    recovered = health.check_recovery(cooldown=1)
    assert recovered is True
    assert health.is_healthy is True
    assert health.consecutive_failures == 0


@pytest.mark.asyncio
async def test_unhealthy_provider_skipped_before_cooldown():
    """An unhealthy provider within cooldown window should be skipped entirely."""
    settings = make_settings(
        llm_provider_priority=["claude", "openai"],
        gemini_api_key="",  # no gemini
        llm_provider_failure_threshold=1,
        llm_provider_cooldown_seconds=3600,
    )
    client = MultiLLMClient(settings)

    # Mark claude unhealthy
    health = client._provider_health["claude"]
    health.record_failure(threshold=1, cooldown=3600)
    assert health.is_healthy is False

    with patch.object(client, "_call_claude", new=AsyncMock()) as mock_claude:
        with patch.object(client, "_call_openai", new=AsyncMock(return_value="openai reply")):
            response = await client.call("sys", "user msg")

    assert response.provider_used == "openai"
    mock_claude.assert_not_called()


@pytest.mark.asyncio
async def test_no_api_key_provider_skipped():
    """A provider with no API key configured should be skipped silently."""
    settings = make_settings(
        anthropic_api_key="",   # Claude has no key
        gemini_api_key="",      # Gemini has no key
        openai_api_key="sk-openai",
    )
    client = MultiLLMClient(settings)

    with patch.object(client, "_call_openai", new=AsyncMock(return_value="openai reply")):
        response = await client.call("sys", "user msg")

    assert response.provider_used == "openai"


@pytest.mark.asyncio
async def test_fallback_disabled_uses_only_claude():
    """When llm_fallback_enabled=False, only Claude is invoked regardless of failures."""
    settings = make_settings(llm_fallback_enabled=False)
    client = MultiLLMClient(settings)

    with patch.object(client, "_call_claude", new=AsyncMock(return_value="claude direct")):
        response = await client.call("sys", "msg")

    assert response.provider_used == "claude"
    assert response.text == "claude direct"


def test_llm_response_dataclass():
    """LLMResponse should store all fields correctly."""
    resp = LLMResponse(
        text="hello",
        provider_used="claude",
        model_used="claude-sonnet-4-6",
        latency_ms=123.4,
        tokens_used=50,
    )
    assert resp.text == "hello"
    assert resp.tokens_used == 50


def test_provider_health_record_success_resets_counter():
    health = ProviderHealth(name="claude", last_failure_time=0.0)
    health.consecutive_failures = 5
    health.is_healthy = False
    health.record_success()
    assert health.consecutive_failures == 0
    assert health.is_healthy is True
