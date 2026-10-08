from abc import ABC, abstractmethod
from typing import Optional
import httpx
import json


class AIProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        pass

    @abstractmethod
    async def generate_json(self, prompt: str, system_prompt: Optional[str] = None) -> dict:
        pass


class BaseAIProvider(AIProvider):
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout: float = 60.0,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def _make_request(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 16384,
        response_format: Optional[dict] = None,
    ) -> str:
        raise NotImplementedError

    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return await self._make_request(messages)

    async def generate_json(self, prompt: str, system_prompt: Optional[str] = None) -> dict:
        json_prompt = prompt + "\n\nRespond ONLY with valid JSON. No markdown, no extra text."
        response = await self.generate(json_prompt, system_prompt)
        return self._parse_json(response)

    def _parse_json(self, text: str) -> dict:
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                try:
                    return json.loads(text[start : end + 1])
                except json.JSONDecodeError:
                    pass
            raise ValueError(f"Failed to parse JSON from response: {text[:200]}")

    async def close(self):
        await self.client.aclose()