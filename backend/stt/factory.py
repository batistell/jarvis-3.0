from backend.stt.base import BaseSTTEngine
from backend.stt.engines.faster_whisper_engine import FasterWhisperEngine
from backend.stt.engines.mock_engine import MockSTTEngine
from backend.config import settings

class STTFactory:
    """
    Fábrica e Registro de Motores STT.
    Permite alternar, registrar ou reordenar motores STT dinamicamente.
    """

    _registry: dict[str, type[BaseSTTEngine]] = {
        "faster-whisper": FasterWhisperEngine,
        "mock": MockSTTEngine,
    }

    @classmethod
    def register_engine(cls, name: str, engine_class: type[BaseSTTEngine]) -> None:
        """Registra dinamicamente um novo motor STT."""
        cls._registry[name.lower()] = engine_class

    @classmethod
    def get_engine_names(cls) -> list[str]:
        """Retorna a lista de nomes de motores STT disponíveis."""
        return list(cls._registry.keys())

    @classmethod
    def create_engine(cls, engine_name: str | None = None) -> BaseSTTEngine:
        """Cria e retorna a instância do motor STT configurado."""
        target_name = (engine_name or getattr(settings, "STT_ENGINE", "faster-whisper")).lower()
        engine_cls = cls._registry.get(target_name, FasterWhisperEngine)
        return engine_cls()
