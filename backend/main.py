import sys
import io
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, status
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.services.auth_service import validate_firebase_token
from backend.services.vad_service import BackendVADDetector
from backend.services.stt_service import stt_service

# Garantir codificação UTF-8 no stdout/stderr no Windows
if hasattr(sys.stdout, 'buffer') and getattr(sys.stdout, 'encoding', '').lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'buffer') and getattr(sys.stderr, 'encoding', '').lower() != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Pré-carrega o modelo Whisper Large no início da execução da aplicação.
    """
    print("\n" + "=" * 65)
    print("🚀 INICIALIZANDO BACKEND DO JARVIS 3.0 (SERVIDORE STT & VAD)")
    print("=" * 65, flush=True)
    
    # Executa pré-carregamento do modelo Whisper Large
    stt_service.load_model()
    
    print("\n🎧 [SERVER READY] Backend aguardando conexões WebSocket e áudio em tempo real...\n", flush=True)
    yield
    print("🛑 Encerrando backend Jarvis 3.0.", flush=True)

app = FastAPI(
    title="JARVIS 3.0 API Engine",
    version="3.0.0",
    description="Backend Python assíncrono para o assistente Jarvis 3.0",
    lifespan=lifespan
)

# Configuração de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "app": "JARVIS 3.0",
        "status": "online",
        "model": settings.WHISPER_MODEL,
        "engine": "Python FastAPI + faster-whisper + Ollama"
    }

@app.websocket("/ws/voice")
async def voice_websocket_endpoint(websocket: WebSocket, token: str = Query(default="dev-token")):
    """
    Endpoint WebSocket de voz bidirecional.
    Loga tudo o que receber de áudio do frontend em tempo real no console do terminal.
    """
    user_email = await validate_firebase_token(token)
    if not user_email:
        print("\n❌ [AUTH ERROR] Conexão rejeitada: token de autenticação inválido.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    print(f"\n⚡ [WEBSOCKET CONNECTED] Cliente conectado ao canal de voz: {user_email}")
    print("   Aguardando streaming de áudio do microfone...\n")

    vad_detector = BackendVADDetector()
    last_partial_text = ""

    try:
        while True:
            message = await websocket.receive()

            if message.get("type") == "websocket.disconnect":
                print(f"\n🔌 [WEBSOCKET DISCONNECTED] Cliente {user_email} desconectou do canal de voz.\n")
                break
            
            # 1. Chunks binários de áudio PCM recebidos do microfone do frontend
            if "bytes" in message and message["bytes"]:
                pcm_chunk = message["bytes"]
                
                is_pause, completed_audio, partial_audio = vad_detector.process_pcm_chunk(pcm_chunk)
                
                # Transcrição parcial em tempo real enquanto o usuário fala
                if partial_audio and not is_pause:
                    partial_text = await stt_service.transcribe_partial_async(partial_audio)
                    if partial_text and partial_text != last_partial_text:
                        last_partial_text = partial_text
                        print(f"\r\033[K🎙️  [LIVE STT]: \"{partial_text}\"", end="", flush=True)
                        await websocket.send_json({
                            "type": "stt_partial",
                            "text": partial_text
                        })

                if is_pause and completed_audio:
                    last_partial_text = ""
                    await websocket.send_json({"type": "stt_status", "status": "transcribing"})
                    
                    transcribed_text = await stt_service.transcribe_pcm_async(completed_audio)
                    
                    if transcribed_text:
                        await websocket.send_json({
                            "type": "stt_result",
                            "text": transcribed_text,
                            "user": user_email
                        })
                    else:
                        await websocket.send_json({"type": "stt_status", "status": "idle"})
                        
            # 2. Comandos de texto manuais
            elif "text" in message and message["text"]:
                text_cmd = message["text"]
                print(f"\n💬 [TEXT COMMAND] Mensagem de texto recebida: \"{text_cmd}\"")

    except WebSocketDisconnect:
        print(f"\n🔌 [WEBSOCKET DISCONNECTED] Cliente {user_email} desconectou do canal de voz.\n")
    except Exception as e:
        print(f"\n⚠️ [WEBSOCKET ERROR] Exceção na sessão de voz: {e}\n")
        try:
            await websocket.close()
        except:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.HOST, port=settings.PORT, reload=True)
