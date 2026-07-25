import sys
import io
import re
import time
import wave
import base64
import numpy as np
from contextlib import asynccontextmanager
from pydantic import BaseModel
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, status, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.services.auth_service import validate_firebase_token
from backend.services.vad_service import BackendVADDetector
from backend.services.stt_service import stt_service
from backend.services.llm_service import llm_service
from backend.services.tts_service import tts_service
from backend.services.health_service import health_service
from backend.services.ha_service import ha_service
from backend.services.conversation_service import conversation_service

# Regex para extrair sentenças completas do stream de tokens do LLM


_SENTENCE_SPLIT_RE = re.compile(r'(?<=[.!?;:\n])\s+')

# Garantir codificação UTF-8 no stdout/stderr no Windows
if hasattr(sys.stdout, 'buffer') and getattr(sys.stdout, 'encoding', '').lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'buffer') and getattr(sys.stderr, 'encoding', '').lower() != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from backend.services.wyoming_service import wyoming_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Pré-carrega o modelo Whisper Large e verifica a disponibilidade do modelo LLM.
    """
    print("\n" + "=" * 65)
    print("🚀 INICIALIZANDO BACKEND DO JARVIS 3.0 (SERVIDORES STT, LLM, VAD & WYOMING)")
    print("=" * 65, flush=True)
    
    # Executa pré-carregamento do modelo Whisper STT
    stt_service.load_model()
    
    # Verifica/baixa modelo LLM no Ollama
    await llm_service.ensure_model_loaded()
    
    # Inicia servidores TCP do Wyoming Protocol (STT 10300, TTS 10200)
    await wyoming_service.start(stt_port=10300, tts_port=10200)

    # Pré-carrega entidades e dispositivos do Home Assistant em memória
    await ha_service.load_entities_cache(force=True)

    print("\n🎧 [SERVER READY] Backend e Servidores Wyoming (10300/10200) Prontos!\n", flush=True)

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
        "engine": "Python FastAPI + faster-whisper + Qwen 2.5 Native"
    }

@app.get("/api/health")
async def get_health_check():
    """
    Endpoint de Health Check para monitoramento de saúde da GPU (VRAM, Utilização, Temperatura)
    e status dos modelos de IA (STT, LLM, TTS).
    """
    return await health_service.get_full_health()

@app.post("/api/health/gc")
async def trigger_garbage_collection():
    """
    Força coleta de lixo e limpeza de memória.
    """
    return health_service.release_memory()


class HAChatRequest(BaseModel):
    message: str | None = None
    text: str | None = None
    conversation_id: str | None = None


class HATTSRequest(BaseModel):
    text: str | None = None
    message: str | None = None
    language: str | None = None


def _convert_audio_to_pcm16_16khz(raw_bytes: bytes) -> bytes:
    """
    Converte bytes de áudio (WAV RIFF ou PCM) recebidos do Home Assistant STT
    em PCM 16-bit 16kHz mono esperado pelo FasterWhisperEngine.
    """
    if not raw_bytes:
        return b""

    if raw_bytes.startswith(b"RIFF") and len(raw_bytes) > 44:
        try:
            with wave.open(io.BytesIO(raw_bytes), "rb") as wf:
                nchannels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                framerate = wf.getframerate()
                frames = wf.readframes(wf.getnframes())

                if sampwidth == 2:
                    audio_data = np.frombuffer(frames, dtype=np.int16)
                elif sampwidth == 4:
                    audio_data = (np.frombuffer(frames, dtype=np.int32) >> 16).astype(np.int16)
                elif sampwidth == 1:
                    audio_data = ((np.frombuffer(frames, dtype=np.uint8).astype(np.int32) - 128) << 8).astype(np.int16)
                else:
                    audio_data = np.frombuffer(frames, dtype=np.int16)

                if nchannels > 1:
                    audio_data = audio_data[::nchannels]

                if framerate != 16000 and len(audio_data) > 0:
                    new_length = int(len(audio_data) * 16000 / framerate)
                    audio_data = np.interp(
                        np.linspace(0, len(audio_data), new_length, endpoint=False),
                        np.arange(len(audio_data)),
                        audio_data
                    ).astype(np.int16)

                return audio_data.tobytes()
        except Exception as e:
            print(f"⚠️ [STT REST] Erro ao decodificar cabeçalho WAV: {e}. Usando bytes brutos como fallback.", flush=True)

    return raw_bytes


# --- ENDPOINTS REST PARA HOME ASSISTANT ASSIST PIPELINE ---

@app.get("/api/v1/ha/test")
async def ha_test_endpoint():
    """
    Endpoint de teste e diagnóstico da conexão do Jarvis com o Home Assistant.
    """
    if not ha_service.is_configured:
        return {
            "configured": False,
            "message": "Token do Home Assistant (HA_TOKEN) não configurado no arquivo .env."
        }
    entities = await ha_service.list_entities(domain="light")
    return {
        "configured": True,
        "ha_url": settings.HA_URL,
        "light_entities_count": len(entities),
        "lights": [
            {
                "entity_id": e.get("entity_id"),
                "state": e.get("state"),
                "friendly_name": e.get("attributes", {}).get("friendly_name")
            }
            for e in entities[:10]
        ]
    }


@app.post("/api/v1/chat")
async def ha_chat_endpoint(req: HAChatRequest):
    """
    Endpoint de Conversação/LLM para o Home Assistant Conversation Agent.
    Recebe a mensagem de texto, executa a verificação de sensores se for comando de luz/dispositivo,
    e retorna a resposta verificada pelo Jarvis.
    """
    prompt = (req.message or req.text or "").strip()
    conversation_id = req.conversation_id or "default"

    if not prompt:
        return {
            "response": "Nenhuma mensagem recebida.",
            "text": "Nenhuma mensagem recebida.",
            "conversation_id": conversation_id
        }

    print(f"🤖 [HA ASSIST CHAT] Mensagem recebida: \"{prompt}\" (conversation_id: {conversation_id})", flush=True)
    try:
        conversation_service.add_user_message(conversation_id, prompt)

        # 1. Tenta interpretar como comando de automação com feedback de sensor do HA e suporte a contexto
        ha_res = await ha_service.parse_and_execute_ha_command(prompt, session_id=conversation_id)
        if ha_res:
            reply_clean = ha_res["message"]
        else:
            history = conversation_service.get_history(conversation_id)
            reply_text = await llm_service.generate(prompt, history=history)
            reply_clean = reply_text.strip()

            # Guardrail Anti-Alucinação de Hardware: impede o LLM de simular confirmações de sensor sem hardware acionado
            reply_lower = reply_clean.lower()
            if "confirmado pelo sensor" in reply_lower or ("dispositivo" in reply_lower and ("ligado" in reply_lower or "desligado" in reply_lower)):
                print(f"🛡️ [LLM HALLUCINATION BLOCKED] Bloqueada alucinação de hardware do LLM: \"{reply_clean}\"", flush=True)
                reply_clean = "Desculpe, não entendi o comando. Como posso ajudar?"

        conversation_service.add_assistant_message(conversation_id, reply_clean)

    except Exception as e:
        print(f"❌ [HA ASSIST CHAT ERROR] Erro no processamento: {e}", flush=True)
        reply_clean = "Desculpe, ocorreu um erro ao processar a resposta no Jarvis."


    print(f"💬 [HA ASSIST CHAT RESPONSE]: \"{reply_clean}\"", flush=True)
    return {
        "response": reply_clean,
        "text": reply_clean,
        "conversation_id": conversation_id
    }



@app.post("/api/v1/stt")
async def ha_stt_endpoint(request: Request):
    """
    Endpoint de Speech-to-Text para a plataforma 'stt: rest' do Home Assistant.
    Recebe o áudio enviado pelo aplicativo do celular / HA e retorna a transcrição.
    """
    audio_bytes = await request.body()
    if not audio_bytes:
        return {"text": ""}

    print(f"🎙️  [HA ASSIST STT] Áudio recebido: {len(audio_bytes)} bytes", flush=True)
    pcm_bytes = _convert_audio_to_pcm16_16khz(audio_bytes)
    
    stt_res = await stt_service.transcribe_pcm_with_info_async(pcm_bytes)
    transcribed_text = stt_res.get("text", "").strip()

    print(f"✨ [HA ASSIST STT RESULT]: \"{transcribed_text}\"", flush=True)
    return {"text": transcribed_text}


@app.post("/api/v1/tts")
async def ha_tts_endpoint(request: Request, req: HATTSRequest | None = None):
    """
    Endpoint de Text-to-Speech para a plataforma 'tts: rest' do Home Assistant.
    Recebe a frase em texto e retorna o arquivo de áudio MP3 binário para o celular reproduzir.
    """
    text = ""
    if req and (req.text or req.message):
        text = req.text or req.message or ""
    else:
        try:
            body_json = await request.json()
            text = body_json.get("text") or body_json.get("message") or ""
        except Exception:
            body_bytes = await request.body()
            text = body_bytes.decode("utf-8", errors="ignore").strip()

    text = text.strip()
    if not text:
        return Response(content=b"", media_type="audio/mpeg")

    print(f"🔊 [HA ASSIST TTS] Sintetizando voz para: \"{text}\"", flush=True)
    try:
        audio_bytes = await tts_service.synthesize_async(text)
        return Response(content=audio_bytes, media_type="audio/mpeg")
    except Exception as e:
        print(f"❌ [HA ASSIST TTS ERROR] Falha ao sintetizar voz: {e}", flush=True)
        return Response(content=b"", media_type="audio/mpeg", status_code=500)


active_voice_socket: WebSocket | None = None

@app.websocket("/ws/voice")
async def voice_websocket_endpoint(websocket: WebSocket, token: str = Query(default="dev-token")):
    """
    Endpoint WebSocket de voz bidirecional.
    Rejeita conexões duplicadas para garantir exatamente 1 sessão de voz ativa.
    """
    global active_voice_socket

    user_email = await validate_firebase_token(token)
    if not user_email:
        print("\n❌ [AUTH ERROR] Conexão rejeitada: token de autenticação inválido.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Se já houver uma conexão ativa aberta, rejeita a tentativa duplicada imediatamente
    if active_voice_socket is not None:
        try:
            if active_voice_socket.client_state.name == "CONNECTED":
                await websocket.close(code=1000, reason="Sessão de voz já ativa")
                return
        except Exception:
            active_voice_socket = None

    await websocket.accept()
    active_voice_socket = websocket
    print(f"\n⚡ [WEBSOCKET CONNECTED] Conexão de voz única ativa para: {user_email}\n")

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
                        print(f"🎙️  [LIVE STT]: \"{partial_text}\"", flush=True)
                        await websocket.send_json({
                            "type": "stt_partial",
                            "text": partial_text
                        })

                if is_pause and completed_audio:
                    last_partial_text = ""
                    await websocket.send_json({"type": "stt_status", "status": "transcribing"})
                    
                    stt_res = await stt_service.transcribe_pcm_with_info_async(completed_audio)
                    transcribed_text = stt_res.get("text", "")
                    detected_lang = stt_res.get("language", "pt")
                    
                    if transcribed_text:
                        await websocket.send_json({
                            "type": "stt_result",
                            "text": transcribed_text,
                            "user": user_email,
                            "language": detected_lang
                        })

                        # Geração de resposta LLM no mesmo idioma que o usuário falou
                        lang_prompt = (
                            f"{settings.JARVIS_SYSTEM_PROMPT}\n"
                            f"Instrução Estrita de Idioma: O usuário falou no idioma '{detected_lang.upper()}'. "
                            f"Você DEVE responder obrigatoriamente no idioma '{detected_lang.upper()}'."
                        )

                        session_id = user_email or "default"
                        conversation_service.add_user_message(session_id, transcribed_text)

                        print(f"🧠 [PROCESSING RESPONSE] Analisando comando e gerando resposta (Idioma: {detected_lang.upper()})...", flush=True)
                        await websocket.send_json({"type": "llm_status", "status": "generating"})

                        # Verifica se é um comando de automação residencial com validação de sensor do HA e suporte a contexto
                        ha_res = await ha_service.parse_and_execute_ha_command(transcribed_text, session_id=session_id)
                        
                        if ha_res:
                            full_llm_response = ha_res["message"]
                            await websocket.send_json({"type": "llm_chunk", "text": full_llm_response})
                            try:
                                audio_bytes = await tts_service.synthesize_async(full_llm_response)
                                if audio_bytes:
                                    audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
                                    await websocket.send_json({"type": "tts_audio", "audio": audio_b64})
                            except Exception as tts_err:
                                print(f"⚠️ [TTS ERROR] {tts_err}", flush=True)
                        else:
                            # --- Sentence-Streaming TTS para respostas convencionais do LLM ---
                            llm_start_t = time.time()
                            full_llm_response = ""
                            tts_buffer = ""        # Acumula tokens até ter uma frase completa
                            first_audio_sent = False

                            async def _flush_tts(sentence: str) -> None:
                                """Sintetiza uma frase e envia o áudio pelo WebSocket imediatamente."""
                                nonlocal first_audio_sent
                                sentence = sentence.strip()
                                if not sentence:
                                    return
                                tts_t = time.time()
                                try:
                                    audio_bytes = await tts_service.synthesize_async(sentence)
                                    if audio_bytes:
                                        audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
                                        await websocket.send_json({"type": "tts_audio", "audio": audio_b64})
                                        elapsed_tts = (time.time() - tts_t) * 1000.0
                                        health_service.record_tts_latency(elapsed_tts)
                                        if not first_audio_sent:
                                            first_audio_sent = True
                                            print(f"🔊 [TTS FIRST CHUNK] {elapsed_tts:.0f}ms → \"{sentence[:40]}...\"", flush=True)
                                except Exception as tts_err:
                                    print(f"⚠️ [TTS ERROR] {tts_err}", flush=True)

                            history = conversation_service.get_history(session_id)
                            async for chunk in llm_service.generate_stream(transcribed_text, system_prompt=lang_prompt, history=history):
                                full_llm_response += chunk
                                tts_buffer += chunk
                                await websocket.send_json({"type": "llm_chunk", "text": chunk})

                                # Verifica se o buffer já contém ao menos uma frase terminada
                                parts = _SENTENCE_SPLIT_RE.split(tts_buffer)
                                if len(parts) > 1:
                                    # As partes exceto a última estão completas → sintetiza cada uma
                                    for sentence in parts[:-1]:
                                        await _flush_tts(sentence)
                                    tts_buffer = parts[-1]  # Guarda o fragmento incompleto

                            # Sintetiza o fragmento final (última frase sem pontuação de fim)
                            if tts_buffer.strip():
                                await _flush_tts(tts_buffer)

                            llm_elapsed = (time.time() - llm_start_t) * 1000.0
                            health_service.record_llm_latency(llm_elapsed)


                            # Guardrail Anti-Alucinação: se o LLM tentar imitar confirmação de hardware no stream de voz
                            reply_lower = full_llm_response.lower()
                            if "confirmado pelo sensor" in reply_lower or ("dispositivo" in reply_lower and ("ligado" in reply_lower or "desligado" in reply_lower)):
                                print(f"🛡️ [LLM HALLUCINATION BLOCKED] Bloqueada alucinação de hardware do LLM no WebSocket: \"{full_llm_response}\"", flush=True)
                                full_llm_response = "Desculpe, não entendi o comando. Como posso ajudar?"

                        conversation_service.add_assistant_message(session_id, full_llm_response.strip())
                        print(f"🤖 [JARVIS RESPONSE]: \"{full_llm_response.strip()}\"\n", flush=True)

                        await websocket.send_json({
                            "type": "llm_result",
                            "text": full_llm_response.strip()
                        })
                        await websocket.send_json({"type": "stt_status", "status": "idle"})
                    else:
                        await websocket.send_json({"type": "stt_status", "status": "idle"})
                        
            # 2. Comandos de texto manuais do chat
            elif "text" in message and message["text"]:
                text_cmd = message["text"]
                session_id = user_email or "default"
                conversation_service.add_user_message(session_id, text_cmd)

                print(f"\n💬 [TEXT COMMAND] Mensagem de texto recebida: \"{text_cmd}\"")
                print(f"🧠 [PROCESSING RESPONSE] Processando mensagem...", flush=True)
                await websocket.send_json({"type": "llm_status", "status": "generating"})
                
                ha_res = await ha_service.parse_and_execute_ha_command(text_cmd, session_id=session_id)
                if ha_res:
                    full_llm_response = ha_res["message"]
                    await websocket.send_json({"type": "llm_chunk", "text": full_llm_response})
                else:
                    history = conversation_service.get_history(session_id)
                    full_llm_response = ""
                    async for chunk in llm_service.generate_stream(text_cmd, history=history):
                        full_llm_response += chunk
                        await websocket.send_json({
                            "type": "llm_chunk",
                            "text": chunk
                        })
                    
                    # Guardrail Anti-Alucinação
                    reply_lower = full_llm_response.lower()
                    if "confirmado pelo sensor" in reply_lower or ("dispositivo" in reply_lower and ("ligado" in reply_lower or "desligado" in reply_lower)):
                        print(f"🛡️ [LLM HALLUCINATION BLOCKED] Bloqueada alucinação de hardware do LLM no chat texto: \"{full_llm_response}\"", flush=True)
                        full_llm_response = "Desculpe, não entendi o comando. Como posso ajudar?"

                conversation_service.add_assistant_message(session_id, full_llm_response.strip())
                print(f"🤖 [JARVIS RESPONSE]: \"{full_llm_response.strip()}\"\n", flush=True)


                
                # Sintetiza áudio TTS para ser reproduzido via Web Audio API no navegador cliente
                if full_llm_response.strip():
                    try:
                        audio_bytes = await tts_service.synthesize_async(full_llm_response.strip())
                        if audio_bytes:
                            audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
                            await websocket.send_json({
                                "type": "tts_audio",
                                "audio": audio_b64
                            })
                    except Exception as tts_err:
                        print(f"⚠️ [TTS ERROR] Falha ao sintetizar áudio TTS: {tts_err}", flush=True)

                await websocket.send_json({
                    "type": "llm_result",
                    "text": full_llm_response.strip()
                })


    except WebSocketDisconnect:
        print(f"\n🔌 [WEBSOCKET DISCONNECTED] Cliente {user_email} desconectou do canal de voz.\n")
    except Exception as e:
        print(f"\n⚠️ [WEBSOCKET ERROR] Exceção na sessão de voz: {e}\n")
        try:
            await websocket.close()
        except:
            pass
    finally:
        if active_voice_socket == websocket:
            active_voice_socket = None

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.HOST, port=settings.PORT, reload=True)
