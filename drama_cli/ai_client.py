"""AI 客户端 - 支持多种 LLM 提供商"""

from openai import OpenAI
from .config import DramaConfig


class AIClient:
    """统一的 AI 客户端"""

    def __init__(self, config: DramaConfig):
        self.config = config
        self.client = OpenAI(
            api_key=config.ai_api_key or "sk-placeholder",
            base_url=config.ai_base_url
        )

    def chat(self, system_prompt: str, user_prompt: str,
             temperature: float = 0.8, max_tokens: int = 4096) -> str:
        """调用 LLM 生成内容"""
        try:
            response = self.client.chat.completions.create(
                model=self.config.ai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"AI 调用失败: {e}")

    def chat_stream(self, system_prompt: str, user_prompt: str,
                    temperature: float = 0.8, max_tokens: int = 4096):
        """流式调用 LLM"""
        try:
            stream = self.client.chat.completions.create(
                model=self.config.ai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            raise RuntimeError(f"AI 流式调用失败: {e}")