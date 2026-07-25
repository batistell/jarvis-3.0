# Jarvis 3.0 — Arquitetura Backend

O backend do Jarvis 3.0 é construído em **Python 3.12** utilizando **FastAPI** com concorrência totalmente assíncrona via `asyncio`. Toda a stack de IA (STT, LLM e TTS) roda **nativamente em Python na GPU CUDA local** — sem Ollama, sem Docker, sem servidores externos.

---

## 1. Tecnologias & Bibliotecas

| Biblioteca | Função |
|---|---|
| **FastAPI + Uvicorn** | Framework assíncrono + servidor ASGI |
| **faster-whisper** | STT em GPU CUDA via CTranslate2 (Whisper Large-v3-Turbo) |
| **ctranslate2** | Runtime de inferência para o Qwen 2.5 3B |
| **transformers (AutoTokenizer)** | Tokenização do Qwen 2.5 |
| **edge-tts** | TTS Neural via Microsoft Edge (Remy Multilingual) |
| **PyJWT + cryptography** | Validação JWT Firebase via JWKS do Google |
| **SQLAlchemy 2.0 Async** | ORM assíncrono (SQLite / PostgreSQL) |
| **Alembic** | Migrações de banco de dados |
| **httpx** | Cliente HTTP assíncrono (Home Assistant) |
| **numpy** | Conversão e processamento de áudio PCM |

---

## 2. Configuração (`backend/config.py`)

Todas as configurações são carregadas de variáveis de ambiente via `python-dotenv`:

```python
class Settings:
    # STT — Whisper Large-v3-Turbo: ~1.5GB VRAM, 8x mais rápido que large-v3
    WHISPER_MODEL: str = "large-v3-turbo"      # ou "large-v3" para máxima precisão
    WHISPER_DEVICE: str = "cuda"
    WHISPER_COMPUTE_TYPE: str = "int8_float16"  # Pesos INT8 + acumuladores FP16

    # LLM — Qwen 2.5 3B CTranslate2: ~1.9GB VRAM
    LLM_ENGINE: str = "qwen-native"
    NATIVE_LLM_MODEL: str = "jncraton/Qwen2.5-3B-Instruct-ct2-int8"

    # TTS — Voz Neural multilíngue (fala PT, EN, ES, FR, DE, etc.)
    TTS_ENGINE: str = "edge-tts"
    TTS_VOICE: str = "fr-FR-RemyMultilingualNeural"

    # VAD
    VAD_SILENCE_THRESHOLD_RMS: float = 0.015
    VAD_SILENCE_DURATION_MS: float = 450

    # Segurança
    FIREBASE_PROJECT_ID: str = "jarvis-1006b"
    ALLOWED_EMAILS: list[str] = ["batistell.labs@gmail.com", "gbbts@gmail.com"]

    # System Prompt do Assistente
    JARVIS_SYSTEM_PROMPT: str = "Você é o Jarvis 3.0, ... RESPONDA SEMPRE NO MESMO IDIOMA..."
```

---

## 3. Arquitetura de Engines (Factory Pattern)

Cada serviço de IA é abstraído por uma interface base e instanciado por uma Factory:

```
BaseSTTEngine  ←  FasterWhisperEngine  (padrão: large-v3-turbo CUDA)
                  MockSTTEngine         (testes)

BaseLLMEngine  ←  NativeQwenEngine     (padrão: Qwen 2.5 3B CTranslate2 CUDA)
                  OllamaEngine          (opcional: Ollama SDK)

BaseTTSEngine  ←  EdgeTTSEngine        (padrão: fr-FR-RemyMultilingualNeural)
```

---

## 4. STT — Faster-Whisper com Detecção PT/EN (`backend/stt/engines/faster_whisper_engine.py`)

O Whisper Large-v3-Turbo usa um **two-pass** para garantir transcrições apenas em Português e Inglês:

```python
ALLOWED_LANGUAGES = {"pt", "en"}

def _pick_allowed_language(self, audio_float32) -> str:
    # Passo 1: detect_language() retorna dict de probabilidade de TODOS os idiomas
    lang, all_probs = self.model.detect_language(audio_float32)
    
    if lang in self.ALLOWED_LANGUAGES:
        return lang
    
    # Passo 2: Idioma não permitido → força PT ou EN (maior score)
    pt_score = all_probs.get("pt", 0.0)
    en_score = all_probs.get("en", 0.0)
    forced = "pt" if pt_score >= en_score else "en"
    print(f"🌐 [STT LANG OVERRIDE] '{lang.upper()}' → '{forced.upper()}'")
    return forced

def transcribe_pcm_with_info(self, pcm_bytes: bytes) -> dict:
    forced_lang = self._pick_allowed_language(audio_float32)
    segments, info = self.model.transcribe(
        audio_float32,
        beam_size=1,
        vad_filter=True,
        hallucination_silence_threshold=0.5,
        no_speech_threshold=0.6,
        language=forced_lang  # Sempre PT ou EN
    )
    return {"text": full_text, "language": forced_lang, "probability": prob}
```

**Parâmetros de carregamento otimizados para VRAM:**
```python
WhisperModel(
    model_size_or_path="large-v3-turbo",
    device="cuda",
    compute_type="int8_float16",
    cpu_threads=4,
    num_workers=1,
    local_files_only=True
)
```

---

## 5. Filtro de Alucinações e Ruído (`backend/services/hallucination_filter.py`)

Pipeline de limpeza aplicado a cada transcrição do Whisper:

```python
class HallucinationFilter:
    # 1. Set exato de ~80 frases fantasma que o Whisper alucina em silêncio:
    #    "thank you", "ok", "bye", "never mind", "i love you", "[inaudible]", etc.
    PHANTOM_EXACT = {"thank you", "thank you.", "never mind", ...}
    
    # 2. Regex para padrões mais longos:
    #    legenda por..., subtitles by..., [texto entre colchetes], ♪...♪, etc.
    PHANTOM_PATTERNS = [re.compile(r'...',)]
    
    # 3. Filtro de ruído: < 3 chars alfanuméricos reais, ou apenas tokens de ruído
    @classmethod
    def _is_noise(cls, text: str) -> bool: ...
    
    @classmethod
    def clean_text(cls, text: str) -> str:
        # 1. Exato → 2. Regex → 3. Ruído → 4. Wakeword variants → 5. Fuzzy Jarvis
```

**Variantes fonéticas corrigidas para "Jarvis":**
`gervis`, `garvis`, `jesus`, `javi`, `jair`, `jardim`, `jairis`, `jarviz`, `jabes`, `gervais`, `jarver`, e outras.

---

## 6. LLM — Qwen 2.5 3B Nativo (`backend/llm/engines/native_qwen_engine.py`)

Inferência 100% local em Python sem Ollama:

```python
self.generator = ctranslate2.Generator(
    model_dir,
    device="cuda",
    compute_type="int8_float16",  # ~1.9GB VRAM
    inter_threads=1,              # Stream CUDA único (economia de VRAM)
    intra_threads=4,
    max_queued_batches=1
)
```

**Instrução dinâmica de idioma** — o idioma detectado pelo Whisper é injetado no system prompt:

```python
lang_prompt = (
    f"{settings.JARVIS_SYSTEM_PROMPT}\n"
    f"Instrução Estrita de Idioma: O usuário falou no idioma '{detected_lang.upper()}'. "
    f"Você DEVE responder obrigatoriamente no idioma '{detected_lang.upper()}'."
)
async for chunk in llm_service.generate_stream(text, system_prompt=lang_prompt):
    ...
```

---

## 7. TTS — Edge-TTS Remy Multilingual (`backend/tts/engines/edge_tts_engine.py`)

A síntese é feita via `edge-tts` em memória e o áudio MP3 é enviado ao cliente via WebSocket:

```python
communicate = edge_tts.Communicate(text.strip(), "fr-FR-RemyMultilingualNeural")
buffer = io.BytesIO()
async for chunk in communicate.stream():
    if chunk["type"] == "audio":
        buffer.write(chunk["data"])
audio_bytes = buffer.getvalue()  # MP3 bytes

# Enviado como Base64 pelo WebSocket:
await websocket.send_json({
    "type": "tts_audio",
    "audio": base64.b64encode(audio_bytes).decode()
})
```

O **cliente** decodifica o Base64 e toca o áudio via `AudioContext` (Web Audio API).  
O áudio **não toca na máquina host** — toca no browser do dispositivo conectado.

---

## 8. Monitoramento de Saúde da GPU (`backend/services/health_service.py`)

Endpoints REST para diagnóstico de performance em tempo real:

```
GET  /api/health    → VRAM, temperatura, carga CUDA + latências STT/LLM/TTS
POST /api/health/gc → Força coleta de lixo e limpeza de VRAM
```

**Resposta JSON:**
```json
{
  "gpu": {
    "gpu_name": "NVIDIA GeForce RTX 3060",
    "vram_total_mb": 12288,
    "vram_used_mb": 4464,
    "vram_used_percent": 36.3,
    "gpu_utilization_percent": 12,
    "temperature_c": 51,
    "status": "OPTIMAL"
  },
  "models": {
    "stt": { "model_name": "large-v3-turbo", "latency_ms": 485 },
    "llm": { "model_name": "jncraton/Qwen2.5-3B-Instruct-ct2-int8", "latency_ms": 820 },
    "tts": { "voice": "fr-FR-RemyMultilingualNeural", "latency_ms": 220 }
  }
}
```

---

## 9. WebSocket de Voz (`/ws/voice`)

### Fluxo Completo por Turno de Voz:

```
[Microfone]  →  PCM chunks (200ms)  →  [WebSocket]
                                          ↓
                                     BackendVADDetector (RMS)
                                          ↓ (pausa detectada)
                                    FasterWhisperEngine.transcribe_pcm_with_info()
                                     → detect_language (PT/EN)
                                     → transcribe(language=forced_lang)
                                     → HallucinationFilter.clean_text()
                                          ↓ (texto limpo)
                                    NativeQwenEngine.generate_stream(text, lang_prompt)
                                     → ctranslate2.Generator (streamed tokens)
                                          ↓ (resposta completa)
                                    EdgeTTSEngine.synthesize(response)
                                     → edge-tts MP3 bytes → Base64
                                          ↓
                                     [WebSocket] → [AudioContext] → 🔊 Fala no Browser
```

---

## 10. Segurança e Autenticação

O backend valida o ID Token do Firebase via **JWKS** do Google sem necessidade de service account:

```python
JWKS_URL = "https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com"
jwk_client = PyJWKClient(JWKS_URL)

async def validate_firebase_token(token: str) -> str | None:
    signing_key = jwk_client.get_signing_key_from_jwt(token)
    payload = jwt.decode(token, signing_key.key, algorithms=["RS256"],
                         audience=FIREBASE_PROJECT_ID, ...)
    email = payload.get("email")
    if email in settings.ALLOWED_EMAILS:
        return email
    return None  # Rejeita conexão WebSocket com código 1008
```
