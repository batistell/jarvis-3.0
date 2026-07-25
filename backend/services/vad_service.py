import time
import numpy as np
from backend.config import settings

class BackendVADDetector:
    """
    Detector de Atividade de Voz (VAD) executado no backend.
    Acumula chunks PCM 16-bit (16kHz Mono) em tempo real, monitora RMS de energia
    e identifica pausas de fala (silêncio prolongado após fala ativa).
    """

    def __init__(
        self,
        silence_threshold_rms: float = settings.VAD_SILENCE_THRESHOLD_RMS,
        silence_duration_ms: float = settings.VAD_SILENCE_DURATION_MS
    ):
        self.silence_threshold_rms = silence_threshold_rms
        self.silence_duration_sec = silence_duration_ms / 1000.0
        
        self.audio_buffer = bytearray()
        self.is_speech_active = False
        self.silence_start_time: float | None = None
        self.min_speech_duration_bytes = 16000 * 2 * 0.4  # Pelo menos 400ms de áudio para evitar estalos

    def process_pcm_chunk(self, chunk_bytes: bytes) -> tuple[bool, bytes | None]:
        """
        Processa um chunk binário de áudio PCM 16-bit Mono 16kHz.
        Retorna:
            (True, audio_bytes_completos) -> se uma pausa foi identificada após fala ativa.
            (False, None) -> se ainda estiver acumulando ou em silêncio.
        """
        if not chunk_bytes:
            return False, None

        self.audio_buffer.extend(chunk_bytes)

        # Converte chunk para int16 numpy array para calcular a energia RMS
        pcm_int16 = np.frombuffer(chunk_bytes, dtype=np.int16)
        if len(pcm_int16) == 0:
            return False, None

        # Normalização float (-1.0 a 1.0)
        pcm_float = pcm_int16.astype(np.float32) / 32768.0
        rms = float(np.sqrt(np.mean(pcm_float ** 2)))

        now = time.time()

        if rms >= self.silence_threshold_rms:
            # Voz ativa detectada no chunk
            if not self.is_speech_active:
                self.is_speech_active = True
                print(f"🎙️ Backend VAD: Voz iniciada (RMS: {rms:.4f})")
            self.silence_start_time = None
        else:
            # Silêncio no chunk
            if self.is_speech_active:
                if self.silence_start_time is None:
                    self.silence_start_time = now
                elif (now - self.silence_start_time) >= self.silence_duration_sec:
                    # Pausa identificada após fala ativa!
                    if len(self.audio_buffer) >= self.min_speech_duration_bytes:
                        completed_audio = bytes(self.audio_buffer)
                        self.reset()
                        print(f"⏹️ Backend VAD: Pausa de fala detectada no servidor! Buffer: {len(completed_audio)} bytes.")
                        return True, completed_audio
                    else:
                        # Áudio muito curto (apenas um estalo)
                        self.reset()

        return False, None

    def reset(self):
        """Reseta o estado do detector VAD."""
        self.audio_buffer.clear()
        self.is_speech_active = False
        self.silence_start_time = None
