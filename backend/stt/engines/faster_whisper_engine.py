import sys
import io
import os
import site
import time
import numpy as np
from faster_whisper import WhisperModel
from backend.config import settings
from backend.stt.base import BaseSTTEngine

# Registrar DLLs do CUDA (nvidia-cublas, nvidia-cudnn, nvidia-cuda-nvrtc) no PATH/DLL directory no Windows
try:
    for site_pkg in site.getsitepackages():
        nvidia_dir = os.path.join(site_pkg, 'nvidia')
        if os.path.isdir(nvidia_dir):
            for root, dirs, files in os.walk(nvidia_dir):
                if root.endswith('bin'):
                    if hasattr(os, 'add_dll_directory'):
                        try:
                            os.add_dll_directory(root)
                        except Exception:
                            pass
                    os.environ['PATH'] = root + ';' + os.environ.get('PATH', '')
except Exception as e:
    print(f"⚠️ Warning ao carregar DLLs do CUDA: {e}")

# Garantir UTF-8 no console do Windows
if hasattr(sys.stdout, 'buffer') and getattr(sys.stdout, 'encoding', '').lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'buffer') and getattr(sys.stderr, 'encoding', '').lower() != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


class FasterWhisperEngine(BaseSTTEngine):
    """
    Módulo de Reconhecimento de Fala (STT) utilizando o motor CTranslate2 (faster-whisper).
    Suporta aceleração por GPU CUDA, fallback automático e prompt inicial com vocabulário customizado.
    """

    def __init__(self):
        self.model: WhisperModel | None = None
        self._is_loading = False

    def load_model(self) -> None:
        """Carrega o modelo Faster-Whisper na GPU CUDA (ou CPU fallback)."""
        if self.model is None and not self._is_loading:
            self._is_loading = True
            print("=" * 65)
            print(f"⚡ [STT ENGINE] Carregando Faster-Whisper '{settings.WHISPER_MODEL}' ({settings.WHISPER_DEVICE} / {settings.WHISPER_COMPUTE_TYPE})...")
            print("   Aguarde a inicialização do modelo na VRAM da GPU...")
            print("=" * 65, flush=True)
            
            try:
                self.model = WhisperModel(
                    settings.WHISPER_MODEL,
                    device=settings.WHISPER_DEVICE,
                    compute_type=settings.WHISPER_COMPUTE_TYPE,
                    cpu_threads=4,       # Threads CPU para pré/pós-processamento (libera GPU)
                    num_workers=1,       # Workers de I/O do CTranslate2
                    download_root=None,
                    local_files_only=True  # Zero verificações HuggingFace na rede
                )
                print("=" * 65)
                print(f"🚀 [WHISPER ULTRA-FAST READY] Modelo '{settings.WHISPER_MODEL}' pronto em GPU CUDA!")
                print("🎧 [SERVER LISTENING] Aguardando streaming de áudio do microfone...")
                print("=" * 65, flush=True)
            except Exception as e:
                print(f"⚠️ [STT ENGINE] Erro ao carregar em CUDA '{settings.WHISPER_MODEL}': {e}")
                print("   Tentando fallback para CPU int8...")
                try:
                    self.model = WhisperModel(settings.WHISPER_MODEL, device="cpu", compute_type="int8")
                    print(f"✅ [STT ENGINE] Modelo '{settings.WHISPER_MODEL}' pronto no CPU fallback!", flush=True)
                except Exception as ex:
                    print(f"❌ [STT ENGINE] Falha crítica ao carregar modelo Whisper: {ex}", flush=True)
            finally:
                self._is_loading = False

    def transcribe_pcm(self, pcm_bytes: bytes) -> str:
        """Transcreve o áudio final acumulado com medição de tempo e filtro VAD."""
        """Transcreve os bytes de áudio PCM finais e retorna o texto transcrito."""
        res = self.transcribe_pcm_with_info(pcm_bytes)
        return res.get("text", "")

    def transcribe_pcm_with_info(self, pcm_bytes: bytes) -> dict:
        """Transcreve o áudio PCM final com detecção automática de idioma do Whisper Large-v3."""
        if not pcm_bytes or self.model is None:
            self.load_model()

        if self.model is None:
            return {"text": "", "language": "pt", "probability": 0.0}

        start_time = time.time()
        pcm_int16 = np.frombuffer(pcm_bytes, dtype=np.int16)
        audio_float32 = pcm_int16.astype(np.float32) / 32768.0
        duration_sec = len(audio_float32) / 16000.0

        try:
            segments, info = self.model.transcribe(
                audio_float32,
                beam_size=1,
                vad_filter=True,
                condition_on_previous_text=False,
                hallucination_silence_threshold=0.5,
                no_speech_threshold=0.6,
                initial_prompt=settings.WHISPER_INITIAL_PROMPT if settings.WHISPER_INITIAL_PROMPT else None,
                language=None  # Detecção automática multilíngue do Large-v3!
            )

            transcribed_fragments = [seg.text.strip() for seg in segments if seg.text.strip()]
            raw_text = " ".join(transcribed_fragments).strip()
            
            from backend.services.hallucination_filter import hallucination_filter
            full_text = hallucination_filter.clean_text(raw_text)
            
            elapsed_ms = (time.time() - start_time) * 1000.0
            from backend.services.health_service import health_service
            health_service.record_stt_latency(elapsed_ms)
            
            detected_lang = getattr(info, "language", "pt")
            prob = getattr(info, "language_probability", 1.0)

            if full_text:
                print(f"✨  [STT {elapsed_ms:.0f}ms | {duration_sec:.1f}s áudio | Idioma: {detected_lang.upper()} ({prob*100:.0f}%)]: \"{full_text}\"\n", flush=True)
            else:
                print(f"ℹ️  [STT {elapsed_ms:.0f}ms]: (Silêncio / sem fala identificada / alucinação filtrada)\n", flush=True)

            return {
                "text": full_text,
                "language": detected_lang,
                "probability": prob
            }

        except Exception as e:
            print(f"❌ [STT ERROR] Erro durante a transcrição: {e}", flush=True)
            return {"text": "", "language": "pt", "probability": 0.0}

    def transcribe_partial_pcm(self, pcm_bytes: bytes) -> str:
        """Transcrição parcial ultrarrápida (live streaming) para áudio em tempo real."""
        if not pcm_bytes or self.model is None:
            return ""

        pcm_int16 = np.frombuffer(pcm_bytes, dtype=np.int16)
        audio_float32 = pcm_int16.astype(np.float32) / 32768.0

        try:
            segments, info = self.model.transcribe(
                audio_float32,
                beam_size=1,
                vad_filter=False,
                condition_on_previous_text=False,
                initial_prompt=settings.WHISPER_INITIAL_PROMPT if settings.WHISPER_INITIAL_PROMPT else None,
                language=None
            )
            fragments = [seg.text.strip() for seg in segments if seg.text.strip()]
            raw = " ".join(fragments).strip()
            from backend.services.hallucination_filter import hallucination_filter
            return hallucination_filter.clean_text(raw)
        except Exception:
            return ""
