from abc import ABC, abstractmethod
from typing import AsyncGenerator

class BaseLLMEngine(ABC):
    """
    Interface Base Abstrata para Motores de Linguagem (LLM).
    Suporta resposta completa, streaming de tokens e chamada de ferramentas (Function Calling).
    """

    async def ensure_model_loaded(self) -> bool:
        """Verifica se o modelo está pronto/carregado (ou baixa se necessário)."""
        return True

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        history: list[dict] | None = None
    ) -> str:
        """Gera a resposta completa para o prompt especificado."""
        pass

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        history: list[dict] | None = None
    ) -> AsyncGenerator[str, None]:
        """Gera a resposta token por token em tempo real (Streaming)."""
        pass

    @abstractmethod
    async def call_tools(
        self,
        prompt: str,
        tools: list[dict],
        system_prompt: str | None = None
    ) -> dict:
        """Executa a invocação de ferramentas (Tool Use / Function Calling) para Home Assistant / Ações."""
        pass
