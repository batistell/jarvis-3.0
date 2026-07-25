import sys
import io
import asyncio
import numpy as np
from faster_whisper import WhisperModel
from backend.config import settings

import os
import site

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

# Garantir UTF-8 no console do Windows para evitar erros de codificação de caractere
if hasattr(sys.stdout, 'buffer') and getattr(sys.stdout, 'encoding', '').lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'buffer') and getattr(sys.stderr, 'encoding', '').lower() != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

class STTService:
    """
    Serviço de transcrição de voz em memória usando faster-whisper (Whisper Large por padrão).
    Pré-carrega o modelo no início da aplicação e transcreve o áudio em tempo real com logs no console.
    """

    def __init__(self):
        self.model: WhisperModel | None = None
        self._is_loading = False

    def load_model(self):
        """Pré-carrega o modelo Whisper na GPU CUDA (ou CPU fallback) na inicialização do servidor."""
        if self.model is None and not self._is_loading:
            self._is_loading = True
            print("=" * 65)
            print(f"⚡ [STT INITIALIZATION] Carregando modelo Whisper '{settings.WHISPER_MODEL}' ({settings.WHISPER_DEVICE} / {settings.WHISPER_COMPUTE_TYPE})...")
            print("   Aguarde a inicialização do modelo na VRAM da GPU...")
            print("=" * 65, flush=True)
            
            try:
                self.model = WhisperModel(
                    settings.WHISPER_MODEL,
                    device=settings.WHISPER_DEVICE,
                    compute_type=settings.WHISPER_COMPUTE_TYPE
                )
                print("=" * 65)
                print(f"🚀 [WHISPER ULTRA-FAST READY] Modelo '{settings.WHISPER_MODEL}' pronto em GPU CUDA!")
                print("🎧 [SERVER LISTENING] Aguardando streaming de áudio do microfone...")
                print("=" * 65, flush=True)
            except Exception as e:
                print(f"⚠️ [STT INITIALIZATION] Erro ao carregar em CUDA '{settings.WHISPER_MODEL}': {e}")
                print("   Tentando fallback para CPU int8...")
                try:
                    self.model = WhisperModel(settings.WHISPER_MODEL, device="cpu", compute_type="int8")
                    print(f"✅ [STT INITIALIZATION] Modelo '{settings.WHISPER_MODEL}' pronto no CPU fallback!", flush=True)
                except Exception as ex:
                    print(f"❌ [STT INITIALIZATION] Falha crítica ao carregar modelo Whisper: {ex}", flush=True)
            finally:
                self._is_loading = False

    def transcribe_pcm(self, pcm_bytes: bytes) -> str:
        """
        Converte os bytes PCM 16-bit Mono (16kHz) em NumPy float32 e executa a transcrição
        com parâmetros otimizados para latência mínima (< 200ms).
        """
        if not pcm_bytes:
            return ""

        if self.model is None:
            self.load_model()

        if self.model is None:
            print("❌ [STT ERROR] Modelo Whisper não está disponível.", flush=True)
            return ""

        import time
        start_time = time.time()

        # Converte PCM 16-bit signed integer para float32 (-1.0 a 1.0)
        pcm_int16 = np.frombuffer(pcm_bytes, dtype=np.int16)
        audio_float32 = pcm_int16.astype(np.float32) / 32768.0

        duration_sec = len(audio_float32) / 16000.0
        try:
            segments, info = self.model.transcribe(
                audio_float32,
                beam_size=1, # Greedy decoding ultra-rápido
                vad_filter=True, # Filtra silêncios internos no buffer
                condition_on_previous_text=False,
                initial_prompt=settings.WHISPER_INITIAL_PROMPT,
                language="pt"
            )

            transcribed_fragments = [seg.text.strip() for seg in segments if seg.text.strip()]
            full_text = " ".join(transcribed_fragments).strip()
            elapsed_ms = (time.time() - start_time) * 1000.0

            if full_text:
                print(f"✨  [STT {elapsed_ms:.0f}ms | {duration_sec:.1f}s áudio]: \"{full_text}\"\n", flush=True)
            else:
                print(f"ℹ️  [STT {elapsed_ms:.0f}ms]: (Silêncio / sem fala identificada)\n", flush=True)

            return full_text

        except Exception as e:
            print(f"❌ [STT ERROR] Erro durante a transcrição: {e}", flush=True)
            return ""

    async def transcribe_pcm_async(self, pcm_bytes: bytes) -> str:
        return await asyncio.to_thread(self.transcribe_pcm, pcm_bytes)

    def transcribe_partial_pcm(self, pcm_bytes: bytes) -> str:
        """
        Transcrição parcial ultrarrápida (live streaming) enquanto o usuário fala.
        """
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
                initial_prompt=settings.WHISPER_INITIAL_PROMPT,
                language="pt"
            )
            fragments = [seg.text.strip() for seg in segments if seg.text.strip()]
            return " ".join(fragments).strip()
        except Exception:
            return ""

    async def transcribe_partial_async(self, pcm_bytes: bytes) -> str:
        return await asyncio.to_thread(self.transcribe_partial_pcm, pcm_bytes)

stt_service = STTService()
