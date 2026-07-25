"""
Servidor Wyoming Protocol para Jarvis 3.0 (STT & TTS Nativo do Home Assistant)
Escuta em portas TCP locais:
- STT (Whisper Large-v3-Turbo CUDA): porta 10300
- TTS (Edge-TTS Remy Multilingual): porta 10200
"""
import asyncio
import logging
from wyoming.server import AsyncServer, AsyncEventHandler
from wyoming.event import Event
from wyoming.info import Info, Attribution, Describe, AsrProgram, AsrModel, TtsProgram, TtsVoice
from wyoming.asr import Transcribe, Transcript
from wyoming.tts import Synthesize
from wyoming.audio import AudioChunk, AudioStart, AudioStop
from backend.services.stt_service import stt_service
from backend.services.tts_service import tts_service

LOGGER = logging.getLogger(__name__)


class WyomingSTTHandler(AsyncEventHandler):
    """Handler para requisições de Speech-to-Text (STT) do Home Assistant."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.audio_data = bytearray()

    async def handle_event(self, event: Event) -> bool:
        if Describe.is_type(event.type):
            info = Info(
                asr=[
                    AsrProgram(
                        name="Jarvis 3.0 Whisper STT",
                        attribution=Attribution(name="Batistell", url="https://github.com/batistell/home-assistant"),
                        installed=True,
                        description="Jarvis 3.0 Whisper Speech-to-Text Service",
                        version="3.0.0",
                        models=[
                            AsrModel(
                                name="whisper-large-v3-turbo",
                                attribution=Attribution(name="Batistell", url="https://github.com/batistell/home-assistant"),
                                installed=True,
                                description="Whisper Large-v3-Turbo CUDA",
                                version="3.0.0",
                                languages=["pt", "en"],
                            )
                        ],
                    )
                ]
            )
            await self.write_event(info.event())
            return True

        if Transcribe.is_type(event.type):
            self.audio_data.clear()
            return True

        if AudioChunk.is_type(event.type):
            chunk = AudioChunk.from_event(event)
            self.audio_data.extend(chunk.audio)
            return True

        if AudioStop.is_type(event.type):
            LOGGER.info("🎙️ [WYOMING STT] Processando %d bytes de áudio...", len(self.audio_data))
            if self.audio_data:
                res = await stt_service.transcribe_pcm_with_info_async(bytes(self.audio_data))
                text = res.get("text", "").strip()
                LOGGER.info("✨ [WYOMING STT RESULTADO]: '%s'", text)
                await self.write_event(Transcript(text=text).event())
            else:
                await self.write_event(Transcript(text="").event())
            return False

        return True


class WyomingTTSHandler(AsyncEventHandler):
    """Handler para requisições de Text-to-Speech (TTS) do Home Assistant."""

    async def handle_event(self, event: Event) -> bool:
        if Describe.is_type(event.type):
            info = Info(
                tts=[
                    TtsProgram(
                        name="Jarvis 3.0 Edge TTS",
                        attribution=Attribution(name="Batistell", url="https://github.com/batistell/home-assistant"),
                        installed=True,
                        description="Jarvis 3.0 Edge Text-to-Speech Service",
                        version="3.0.0",
                        voices=[
                            TtsVoice(
                                name="fr-FR-RemyMultilingualNeural",
                                attribution=Attribution(name="Microsoft", url="https://github.com/rany2/edge-tts"),
                                installed=True,
                                description="Remy Multilingual Neural",
                                version="3.0.0",
                                languages=["pt", "en", "fr"],
                            )
                        ],
                    )
                ]
            )
            await self.write_event(info.event())
            return True

        if Synthesize.is_type(event.type):
            synth = Synthesize.from_event(event)
            text = synth.text.strip()
            LOGGER.info("🔊 [WYOMING TTS] Sintetizando: '%s'", text)

            if text:
                try:
                    mp3_bytes = await tts_service.synthesize_async(text)
                    if mp3_bytes:
                        await self.write_event(AudioStart(rate=24000, width=2, channels=1).event())
                        await self.write_event(AudioChunk(audio=mp3_bytes, rate=24000, width=2, channels=1).event())
                        await self.write_event(AudioStop().event())
                except Exception as err:
                    LOGGER.error("❌ [WYOMING TTS ERRO]: %s", err)
                    await self.write_event(AudioStop().event())
            return False

        return True


class WyomingService:
    """Gerenciador dos servidores TCP do Wyoming Protocol."""

    def __init__(self):
        self.stt_server = None
        self.tts_server = None

    async def start(self, stt_port: int = 10300, tts_port: int = 10200):
        """Inicia os servidores TCP Wyoming no evento de inicialização do FastAPI."""
        try:
            LOGGER.info("🚀 Iniciando Servidor Wyoming STT na porta TCP %d...", stt_port)
            self.stt_server = AsyncServer.from_uri(f"tcp://0.0.0.0:{stt_port}")
            asyncio.create_task(self.stt_server.run(WyomingSTTHandler))

            LOGGER.info("🚀 Iniciando Servidor Wyoming TTS na porta TCP %d...", tts_port)
            self.tts_server = AsyncServer.from_uri(f"tcp://0.0.0.0:{tts_port}")
            asyncio.create_task(self.tts_server.run(WyomingTTSHandler))
            LOGGER.info("✅ Servidores Wyoming STT (10300) e TTS (10200) ativos!")
        except Exception as e:
            LOGGER.error("⚠️ Erro ao iniciar servidores Wyoming: %s", e)


wyoming_service = WyomingService()
