"""Minimal provider-agnostic LLM client.

Gemini, Groq and Ollama all expose an OpenAI-compatible
`/chat/completions` endpoint, so one ~40-line client covers the free options.
Switching provider is an environment variable, not a code change.

    LLM_PROVIDER=gemini  LLM_API_KEY=...   # Google AI Studio key (free tier)
    LLM_PROVIDER=groq    LLM_API_KEY=...   # console.groq.com key (free tier)
    LLM_PROVIDER=ollama                    # local model, no key
    LLM_MODEL=...                          # optional override
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

import requests

PROVIDERS = {
    # Model names change often: check the provider's model list and override with LLM_MODEL.
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "gemini-2.5-flash-lite"),
    "groq": ("https://api.groq.com/openai/v1", "openai/gpt-oss-20b"),
    "ollama": ("http://localhost:11434/v1", "qwen3:8b"),
}


class LLMRequestError(RuntimeError):
    """The API rejected the request (bad key, unknown model...): retrying will not help."""


@dataclass
class LLMClient:
    base_url: str
    model: str
    api_key: str = ""
    timeout: float = 60.0
    max_retries: int = 4
    min_interval: float = 4.5  # seconds between calls: stays under ~15 req/min free tiers

    _last_call: float = 0.0

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
                   model=os.getenv("LLM_MODEL", model), api_key=key,
                   min_interval=0.0 if provider == "ollama" else 4.5)

    def chat(self, system: str, user: str, json_mode: bool = False) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 0,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

        for attempt in range(self.max_retries):
            wait = self.min_interval - (time.monotonic() - self._last_call)
            if wait > 0:
                time.sleep(wait)
            self._last_call = time.monotonic()
            resp = requests.post(f"{self.base_url.rstrip('/')}/chat/completions",
                                 json=payload, headers=headers, timeout=self.timeout)
            if resp.status_code in (429, 500, 502, 503):  # rate limit / transient
                time.sleep(2 ** attempt * 5)
                continue
            if not resp.ok:  # keep the provider's explanation: it says why (model retired, bad key...)
                raise LLMRequestError(f"HTTP {resp.status_code} for model '{self.model}': {resp.text[:500]}")
            return resp.json()["choices"][0]["message"]["content"]
        raise RuntimeError(f"LLM call failed after {self.max_retries} retries (last {resp.status_code}).")
