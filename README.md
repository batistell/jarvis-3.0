# Jarvis 3.0 — Assistente Pessoal Inteligente em Python

O **Jarvis 3.0** é um assistente pessoal por voz e texto, **always-listening**, construído inteiramente em **Python (FastAPI)** no backend e **React (Vite + TypeScript)** no frontend. Toda a pipeline de IA — reconhecimento de voz, inferência do modelo de linguagem e síntese de fala — executa **nativamente em Python na GPU CUDA local**, sem Ollama, sem Docker e sem servidores externos.

---

## 🚀 Funcionalidades Principais

- **STT multilíngue (PT/EN) com Whisper Large-v3-Turbo**: Reconhecimento de voz em tempo real via `faster-whisper` + CTranslate2 em GPU CUDA. Detecção automática de idioma restrita a Português e Inglês com two-pass (`detect_language` → `transcribe`).
- **LLM Nativo com Qwen 2.5 3B Instruct**: Inferência 100% local via CTranslate2 (`ctranslate2.Generator`) em GPU CUDA. Sem Ollama. Streaming de tokens em tempo real para o frontend.
- **TTS Neural Multilíngue (Remy)**: Síntese de voz via Microsoft Edge TTS (`edge-tts`) com a voz `fr-FR-RemyMultilingualNeural`, capaz de sintetizar PT e EN com entonação natural.
- **Resposta no Idioma do Usuário**: O Whisper detecta o idioma falado (PT ou EN) e instrui o Qwen a responder obrigatoriamente no mesmo idioma. A voz Remy sintetiza a resposta no idioma correspondente.
- **Filtro de Alucinações e Ruído**: Pipeline `HallucinationFilter` que descarta automaticamente frases fantasma do Whisper em silêncio ("Thank you", "Ok", "Bye", símbolos musicais, etc.), filtra ruído puro e normaliza variações fonéticas de "Jarvis".
- **Reprodução de Áudio no Navegador (Web Audio API)**: O áudio sintetizado é enviado como Base64 via WebSocket e reproduzido pelo cliente via `AudioContext`. O áudio **não toca na máquina host** — toca no dispositivo que acessa a interface web.
- **Seleção Dinâmica de Microfone**: O usuário pode selecionar e trocar o microfone ativo diretamente no HUD da interface.
- **Monitoramento de Saúde da GPU em Tempo Real**: Widget no frontend exibe VRAM, temperatura, carga CUDA e latência dos modelos STT, LLM e TTS em tempo real.
- **Segurança Local Robusta**: Autenticação via **Firebase Auth** (Google Sign-In) + validação criptográfica de tokens JWT via JWKS. Lista branca de e-mails autorizados.

---

## 🛠️ Stack Tecnológico

| Camada | Tecnologia |
|---|---|
| **Backend** | Python 3.12, FastAPI, Uvicorn, asyncio |
| **STT** | `faster-whisper` + CTranslate2 + CUDA — modelo `large-v3-turbo` |
| **LLM** | CTranslate2 `ctranslate2.Generator` — `jncraton/Qwen2.5-3B-Instruct-ct2-int8` |
| **TTS** | `edge-tts` — voz `fr-FR-RemyMultilingualNeural` (Microsoft Neural) |
| **VAD** | Backend VAD via RMS + janela de silêncio configurável |
| **Frontend** | React 18 + Vite + TypeScript + Web Audio API |
| **Autenticação** | Firebase Auth (Google) + JWKS + PyJWT + whitelist de e-mails |
| **Banco de Dados** | SQLite + SQLAlchemy 2.0 Async + Alembic |
| **GPU** | NVIDIA CUDA — testado em RTX 3060 12GB (Driver 591.86, CUDA 13.1) |

---

## 📁 Estrutura de Pastas

```text
jarvis-3.0/
├── AGENTS.md                        # Regras globais para agentes de IA
├── README.md                        # Este arquivo
├── .env.example                     # Modelo de variáveis de ambiente
├── jarvis.ps1 / jarvis.cmd          # Scripts de boot (encerra zumbis, sobe backend + frontend)
├── requirements.txt                 # Dependências Python
├── backend/
│   ├── main.py                      # FastAPI app, WebSocket /ws/voice, endpoints REST
│   ├── config.py                    # Settings centralizados (WHISPER_MODEL, TTS_VOICE, etc.)
│   ├── llm/
│   │   ├── base.py                  # Interface abstrata BaseLLMEngine
│   │   ├── factory.py               # LLMFactory (seleção de engine)
│   │   └── engines/
│   │       └── native_qwen_engine.py # CTranslate2 Qwen 2.5 3B nativo na GPU
│   ├── stt/
│   │   ├── base.py                  # Interface abstrata BaseSTTEngine
│   │   ├── factory.py               # STTFactory (seleção de engine)
│   │   └── engines/
│   │       └── faster_whisper_engine.py # Whisper Large-v3-Turbo CUDA + two-pass PT/EN
│   ├── tts/
│   │   ├── base.py                  # Interface abstrata BaseTTSEngine
│   │   ├── factory.py               # TTSFactory (seleção de engine)
│   │   └── engines/
│   │       └── edge_tts_engine.py   # Edge-TTS Remy Multilingual
│   └── services/
│       ├── stt_service.py           # Singleton STT
│       ├── llm_service.py           # Singleton LLM
│       ├── tts_service.py           # Singleton TTS
│       ├── vad_service.py           # VAD (Voice Activity Detection)
│       ├── hallucination_filter.py  # Filtro de alucinações/ruído do Whisper
│       ├── health_service.py        # Monitoramento GPU + latências dos modelos
│       └── auth_service.py          # Validação JWT Firebase via JWKS
├── frontend/
│   └── src/
│       ├── App.tsx                  # App principal, WebSocket, Audio Queue Player
│       ├── components/
│       │   ├── Header.tsx           # HUD superior com status de conexão
│       │   ├── VoiceOrb.tsx         # Orb central animado (idle/listening/thinking/speaking)
│       │   ├── ChatWindow.tsx       # Timeline de mensagens com streaming de tokens
│       │   ├── MessageInput.tsx     # Input de texto + botão de gravação
│       │   ├── MicrophoneSelector.tsx # Seletor dinâmico de microfone no HUD
│       │   ├── GPUHealthWidget.tsx  # Widget de monitoramento GPU e latência dos modelos
│       │   └── ControlPanel.tsx     # Ações rápidas
│       └── hooks/
│           └── useVoiceRecorder.ts  # Captura de microfone, VAD e envio de chunks PCM
└── docs/
    ├── architecture/                # Arquitetura técnica detalhada
    ├── decisions/                   # ADRs (Architecture Decision Records)
    ├── modules/                     # Especificações de domínio
    ├── api/                         # Contratos de API WebSocket e REST
    └── workflows/                   # Fluxos operacionais
```

---

## ⚙️ Configuração e Execução

### 1. Variáveis de Ambiente (`.env`)

Copie o `.env.example` e configure:

```env
FIREBASE_PROJECT_ID=jarvis-1006b
ALLOWED_EMAILS=seu@gmail.com

# STT (Whisper) — large-v3-turbo usa ~1.5GB VRAM (vs 3.1GB do large-v3)
WHISPER_MODEL=large-v3-turbo
WHISPER_COMPUTE_TYPE=int8_float16

# LLM — Qwen 2.5 3B int8 usa ~1.9GB VRAM
NATIVE_LLM_MODEL=jncraton/Qwen2.5-3B-Instruct-ct2-int8

# TTS — Voz multilíngue (fala PT, EN, ES, FR, etc.)
TTS_VOICE=fr-FR-RemyMultilingualNeural
```

### 2. Instalar Dependências Python

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Instalar Dependências Frontend

```powershell
cd frontend
npm install
cd ..
```

### 4. Executar o Jarvis

```powershell
.\jarvis
```

O script:
1. Encerra processos zumbis anteriores nas portas 8000/5173 (liberando VRAM da GPU)
2. Inicia o servidor Vite (frontend) em segundo plano
3. Abre o Chrome em modo app (`http://localhost:5173`)
4. Inicia o backend FastAPI (`http://localhost:8000`)

---

## 📡 Endpoints

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/` | Status geral do backend |
| `WS` | `/ws/voice?token=JWT` | WebSocket bidirecional de voz |
| `GET` | `/api/health` | Métricas da GPU e status dos modelos |
| `POST` | `/api/health/gc` | Força coleta de lixo e limpeza de VRAM |

---

## 🔊 Payloads WebSocket

**Backend → Frontend:**

| Tipo | Payload | Descrição |
|---|---|---|
| `stt_status` | `{"status": "transcribing"}` | Backend iniciou transcrição |
| `stt_result` | `{"text": "...", "language": "pt"}` | Texto transcrito + idioma detectado |
| `llm_status` | `{"status": "generating"}` | LLM iniciou geração |
| `llm_chunk` | `{"text": "..."}` | Token de resposta em streaming |
| `llm_result` | `{"text": "..."}` | Resposta completa do LLM |
| `tts_audio` | `{"audio": "<base64_mp3>"}` | Áudio MP3 sintetizado em Base64 |
| `partial_stt` | `{"text": "..."}` | Transcrição parcial em tempo real |

**Frontend → Backend:**

| Tipo | Payload | Descrição |
|---|---|---|
| `bytes` | PCM 16-bit Mono 16kHz | Chunk de áudio do microfone |
| `text_message` | `{"text": "..."}` | Mensagem digitada |

---

## 🧠 VRAM Estimada por Modelo (RTX 3060 12GB)

| Modelo | VRAM |
|---|---|
| Whisper Large-v3-Turbo (int8_float16) | ~1.5 GB |
| Qwen 2.5 3B int8 (CTranslate2) | ~1.9 GB |
| **Total Jarvis** | **~3.4 GB** |
| Chrome + Discord + IDE + sistema | ~7.0–8.0 GB |
| **Total em uso real (típico)** | **~11–12 GB** |

> O consumo elevado da VRAM não é dos modelos de IA, mas sim do Windows WDDM (contextos gráficos de Chrome, Edge, Discord, IDE, etc.)