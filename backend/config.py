import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # Seleção de Motor STT ("faster-whisper", "mock", etc)
    STT_ENGINE: str = os.getenv("STT_ENGINE", "faster-whisper")
    
    # STT Faster Whisper
    # Opções: "large-v3" (3.1GB VRAM, máxima precisão acústica em PT), "large-v3-turbo" (1.5GB VRAM)
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "large-v3")

    WHISPER_DEVICE: str = os.getenv("WHISPER_DEVICE", "cuda")
    # int8_float16 = pesos INT8 + acumuladores FP16 → menor VRAM, mais rápido que pure float16
    WHISPER_COMPUTE_TYPE: str = os.getenv("WHISPER_COMPUTE_TYPE", "int8_float16")
    WHISPER_INITIAL_PROMPT: str | None = os.getenv("WHISPER_INITIAL_PROMPT", None)
    
    # Seleção e Configuração de Motor LLM (Nativo Python em Memória, Ollama, Qwen2.5)
    LLM_ENGINE: str = os.getenv("LLM_ENGINE", "qwen-native")
    NATIVE_LLM_MODEL: str = os.getenv("NATIVE_LLM_MODEL", "jncraton/Qwen2.5-3B-Instruct-ct2-int8")
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
    JARVIS_SYSTEM_PROMPT: str = os.getenv(
        "JARVIS_SYSTEM_PROMPT",
        "Você é o Jarvis 3.0, um assistente pessoal conciso e fluente integrado ao Home Assistant. REGRA DE SEGURANÇA E CONFIABILIDADE: O acionamento de hardware é feito EXCLUSIVAMENTE pela plataforma do sistema via validação de sensores. Você É ABSOLUTAMENTE PROIBIDO de iniciar respostas com 'Confirmado pelo sensor' ou dizer 'O dispositivo ... foi ligado/desligado'. Essas confirmações são reservadas ao sistema. Se a fala do usuário for um ruído, transcrição incompleta ou termo confuso (ex: 'Ligi', 'Lídia Luz'), apenas responda amigavelmente: 'Desculpe, não entendi o comando. Como posso ajudar?'. RESPONDA NO MESMO IDIOMA DO USUÁRIO."
    )



    
    # Seleção e Configuração de Motor TTS (Edge-TTS Multilíngue Remy)
    TTS_ENGINE: str = os.getenv("TTS_ENGINE", "edge-tts")
    TTS_VOICE: str = os.getenv("TTS_VOICE", "fr-FR-RemyMultilingualNeural")
    
    # VAD backend config
    VAD_SILENCE_THRESHOLD_RMS: float = float(os.getenv("VAD_SILENCE_THRESHOLD_RMS", "0.015"))
    VAD_SILENCE_DURATION_MS: float = float(os.getenv("VAD_SILENCE_DURATION_MS", "450"))
    
    # Security
    FIREBASE_PROJECT_ID: str = os.getenv("FIREBASE_PROJECT_ID", "jarvis-1006b")
    ALLOWED_EMAILS: list[str] = [
        e.strip() for e in os.getenv("ALLOWED_EMAILS", "batistell.labs@gmail.com,gbbts@gmail.com").split(",") if e.strip()
    ]

    # Home Assistant API Integration
    HA_URL: str = os.getenv("HA_URL", os.getenv("HOME_ASSISTANT_URL", os.getenv("JARVIS_HA_URL", "http://homeassistant.local:8123"))).rstrip("/")
    HA_TOKEN: str = os.getenv("HA_TOKEN", os.getenv("HOME_ASSISTANT_TOKEN", os.getenv("JARVIS_HA_TOKEN", "")))

settings = Settings()


