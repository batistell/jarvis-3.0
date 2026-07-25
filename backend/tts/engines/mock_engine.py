from backend.tts.base import BaseTTSEngine

class MockTTSEngine(BaseTTSEngine):
    """Motor TTS Mock para testes offline."""
    async def synthesize(self, text: str) -> bytes:
        return b""
