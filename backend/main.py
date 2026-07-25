from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, status
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.services.auth_service import validate_firebase_token
from backend.services.vad_service import BackendVADDetector
from backend.services.stt_service import stt_service

app = FastAPI(
    title="JARVIS 3.0 API Engine",
    version="3.0.0",
    description="Backend Python assíncrono para o assistente Jarvis 3.0"
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
        "engine": "Python FastAPI + faster-whisper + Ollama"
    }

@app.websocket("/ws/voice")
async def voice_websocket_endpoint(websocket: WebSocket, token: str = Query(default="dev-token")):
    """
    Endpoint WebSocket de voz bidirecional.
    Recebe chunks binários PCM (16kHz Mono) em tempo real, executa o VAD no backend para identificar
    pausas de fala e retorna o texto transcrito pelo faster-whisper instantaneamente.
    """
    user_email = await validate_firebase_token(token)
    if not user_email:
        print("❌ Conexão rejeitada: token de autenticação inválido.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    print(f"⚡ Cliente conectado ao canal de voz: {user_email}")

    vad_detector = BackendVADDetector()

    try:
        while True:
            message = await websocket.receive()
            
            # 1. Chunks binários de áudio PCM
            if "bytes" in message and message["bytes"]:
                pcm_chunk = message["bytes"]
                
                # VAD no backend detecta se o usuário pausou de falar
                is_pause, completed_audio = vad_detector.process_pcm_chunk(pcm_chunk)
                
                if is_pause and completed_audio:
                    # Notifica início da transcrição
                    await websocket.send_json({"type": "stt_status", "status": "transcribing"})
                    
                    # Executa transcrição em memória com faster-whisper
                    transcribed_text = await stt_service.transcribe_pcm_async(completed_audio)
                    
                    if transcribed_text:
                        print(f"✨ Transcrito [Ouvido de {user_email}]: \"{transcribed_text}\"")
                        
                        # Envia o texto transcrito em tempo real para atualização da tela no Frontend
                        await websocket.send_json({
                            "type": "stt_result",
                            "text": transcribed_text,
                            "user": user_email
                        })
                    else:
                        print("ℹ️ Nenhuma fala nítida identificada no trecho.")
                        await websocket.send_json({"type": "stt_status", "status": "idle"})
                        
            # 2. Comandos de texto manuais
            elif "text" in message and message["text"]:
                text_cmd = message["text"]
                if text_cmd == "SPEECH_END":
                    # Sinalizador manual do frontend se acionado
                    pass
                else:
                    print(f"💬 Mensagem de texto recebida: {text_cmd}")

    except WebSocketDisconnect:
        print(f"🔌 Cliente {user_email} desconectou do canal de voz.")
    except Exception as e:
        print(f"⚠️ Erro inesperado na sessão WebSocket: {e}")
        try:
            await websocket.close()
        except:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.HOST, port=settings.PORT, reload=True)
