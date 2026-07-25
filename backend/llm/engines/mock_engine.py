import asyncio
from typing import AsyncGenerator
from backend.llm.base import BaseLLMEngine

class MockLLMEngine(BaseLLMEngine):
    """
    Motor LLM Mock para desenvolvimento offline e testes.
    """

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        history: list[dict] | None = None
    ) -> str:
        return f"[MOCK LLM]: Resposta simulada para '{prompt}'."

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        history: list[dict] | None = None
    ) -> AsyncGenerator[str, None]:
        words = ["Olá,", "sou", "o", "Jarvis", "simulado.", "Como", "posso", "ajudar?"]
        for word in words:
            yield word + " "
            await asyncio.sleep(0.05)

    async def call_tools(
        self,
        prompt: str,
        tools: list[dict],
        system_prompt: str | None = None
    ) -> dict:
        return {
            "content": f"[MOCK LLM]: Chamada de ferramentas simulada para '{prompt}'.",
            "tool_calls": []
        }
