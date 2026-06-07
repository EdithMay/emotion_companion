"""OpenAI-compatible LLM service."""

import json
import os
from typing import Iterator

import requests

_llm_instance = None


class OpenAICompatibleLLM:
    """Small adapter exposing the invoke/stream_invoke API used by the app."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout: float,
    ):
        if not api_key:
            raise ValueError("LLM_API_KEY 或 OPENAI_API_KEY 未配置")
        if not base_url:
            raise ValueError("LLM_BASE_URL 或 OPENAI_BASE_URL 未配置")
        if not model:
            raise ValueError("LLM_MODEL_ID 或 OPENAI_MODEL 未配置")

        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.provider = "openai-compatible"

    @property
    def chat_completions_url(self) -> str:
        return f"{self.base_url}/chat/completions"

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _payload(self, messages: list[dict], stream: bool) -> dict:
        return {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "stream": stream,
        }

    def invoke(self, messages: list[dict]) -> str:
        """Call /chat/completions and return the assistant message content."""
        response = requests.post(
            self.chat_completions_url,
            headers=self._headers(),
            json=self._payload(messages, stream=False),
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices") or []
        if not choices:
            return ""
        message = choices[0].get("message") or {}
        return (message.get("content") or "").strip()

    def stream_invoke(self, messages: list[dict]) -> Iterator[str]:
        """Stream content chunks from OpenAI-style data-only SSE."""
        with requests.post(
            self.chat_completions_url,
            headers=self._headers(),
            json=self._payload(messages, stream=True),
            timeout=self.timeout,
            stream=True,
        ) as response:
            response.raise_for_status()
            for raw_line in response.iter_lines():
                if not raw_line:
                    continue

                line = raw_line.decode("utf-8").strip()
                if not line.startswith("data:"):
                    continue

                payload = line[5:].strip()
                if payload == "[DONE]":
                    break

                try:
                    data = json.loads(payload)
                except json.JSONDecodeError:
                    continue

                choices = data.get("choices") or []
                if not choices:
                    continue

                delta = choices[0].get("delta") or {}
                content = delta.get("content")
                if content:
                    yield content


def get_llm() -> OpenAICompatibleLLM:
    """Return a singleton OpenAI-compatible LLM adapter."""
    global _llm_instance

    if _llm_instance is None:
        from ..config import get_settings

        settings = get_settings()
        timeout = float(os.getenv("LLM_TIMEOUT") or 300)
        api_key = os.getenv("LLM_API_KEY") or settings.openai_api_key
        base_url = os.getenv("LLM_BASE_URL") or settings.openai_base_url
        model = os.getenv("LLM_MODEL_ID") or settings.openai_model

        _llm_instance = OpenAICompatibleLLM(
            api_key=api_key,
            base_url=base_url,
            model=model,
            timeout=timeout,
        )

        print("✅ LLM服务初始化成功")
        print(f"   提供商: {_llm_instance.provider}")
        print(f"   Base URL: {_llm_instance.base_url}")
        print(f"   模型: {_llm_instance.model}")

    return _llm_instance


def reset_llm():
    """Reset the singleton for tests or runtime reconfiguration."""
    global _llm_instance
    _llm_instance = None
