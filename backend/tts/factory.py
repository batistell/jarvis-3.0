from backend.tts.base import BaseTTSEngine
from backend.tts.engines.edge_tts_engine import EdgeTTSEngine
from backend.tts.engines.mock_engine import MockTTSEngine
from backend.config import settings

class TTSFactory:
    """
    Fábrica e Registro de Motores TTS.
    Permite alternar entre EdgeTTS, PiperTTS ou Mock dinamicamente.
    """

    _registry: dict[str, type[BaseTTSEngine]] = {
        "edge-tts": EdgeTTSEngine,
        "mock": MockTTSEngine,
    }

    @classmethod
    def register_engine(cls, name: str, engine_class: type[BaseTTSEngine]) -> None:
        """Registra um novo motor TTS."""
        cls._registry[name.lower()] = engine_class

    @classmethod
    def get_engine_names(cls) -> list[str]:
        """Retorna os motores TTS disponíveis."""
        return list(cls._registry.keys())

    @classmethod
    def create_engine(cls, engine_name: str | None = None) -> BaseTTSEngine:
        """Cria e retorna o motor TTS configurado."""
        target_name = (engine_name or getattr(settings, "TTS_ENGINE", "edge-tts")).lower()
        engine_cls = cls._registry.get(target_name, EdgeTTSEngine)
        return engine_cls()
