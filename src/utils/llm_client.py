"""Multi-provider LLM client with automatic fallback: Claude → Gemini → OpenAI."""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class LLMResponse:
    """Response from a LLM call with metadata."""

    text: str
    provider_used: str
    model_used: str
    latency_ms: float
    tokens_used: Optional[int] = None


@dataclass
class ProviderHealth:
    """Tracks the health state of an LLM provider."""

    name: str
    consecutive_failures: int = 0
    last_failure_time: float = field(default_factory=float)
    is_healthy: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.last_failure_time, float):
            self.last_failure_time = 0.0

    def record_failure(self, threshold: int, cooldown: int) -> None:
        self.consecutive_failures += 1
        self.last_failure_time = time.monotonic()
        if self.consecutive_failures >= threshold:
            self.is_healthy = False
            logger.warning(
                "LLM provider marked unhealthy",
                provider=self.name,
                failures=self.consecutive_failures,
            )

    def record_success(self) -> None:
        self.consecutive_failures = 0
        self.is_healthy = True

    def check_recovery(self, cooldown: int) -> bool:
        """Return True if provider is healthy or has recovered after cooldown."""
        if self.is_healthy:
            return True
        if time.monotonic() - self.last_failure_time > cooldown:
            self.is_healthy = True
            self.consecutive_failures = 0
            logger.info("LLM provider recovered", provider=self.name)
            return True
        return False


class MultiLLMClient:
    """
    Multi-provider LLM client with automatic failover.

    Priority order: Claude (Anthropic) → Gemini (Google) → OpenAI.
    Falls back to next provider on any exception (API error, timeout, rate limit).
    Tracks provider health and marks unhealthy after threshold failures.
    Unhealthy providers are retried after a cooldown period.
    """

    def __init__(self, settings) -> None:
        self.settings = settings
        self._provider_health: dict[str, ProviderHealth] = {}
        self._anthropic_client = None
        self._openai_client = None
        self._provider_order: list[str] = getattr(
            settings, "llm_provider_priority", ["claude", "gemini", "openai"]
        )
        for p in self._provider_order:
            self._provider_health[p] = ProviderHealth(name=p, last_failure_time=0.0)

    def _get_anthropic_client(self):
        if self._anthropic_client is None:
            from anthropic import AsyncAnthropic

            self._anthropic_client = AsyncAnthropic(api_key=self.settings.anthropic_api_key)
        return self._anthropic_client

    def _get_openai_client(self):
        if self._openai_client is None:
            from openai import AsyncOpenAI

            self._openai_client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        return self._openai_client

    async def _call_claude(self, system_prompt: str, user_message: str, max_tokens: int) -> str:
        client = self._get_anthropic_client()
        response = await client.messages.create(
            model=self.settings.anthropic_model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        content = response.content[0]
        if content.type != "text":
            raise ValueError(f"Expected text response, got {content.type}")
        return content.text

    async def _call_gemini(self, system_prompt: str, user_message: str, max_tokens: int) -> str:
        try:
            from google import genai
            from google.genai import types as genai_types
        except ImportError as err:
            raise RuntimeError(
                "google-genai not installed. Run: pip install google-genai"
            ) from err
        client = genai.Client(api_key=self.settings.gemini_api_key)
        model_name = getattr(self.settings, "gemini_model", "gemini-2.0-flash-001")
        response = await client.aio.models.generate_content(
            model=model_name,
            contents=user_message,
            config=genai_types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=max_tokens,
            ),
        )
        return response.text or ""

    async def _call_openai(self, system_prompt: str, user_message: str, max_tokens: int) -> str:
        client = self._get_openai_client()
        response = await client.chat.completions.create(
            model=getattr(self.settings, "openai_model", "gpt-4o"),
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )
        return response.choices[0].message.content or ""

    async def call(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Call LLM with automatic fallback. Returns LLMResponse with provider info."""
        if not getattr(self.settings, "llm_fallback_enabled", True):
            return await self._call_single("claude", system_prompt, user_message, max_tokens)

        cooldown: int = getattr(self.settings, "llm_provider_cooldown_seconds", 60)
        threshold: int = getattr(self.settings, "llm_provider_failure_threshold", 3)

        last_exc: Optional[Exception] = None

        for provider in self._provider_order:
            health = self._provider_health.get(provider)
            if health and not health.check_recovery(cooldown):
                logger.info("Skipping unhealthy provider", provider=provider)
                continue

            if not self._has_api_key(provider):
                logger.debug("No API key for provider, skipping", provider=provider)
                continue

            start = time.monotonic()
            try:
                text = await self._call_provider(provider, system_prompt, user_message, max_tokens)
                latency_ms = (time.monotonic() - start) * 1000
                if health:
                    health.record_success()
                logger.info(
                    "LLM call succeeded",
                    provider=provider,
                    latency_ms=round(latency_ms),
                )
                return LLMResponse(
                    text=text,
                    provider_used=provider,
                    model_used=self._get_model_name(provider),
                    latency_ms=latency_ms,
                )
            except Exception as exc:
                latency_ms = (time.monotonic() - start) * 1000
                last_exc = exc
                if health:
                    health.record_failure(threshold, cooldown)
                logger.warning(
                    "LLM provider failed, trying next",
                    provider=provider,
                    error=str(exc)[:200],
                    latency_ms=round(latency_ms),
                )

        raise RuntimeError(f"All LLM providers failed. Last error: {last_exc}") from last_exc

    async def _call_provider(
        self, provider: str, system_prompt: str, user_message: str, max_tokens: int
    ) -> str:
        if provider == "claude":
            return await self._call_claude(system_prompt, user_message, max_tokens)
        if provider == "gemini":
            return await self._call_gemini(system_prompt, user_message, max_tokens)
        if provider == "openai":
            return await self._call_openai(system_prompt, user_message, max_tokens)
        raise ValueError(f"Unknown provider: {provider}")

    async def _call_single(
        self, provider: str, system_prompt: str, user_message: str, max_tokens: int
    ) -> LLMResponse:
        start = time.monotonic()
        text = await self._call_provider(provider, system_prompt, user_message, max_tokens)
        return LLMResponse(
            text=text,
            provider_used=provider,
            model_used=self._get_model_name(provider),
            latency_ms=(time.monotonic() - start) * 1000,
        )

    def _has_api_key(self, provider: str) -> bool:
        if provider == "claude":
            return bool(getattr(self.settings, "anthropic_api_key", ""))
        if provider == "gemini":
            return bool(getattr(self.settings, "gemini_api_key", ""))
        if provider == "openai":
            return bool(getattr(self.settings, "openai_api_key", ""))
        return False

    def _get_model_name(self, provider: str) -> str:
        if provider == "claude":
            return getattr(self.settings, "anthropic_model", "claude-sonnet-4-6")
        if provider == "gemini":
            return getattr(self.settings, "gemini_model", "gemini-2.0-flash-001")
        if provider == "openai":
            return getattr(self.settings, "openai_model", "gpt-4o")
        return "unknown"
