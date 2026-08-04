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

    # Idiomas permitidos para detecção — apenas PT e EN
    ALLOWED_LANGUAGES = {"pt", "en"}

    def _pick_allowed_language(self, audio_float32) -> str:
        """
        Detecta o idioma do áudio e força para PT ou EN.
        Usa model.detect_language() para obter probabilidades de todos os idiomas,
        então seleciona o de maior score dentro de {pt, en}.
        """
        try:
            lang, all_probs = self.model.detect_language(audio_float32)
            if lang in self.ALLOWED_LANGUAGES:
                return lang
            # O idioma detectado não é PT nem EN — escolhe qual dos dois tem maior probabilidade
            pt_score = all_probs.get("pt", 0.0)
            en_score = all_probs.get("en", 0.0)
            forced = "pt" if pt_score >= en_score else "en"
            print(f"🌐 [STT LANG OVERRIDE] '{lang.upper()}' → '{forced.upper()}' (pt={pt_score:.2f} en={en_score:.2f})", flush=True)
            return forced
        except Exception:
            return "pt"

    @staticmethod
    def _preprocess_audio(audio_float32: np.ndarray) -> np.ndarray:
        """
        Pipeline leve de limpeza de sinal de áudio:
        1. Filtro Passa-Alta IIR (80Hz): Remove ruídos graves de fundo (ventoinhas/ar-condicionado).
        2. Normalização suave de pico (sem amplificação excessiva de ruído de fundo).
        """
        if len(audio_float32) == 0:
            return audio_float32

        # 1. Filtro Passa-Alta (IIR 80Hz a 16kHz)
        y = np.zeros_like(audio_float32)
        alpha = 0.9687
        for i in range(1, len(audio_float32)):
            y[i] = alpha * (y[i-1] + audio_float32[i] - audio_float32[i-1])

        # 2. Normalização suave (apenas impede clipping > 0.95, NUNCA amplifica ruído de fundo)
        peak = np.max(np.abs(y))
        if peak > 0.95:
            y = y * (0.95 / peak)

        return y

    def transcribe_pcm_with_info(self, pcm_bytes: bytes, custom_prompt: str | None = None) -> dict:
        """Transcreve o áudio PCM limpando ruído grave e mantendo alta fidelidade fonética."""

        if not pcm_bytes or self.model is None:
            self.load_model()

        if self.model is None:
            return {"text": "", "language": "pt", "probability": 0.0}

        start_time = time.time()
        pcm_int16 = np.frombuffer(pcm_bytes, dtype=np.int16)
        audio_raw = pcm_int16.astype(np.float32) / 32768.0
        duration_sec = len(audio_raw) / 16000.0

        # Aplica o pipeline de limpeza e condicionamento de sinal de áudio
        audio_float32 = self._preprocess_audio(audio_raw)

        try:
            # Passo 1: detecção rápida de idioma → restrita a PT e EN
            forced_lang = self._pick_allowed_language(audio_float32)

            # Constrói o initial_prompt de domínio (Jarvis + Comandos + Vocabulário HA)
            default_prompt = (
                settings.WHISPER_INITIAL_PROMPT or
                "Jarvis assistente. Comandos de automação residencial do Home Assistant: ligar, desligar, alternar, acender, apagar a luz do escritório, Office Light, luz da sala, cozinha, quarto, banheiro, tomada, dispositivo."
            )
            prompt = f"{default_prompt} {custom_prompt}".strip() if custom_prompt else default_prompt

            # Passo 2: transcrição com GPU beam_size=5 e best_of=5 para máxima fidelidade fonética
            segments, info = self.model.transcribe(
                audio_float32,
                beam_size=5,
                best_of=5,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=350),
                condition_on_previous_text=False,
                hallucination_silence_threshold=0.5,
                no_speech_threshold=0.6,
                initial_prompt=prompt,
                language=forced_lang
            )


            transcribed_fragments = [seg.text.strip() for seg in segments if seg.text.strip()]
            raw_text = " ".join(transcribed_fragments).strip()
            
            from backend.services.hallucination_filter import hallucination_filter
            full_text = hallucination_filter.clean_text(raw_text)
            
            elapsed_ms = (time.time() - start_time) * 1000.0
            from backend.services.health_service import health_service
            health_service.record_stt_latency(elapsed_ms)
            
            prob = getattr(info, "language_probability", 1.0)

            if full_text:
                print(f"✨  [STT {elapsed_ms:.0f}ms | {duration_sec:.1f}s áudio | Idioma: {forced_lang.upper()} ({prob*100:.0f}%)]: \"{full_text}\"\n", flush=True)
            else:
                print(f"ℹ️  [STT {elapsed_ms:.0f}ms]: (Silêncio / sem fala identificada / alucinação filtrada)\n", flush=True)

            return {
                "text": full_text,
                "language": forced_lang,
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
            forced_lang = self._pick_allowed_language(audio_float32)
            segments, info = self.model.transcribe(
                audio_float32,
                beam_size=1,
                vad_filter=False,
                condition_on_previous_text=False,
                initial_prompt=settings.WHISPER_INITIAL_PROMPT if settings.WHISPER_INITIAL_PROMPT else None,
                language=forced_lang
            )
            fragments = [seg.text.strip() for seg in segments if seg.text.strip()]
            raw = " ".join(fragments).strip()
            from backend.services.hallucination_filter import hallucination_filter
            return hallucination_filter.clean_text(raw)
        except Exception:
            return ""
