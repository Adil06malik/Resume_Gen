import asyncio
from typing import Optional
import httpx
from app.ai.base import BaseAIProvider


class OpenAICompatibleProvider(BaseAIProvider):
    async def _post(self, url: str, headers: dict, payload: dict) -> str:
        max_attempts = 4
        for attempt in range(max_attempts):
            response = await self.client.post(url, headers=headers, json=payload)
            if response.status_code in (429, 500, 502, 503, 504) and attempt < max_attempts - 1:
                await asyncio.sleep(2 * (attempt + 1))
                continue
            response.raise_for_status()
            data = response.json()

            try:
                content = data["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError) as e:
                # Transient empty/malformed responses from rate-limited or
                # reasoning models -> retry a couple of times.
                if attempt < max_attempts - 1:
                    await asyncio.sleep(2 * (attempt + 1))
                    continue
                raise ValueError(f"Malformed response from AI provider: {str(data)[:500]}") from e

            if content is None or not str(content).strip():
                if attempt < max_attempts - 1:
                    await asyncio.sleep(2 * (attempt + 1))
                    continue

            return content or ""

        raise ValueError("AI provider returned no usable response after retries")

    async def _make_request(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 16384,
        response_format: Optional[dict] = None,
    ) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": int(max_tokens),
        }
        if response_format:
            payload["response_format"] = response_format
        return await self._post(url, headers, payload)


class OpenRouterProvider(OpenAICompatibleProvider):
    async def _make_request(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 16384,
        response_format: Optional[dict] = None,
    ) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/ai-resume-tailor",
            "X-Title": "AI Resume Tailor",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": int(max_tokens),
        }
        if response_format:
            payload["response_format"] = response_format
        return await self._post(url, headers, payload)