from backend.tts.factory import TTSFactory

class TTSService:
    """
    Fachada Singleton para síntese de voz TTS.
    Gera o áudio das respostas da IA para serem enviadas via WebSocket e reproduzidas no navegador cliente.
    """
    def __init__(self):
        self.engine = TTSFactory.create_engine()

    async def synthesize_async(self, text: str) -> bytes:
        """Sintetiza o texto em áudio MP3/WAV."""
        return await self.engine.synthesize(text)

tts_service = TTSService()
