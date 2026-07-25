import asyncio
from abc import ABC, abstractmethod

class BaseSTTEngine(ABC):
    """
    Interface Base Abstrata para Motores de Reconhecimento de Fala (STT).
    Permite alternar, reordenar ou adicionar novos motores (Faster-Whisper, Whisper.cpp, etc).
    """

    @abstractmethod
    def load_model(self) -> None:
        """Carrega o modelo de STT na memória/GPU."""
        pass

    @abstractmethod
    def transcribe_pcm(self, pcm_bytes: bytes) -> str:
        """Transcreve os bytes de áudio PCM finais de forma síncrona."""
        pass

    @abstractmethod
    def transcribe_partial_pcm(self, pcm_bytes: bytes) -> str:
        """Transcreve trechos parciais em tempo real (live streaming)."""
        pass

    async def transcribe_pcm_async(self, pcm_bytes: bytes) -> str:
        """Invoca a transcrição final de forma assíncrona em uma thread separada."""
        return await asyncio.to_thread(self.transcribe_pcm, pcm_bytes)

    async def transcribe_partial_async(self, pcm_bytes: bytes) -> str:
        """Invoca a transcrição parcial em tempo real de forma assíncrona."""
        return await asyncio.to_thread(self.transcribe_partial_pcm, pcm_bytes)
