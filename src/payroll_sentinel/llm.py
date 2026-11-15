"""Minimal provider-agnostic LLM client.

Gemini, Groq and Ollama all expose an OpenAI-compatible
`/chat/completions` endpoint, so one ~40-line client covers the free options.
Switching provider is an environment variable, not a code change.

    LLM_PROVIDER=gemini  LLM_API_KEY=...   # Google AI Studio key (free tier)
    LLM_PROVIDER=groq    LLM_API_KEY=...   # console.groq.com key (free tier)
    LLM_PROVIDER=ollama                    # local model, no key
    LLM_MODEL=...                          # optional override
    LLM_REASONING_EFFORT=low               # optional, for reasoning models such as gpt-oss
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field

import requests

PROVIDERS = {
    # Model names change often: check the provider's model list and override with LLM_MODEL.
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "gemini-3.5-flash-lite"),
    "groq": ("https://api.groq.com/openai/v1", "openai/gpt-oss-20b"),
    "ollama": ("http://localhost:11434/v1", "qwen3:8b"),
}


class LLMRequestError(RuntimeError):
    """The API rejected the request (bad key, unknown model...): retrying will not help."""


class LLMOutputError(RuntimeError):
    """The model answered, but not with valid JSON: only this request failed, not the setup."""


@dataclass
class LLMStats:
    """What one run cost: answered calls, HTTP requests (with retries), 429s and time.

    `seconds` is wall time inside chat(), including the pause between calls that
    keeps us under free-tier limits; `api_seconds` is only the time spent waiting
    for HTTP responses, so it compares how fast models are.
    """
    calls: int = 0
    requests: int = 0
    rate_limited: int = 0
    seconds: float = 0.0
    api_seconds: float = 0.0

    def summary(self) -> str:
        mean = f"{self.seconds / self.calls:.1f} s" if self.calls else "n/a"
        api_mean = f"{self.api_seconds / self.requests:.1f} s" if self.requests else "n/a"
        return (f"{self.calls} LLM calls ({self.requests} HTTP requests, {self.rate_limited} "
                f"rate-limit (429) responses), {self.seconds:.1f} s in LLM calls, {mean} per call; "
                f"{self.api_seconds:.1f} s waiting for the API ({api_mean} per request), the rest "
                "is pacing and retry back-off")


@dataclass
class LLMClient:
    base_url: str
    model: str
    api_key: str = ""
    provider: str = "custom"
    timeout: float = 60.0
    max_retries: int = 4
    min_interval: float = 4.5  # seconds between calls: stays under ~15 req/min free tiers
    # Reasoning models (gpt-oss) think before answering; with the default effort the
    # thinking can fill the whole answer budget and leave no JSON. None: not sent.
    reasoning_effort: str | None = None

    _last_call: float = 0.0
    stats: LLMStats = field(default_factory=LLMStats)

    @property
    def label(self) -> str:
        """Model name as shown in reports, with the reasoning effort when one is set."""
        return f"{self.model}, reasoning_effort={self.reasoning_effort}" if self.reasoning_effort else self.model

    @property
    def tag(self) -> str:
        """Provider and model as a file-name-safe string, e.g. 'gemini_gemini-3.5-flash-lite'."""
        return re.sub(r"[^A-Za-z0-9._-]+", "-", f"{self.provider}_{self.model}").strip("-")

    @classmethod
    def from_env(cls) -> "LLMClient":
        provider = os.getenv("LLM_PROVIDER", "gemini").lower()
        if provider not in PROVIDERS:
            raise ValueError(f"Unknown LLM_PROVIDER '{provider}'. Options: {list(PROVIDERS)}")
        base_url, model = PROVIDERS[provider]
        key = os.getenv("LLM_API_KEY", "")
        if provider != "ollama" and not key:
            raise RuntimeError(f"Set LLM_API_KEY for provider '{provider}'.")
        return cls(base_url=os.getenv("LLM_BASE_URL", base_url),
                   model=os.getenv("LLM_MODEL", model), api_key=key, provider=provider,
                   min_interval=0.0 if provider == "ollama" else 4.5,
                   reasoning_effort=os.getenv("LLM_REASONING_EFFORT") or None)

    def list_models(self) -> list[str]:
        """Model ids this key can use (OpenAI-compatible GET /models)."""
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        resp = requests.get(f"{self.base_url.rstrip('/')}/models", headers=headers, timeout=self.timeout)
        if not resp.ok:
            raise LLMRequestError(f"HTTP {resp.status_code} listing models: {resp.text[:500]}")
        return sorted(m["id"] for m in resp.json().get("data", []))

    def chat(self, system: str, user: str, json_mode: bool = False) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 0,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        if self.reasoning_effort:
            payload["reasoning_effort"] = self.reasoning_effort
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

        start = time.monotonic()
        try:
            for attempt in range(self.max_retries):
                wait = self.min_interval - (time.monotonic() - self._last_call)
                if wait > 0:
                    time.sleep(wait)
                self._last_call = time.monotonic()
                self.stats.requests += 1
                sent = time.monotonic()
                try:
                    resp = requests.post(f"{self.base_url.rstrip('/')}/chat/completions",
                                         json=payload, headers=headers, timeout=self.timeout)
                finally:
                    self.stats.api_seconds += time.monotonic() - sent
                if resp.status_code in (429, 500, 502, 503):  # rate limit / transient
                    self.stats.rate_limited += resp.status_code == 429
                    time.sleep(2 ** attempt * 5)
                    continue
                if resp.status_code == 400 and "json_validate_failed" in resp.text:
                    # Groq checks JSON mode itself: the model's output was bad, not our setup
                    raise LLMOutputError(f"model '{self.model}' did not return valid JSON: {resp.text[:300]}")
                if not resp.ok:  # keep the provider's explanation: it says why (model retired, bad key...)
                    raise LLMRequestError(
                        f"HTTP {resp.status_code} for model '{self.model}': {resp.text[:500]}")
                self.stats.calls += 1
                return resp.json()["choices"][0]["message"]["content"]
            raise RuntimeError(f"LLM call failed after {self.max_retries} retries (last {resp.status_code}).")
        finally:
            self.stats.seconds += time.monotonic() - start
