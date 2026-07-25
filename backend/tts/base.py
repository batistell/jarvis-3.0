from abc import ABC, abstractmethod

class BaseTTSEngine(ABC):
    """Interface abstrata para motores Text-To-Speech (TTS)."""

    @abstractmethod
    async def synthesize(self, text: str) -> bytes:
        """Sintetiza texto em bytes de áudio (MP3/WAV)."""
        pass
