import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # Seleção de Motor STT ("faster-whisper", "mock", etc)
    STT_ENGINE: str = os.getenv("STT_ENGINE", "faster-whisper")
    
    # STT Faster Whisper (Large-v3 completo + CUDA por padrão para máxima precisão)
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "large-v3")
    WHISPER_DEVICE: str = os.getenv("WHISPER_DEVICE", "cuda")
    WHISPER_COMPUTE_TYPE: str = os.getenv("WHISPER_COMPUTE_TYPE", "float16")
    WHISPER_INITIAL_PROMPT: str = os.getenv(
        "WHISPER_INITIAL_PROMPT",
        "Jarvis assistente virtual de inteligência artificial local. comandos de voz em português e inglês."
    )
    
    # Seleção e Configuração de Motor LLM (Nativo Python em Memória, Ollama, Qwen2.5)
    LLM_ENGINE: str = os.getenv("LLM_ENGINE", "qwen-native")
    NATIVE_LLM_MODEL: str = os.getenv("NATIVE_LLM_MODEL", "jncraton/Qwen2.5-3B-Instruct-ct2-int8")
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
    JARVIS_SYSTEM_PROMPT: str = os.getenv(
        "JARVIS_SYSTEM_PROMPT",
        "Você é o Jarvis 3.0, um assistente pessoal conciso e inteligente. Responda em português de forma direta e curta para ser lido em voz alta pelo sistema TTS."
    )
    
    # VAD backend config
    VAD_SILENCE_THRESHOLD_RMS: float = float(os.getenv("VAD_SILENCE_THRESHOLD_RMS", "0.015"))
    VAD_SILENCE_DURATION_MS: float = float(os.getenv("VAD_SILENCE_DURATION_MS", "450"))
    
    # Security
    FIREBASE_PROJECT_ID: str = os.getenv("FIREBASE_PROJECT_ID", "jarvis-1006b")
    ALLOWED_EMAILS: list[str] = [
        e.strip() for e in os.getenv("ALLOWED_EMAILS", "batistell.labs@gmail.com,gbbts@gmail.com").split(",") if e.strip()
    ]

settings = Settings()
