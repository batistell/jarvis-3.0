from backend.llm.base import BaseLLMEngine
from backend.llm.engines.native_qwen_engine import NativeQwenEngine
from backend.llm.engines.ollama_engine import OllamaLLMEngine
from backend.llm.engines.mock_engine import MockLLMEngine
from backend.config import settings

class LLMFactory:
    """
    Fábrica e Registro de Motores LLM.
    Permite alternar entre Qwen Nativo (CTranslate2 em memória), Ollama ou Mock dinamicamente.
    """

    _registry: dict[str, type[BaseLLMEngine]] = {
        "qwen-native": NativeQwenEngine,
        "ollama": OllamaLLMEngine,
        "mock": MockLLMEngine,
    }

    @classmethod
    def register_engine(cls, name: str, engine_class: type[BaseLLMEngine]) -> None:
        """Registra um novo motor LLM."""
        cls._registry[name.lower()] = engine_class

    @classmethod
    def get_engine_names(cls) -> list[str]:
        """Retorna os motores LLM disponíveis."""
        return list(cls._registry.keys())

    @classmethod
    def create_engine(cls, engine_name: str | None = None) -> BaseLLMEngine:
        """Cria e retorna o motor LLM configurado."""
        target_name = (engine_name or getattr(settings, "LLM_ENGINE", "qwen-native")).lower()
        engine_cls = cls._registry.get(target_name, NativeQwenEngine)
        return engine_cls()
