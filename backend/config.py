import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # STT Faster Whisper
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "base")
    WHISPER_DEVICE: str = os.getenv("WHISPER_DEVICE", "cpu")
    WHISPER_COMPUTE_TYPE: str = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
    
    # VAD backend config
    VAD_SILENCE_THRESHOLD_RMS: float = float(os.getenv("VAD_SILENCE_THRESHOLD_RMS", "0.015"))
    VAD_SILENCE_DURATION_MS: float = float(os.getenv("VAD_SILENCE_DURATION_MS", "800"))
    
    # Security
    FIREBASE_PROJECT_ID: str = os.getenv("FIREBASE_PROJECT_ID", "jarvis-1006b")
    ALLOWED_EMAILS: list[str] = [
        e.strip() for e in os.getenv("ALLOWED_EMAILS", "batistell.labs@gmail.com,gbbts@gmail.com").split(",") if e.strip()
    ]

settings = Settings()
