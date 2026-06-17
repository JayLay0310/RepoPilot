import json
import os
from functools import lru_cache
from typing import Any

try:
    from openai import APIError, OpenAI, RateLimitError
except ImportError:
    OpenAI = None
    APIError = Exception
    RateLimitError = Exception

from backend.config import get_settings


class LLMClient:
    """Wrapper around OpenAI chat completions."""

    def __init__(self, api_key: str | None = None, model: str = "gpt-4-turbo") -> None:
        self.model = model
        self.client = None

        if OpenAI is None:
            return

        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            return

        self.client = OpenAI(api_key=api_key)

    def call(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> dict[str, Any]:
        if self.client is None:
            return {"success": False, "error": "OpenAI client not initialized", "content": ""}

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return {
                "success": True,
                "content": response.choices[0].message.content,
                "tokens_used": response.usage.total_tokens if response.usage else 0,
            }
        except RateLimitError:
            return {"success": False, "error": "Rate limit exceeded", "content": ""}
        except APIError as exc:
            return {"success": False, "error": str(exc), "content": ""}
        except Exception as exc:
            return {"success": False, "error": str(exc), "content": ""}

    def call_with_json(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.3,
        max_tokens: int = 2500,
    ) -> dict[str, Any]:
        if self.client is None:
            return {"success": False, "error": "OpenAI client not initialized", "data": {}}

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or "{}"
            return {
                "success": True,
                "data": json.loads(content),
                "tokens_used": response.usage.total_tokens if response.usage else 0,
            }
        except json.JSONDecodeError:
            return {"success": False, "error": "Invalid JSON response", "data": {}}
        except Exception as exc:
            return {"success": False, "error": str(exc), "data": {}}


@lru_cache(maxsize=1)
def get_llm_client() -> LLMClient:
    settings = get_settings()
    return LLMClient(api_key=settings.openai_api_key, model=settings.openai_model)
