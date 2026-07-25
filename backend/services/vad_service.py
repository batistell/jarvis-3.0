import sys
import io
import time
import numpy as np
from backend.config import settings

# Garantir UTF-8 no console do Windows
if hasattr(sys.stdout, 'buffer') and getattr(sys.stdout, 'encoding', '').lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'buffer') and getattr(sys.stderr, 'encoding', '').lower() != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

class BackendVADDetector:
    """
    Detector de Atividade de Voz (VAD) executado no backend.
    Monitora e exibe em tempo real no terminal a chegada de cada chunk de áudio do frontend.
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
        self.min_speech_duration_bytes = 16000 * 2 * 0.4  # Mínimo 400ms de áudio
        self.chunk_count = 0

    def process_pcm_chunk(self, chunk_bytes: bytes) -> tuple[bool, bytes | None, bytes | None]:
        """
        Processa um chunk binário PCM (16kHz Mono 16-bit) e retorna:
        (is_pause, completed_audio_bytes, partial_audio_bytes)
        """
        if not chunk_bytes:
            return False, None, None

        self.chunk_count += 1
        self.audio_buffer.extend(chunk_bytes)

        pcm_int16 = np.frombuffer(chunk_bytes, dtype=np.int16)
        if len(pcm_int16) == 0:
            return False, None, None

        pcm_float = pcm_int16.astype(np.float32) / 32768.0
        rms = float(np.sqrt(np.mean(pcm_float ** 2)))

        now = time.time()
        state_label = "FALANDO 🎙️" if rms >= self.silence_threshold_rms else "SILÊNCIO 💤"

        # Log visual limpo em tempo real com limpeza da linha (\033[K)
        bar_length = int(min(16, rms * 80))
        visual_bar = "█" * bar_length + "░" * (16 - bar_length)
        print(f"\r\033[K[AUDIO #{self.chunk_count:03d}] RMS: {rms:.4f} [{visual_bar}] {state_label}", end="", flush=True)

        partial_audio = None

        if rms >= self.silence_threshold_rms:
            if not self.is_speech_active:
                self.is_speech_active = True
                print(f"\r\033[K🎙️  [VAD] Fala iniciada pelo usuário...", flush=True)
            self.silence_start_time = None

            # Durante a fala ativa, libera o buffer parcial a cada 2 chunks (~400ms) para transcrição live
            if len(self.audio_buffer) >= self.min_speech_duration_bytes and self.chunk_count % 2 == 0:
                partial_audio = bytes(self.audio_buffer)
        else:
            if self.is_speech_active:
                if self.silence_start_time is None:
                    self.silence_start_time = now
                elif (now - self.silence_start_time) >= self.silence_duration_sec:
                    # Pausa de fala detectada no servidor
                    if len(self.audio_buffer) >= self.min_speech_duration_bytes:
                        completed_audio = bytes(self.audio_buffer)
                        total_sec = len(completed_audio) / 32000.0
                        print(f"\r\033[K⏹️  [VAD] Pausa detectada ({total_sec:.1f}s de áudio). Processando...", flush=True)
                        self.reset()
                        return True, completed_audio, None
                    else:
                        print(f"\r\033[Kℹ️  [VAD] Ruído descartado ({len(self.audio_buffer)} bytes).", flush=True)
                        self.reset()

        return False, None, partial_audio

    def reset(self):
        self.audio_buffer.clear()
        self.is_speech_active = False
        self.silence_start_time = None
        self.chunk_count = 0
