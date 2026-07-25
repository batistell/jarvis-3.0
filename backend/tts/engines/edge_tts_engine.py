import io
import asyncio
import edge_tts
from backend.tts.base import BaseTTSEngine
from backend.config import settings

class EdgeTTSEngine(BaseTTSEngine):
    """
    Motor TTS Neural ultra-realista usando Microsoft Edge TTS.
    Gera áudio MP3 em memória para ser enviado ao navegador cliente e reproduzido via Web Audio API.
    """

    def __init__(self, voice: str | None = None):
        self.voice = voice or getattr(settings, "TTS_VOICE", "pt-BR-AntonioNeural")

    async def synthesize(self, text: str) -> bytes:
        if not text or not text.strip():
            return b""

        try:
            communicate = edge_tts.Communicate(text.strip(), self.voice)
            buffer = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    buffer.write(chunk["data"])
            return buffer.getvalue()
        except Exception as e:
            print(f"❌ [TTS ERROR] Erro na síntese EdgeTTS: {e}", flush=True)
            return b""
