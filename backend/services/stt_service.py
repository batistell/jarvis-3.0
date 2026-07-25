import asyncio
import numpy as np
from faster_whisper import WhisperModel
from backend.config import settings

class STTService:
    """
    Serviço de transcrição de voz em memória usando faster-whisper.
    """

    def __init__(self):
        self.model: WhisperModel | None = None
        self._is_loading = False

    def _ensure_model_loaded(self):
        if self.model is None and not self._is_loading:
            self._is_loading = True
            print(f"⚡ Carregando modelo faster-whisper ({settings.WHISPER_MODEL}) no dispositivo {settings.WHISPER_DEVICE}...")
            try:
                self.model = WhisperModel(
                    settings.WHISPER_MODEL,
                    device=settings.WHISPER_DEVICE,
                    compute_type=settings.WHISPER_COMPUTE_TYPE
                )
                print("✅ Modelo faster-whisper carregado com sucesso.")
            except Exception as e:
                print(f"⚠️ Erro ao carregar faster-whisper ({e}). Tentando modo de fallback em cpu/float32...")
                self.model = WhisperModel(
                    settings.WHISPER_MODEL,
                    device="cpu",
                    compute_type="float32"
                )
            finally:
                self._is_loading = False

    def transcribe_pcm(self, pcm_bytes: bytes) -> str:
        """
        Converte os bytes PCM 16-bit Mono (16kHz) em NumPy float32 e executa o Whisper em memória.
        """
        if not pcm_bytes:
            return ""

        self._ensure_model_loaded()
        if self.model is None:
            return ""

        # Converte PCM 16-bit signed integer para float32 (-1.0 a 1.0)
        pcm_int16 = np.frombuffer(pcm_bytes, dtype=np.int16)
        audio_float32 = pcm_int16.astype(np.float32) / 32768.0

        try:
            segments, _ = self.model.transcribe(
                audio_float32,
                beam_size=5,
                language="pt"
            )
            text = " ".join([segment.text for segment in segments]).strip()
            return text
        except Exception as e:
            print(f"❌ Erro na transcrição faster-whisper: {e}")
            return ""

    async def transcribe_pcm_async(self, pcm_bytes: bytes) -> str:
        """
        Executa a transcrição CPU-bound em uma thread separada para não bloquear o event loop do asyncio.
        """
        return await asyncio.to_thread(self.transcribe_pcm, pcm_bytes)

stt_service = STTService()
