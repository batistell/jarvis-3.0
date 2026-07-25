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

        start_t = time.time()
        try:
            communicate = edge_tts.Communicate(text.strip(), self.voice)
            buffer = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    buffer.write(chunk["data"])
            res = buffer.getvalue()
            elapsed_ms = (time.time() - start_t) * 1000.0
            from backend.services.health_service import health_service
            health_service.record_tts_latency(elapsed_ms)
            return res
        except Exception as e:
            print(f"❌ [TTS ERROR] Erro na síntese EdgeTTS: {e}", flush=True)
            return b""
