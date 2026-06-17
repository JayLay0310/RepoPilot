import os
import json
from typing import Optional, Dict, Any
from functools import lru_cache

try:
    from openai import OpenAI, APIError, RateLimitError
except ImportError:
    OpenAI = None
    APIError = Exception
    RateLimitError = Exception

from backend.config import get_settings


class LLMClient:
    """封装 OpenAI API 调用的客户端"""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4-turbo"):
        self.model = model
        self.client = None
        
        if OpenAI is None:
            print("Warning: OpenAI not installed. LLM features disabled.")
            return
        
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("Warning: OPENAI_API_KEY not set. LLM features disabled.")
            return
        
        self.client = OpenAI(api_key=api_key)

    def call(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> Dict[str, Any]:
        """调用 LLM"""
        if self.client is None:
            return {
                "success": False,
                "error": "OpenAI client not initialized",
                "content": "",
            }

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
                "tokens_used": response.usage.total_tokens,
            }
        except RateLimitError:
            return {
                "success": False,
                "error": "Rate limit exceeded",
                "content": "",
            }
        except APIError as e:
            return {
                "success": False,
                "error": str(e),
                "content": "",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "content": "",
            }

    def call_with_json(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.3,
    ) -> Dict[str, Any]:
        """调用 LLM 并期望返回 JSON"""
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
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            data = json.loads(content)
            return {
                "success": True,
                "data": data,
                "tokens_used": response.usage.total_tokens,
            }
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "Invalid JSON response",
                "data": {},
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "data": {},
            }


@lru_cache(maxsize=1)
def get_llm_client() -> LLMClient:
    """获取 LLM 客户端单例"""
    settings = get_settings()
    return LLMClient(model=settings.openai_model)
