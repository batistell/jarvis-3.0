# Jarvis 3.0 - Arquitetura Backend

O backend do Jarvis 3.0 é construído em **Python 3.11+** utilizando o framework **FastAPI**, aproveitando a concorrência assíncrona do `asyncio` e bibliotecas nativas de inteligência artificial para interação com o **Ollama**, **faster-whisper** e **Piper TTS**.

---

## 1. Tecnologias & Bibliotecas

*   **Python 3.11+ / 3.12**: Runtime principal aproveitando tipagem moderna (`pydantic` v2, type hints) e melhorias de performance do `asyncio`.
*   **FastAPI**: Framework web moderno, assíncrono e de alto desempenho para construção de APIs REST, SSE e WebSockets.
*   **Uvicorn**: Servidor ASGI de alta velocidade alimentado por `uvloop` e `httptools`.
*   **Ollama Python SDK (`ollama`)**: Cliente assíncrono oficial (`ollama.AsyncClient`) para integração com o modelo Llama 3.
*   **faster-whisper**: Biblioteca em Python baseada no CTranslate2 e PyTorch para transcrição acelerada de áudio em memória (STT).
*   **piper-tts**: Motor em Python para síntese de texto em fala de baixíssima latência (TTS).
*   **SQLAlchemy 2.0 (Async)**: ORM com suporte completo a `asyncio` para persistência de dados.
*   **httpx**: Cliente HTTP assíncrono para integração com a REST API do Home Assistant.
*   **PyJWT & cryptography**: Validação criptográfica de tokens JWT do Firebase Auth via chaves públicas JWKS do Google.

---

## 2. Integração com Ollama (Llama 3)

A integração com o Ollama é configurada através de variáveis de ambiente (`.env`) e instanciada assincronamente:

```python
import os
from ollama import AsyncClient

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

ollama_client = AsyncClient(host=OLLAMA_BASE_URL)
```

O `AsyncClient` permite streaming de respostas de forma totalmente não-bloqueante dentro das rotas do FastAPI ou handlers de WebSockets.

---

## 3. Fluxo Reativo & Endpoint de Stream (Modo Texto / Fallback)

Para interações puramente baseadas em texto ou fallback, o backend disponibiliza um endpoint utilizando **Server-Sent Events (SSE)** através do `EventSourceResponse` (ou `StreamingResponse` nativo do FastAPI).

### Exemplo de Controller / Rota em FastAPI:

```python
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from ollama import AsyncClient
import json

app = FastAPI()
ollama_client = AsyncClient(host="http://localhost:11434")

class ChatRequest(BaseModel):
    message: str

async def generate_chat_stream(prompt_text: str):
    response_stream = await ollama_client.chat(
        model="llama3",
        messages=[{"role": "user", "content": prompt_text}],
        stream=True
    )
    
    async for chunk in response_stream:
        content = chunk.get("message", {}).get("content", "")
        if content:
            yield f"data: {json.dumps({'content': content})}\n\n"

@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    return StreamingResponse(
        generate_chat_stream(request.message),
        media_type="text/event-stream"
    )
```

---

## 4. Gestão de Memória da Conversa (Contexto)

Para reter o histórico e contexto das mensagens:

*   **Sessão de Conversa**: Armazenada no banco de dados através das tabelas `Conversation` e `Message`.
*   **Janela de Contexto Ativo**: O backend recupera apenas as últimas N mensagens ativas (ex: últimas 10 mensagens) do banco de dados e as formata na lista de `messages` enviada ao Ollama.
*   **Limitação de Tokens**: Evita exceder o limite de tokens do Llama 3 mantendo o histórico enxuto e serializável diretamente em objetos JSON do Python.

---

## 5. Integração com Home Assistant (Function Calling / Tool Use)

Para permitir que o Jarvis 3.0 controle dispositivos físicos na casa (luzes, interruptores, sensores), utilizaremos o recurso de **Tools / Function Calling** suportado nativamente pelo Ollama em Python e pela API REST do Home Assistant via `httpx`.

### Como funciona o Function Calling em Python:
1. Definimos o esquema JSON da função aceita pelo Ollama (ferramenta de controle residencial).
2. O modelo analisa a mensagem do usuário (ex: *"Ligue a luz do quarto"*).
3. Se identificar a intenção, a resposta do Ollama retorna uma solicitação de chamada de ferramenta (`tool_calls`).
4. O FastAPI executa a função Python correspondente, enviando um `POST` assíncrono via `httpx` para a API do Home Assistant no Raspberry Pi (`http://<raspberry-pi-ip>:8123/api/services/light/turn_on`).
5. O resultado da execução é devolvido ao Ollama, que gera a resposta final ao usuário.

### Exemplo de Código em Python:

```python
import httpx
import os

HA_URL = os.getenv("HOME_ASSISTANT_URL", "http://192.168.1.100:8123")
HA_TOKEN = os.getenv("HOME_ASSISTANT_TOKEN", "token_aqui")

tools_schema = [{
    "type": "function",
    "function": {
        "name": "control_home_device",
        "description": "Controla dispositivos de automação doméstica no Home Assistant",
        "parameters": {
            "type": "object",
            "properties": {
                "entity_id": {"type": "string", "description": "ID da entidade (ex: light.bedroom)"},
                "action": {"type": "string", "description": "Ação (turn_on ou turn_off)"}
            },
            "required": ["entity_id", "action"]
        }
    }
}]

async def execute_home_assistant_tool(entity_id: str, action: str) -> str:
    domain = entity_id.split(".")[0]
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json"
    }
    url = f"{HA_URL}/api/services/{domain}/{action}"
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json={"entity_id": entity_id})
        if response.status_code == 200:
            return "Comando executado com sucesso."
        return f"Erro ao executar comando: {response.text}"
```

---

## 6. Processamento de Voz (WebSockets, STT e TTS Nativos)

No Jarvis 3.0, a transmissão de voz é realizada via **WebSocket** em `/ws/voice`. A transcrição (STT) e a síntese (TTS) rodam **diretamente dentro do ecossistema Python**, eliminando chamadas HTTP para serviços externos de áudio.

### Fluxo no WebSocket Handler:
1. **Conexão Estabelecida**: O cliente abre a conexão WebSocket em `/ws/voice?token=JWT`.
2. **Recebimento de Áudio (STT em Memória com faster-whisper)**:
   - O cliente envia amostras de **áudio PCM linear bruto** (16000 Hz, 16-bit, Mono) como dados binários (`bytes`).
   - O backend acumula os `bytes` em um buffer de memória (`io.BytesIO`).
   - Quando o sinalizador `"SPEECH_END"` é recebido, os bytes PCM acumulados são convertidos para um array NumPy e passados diretamente para o modelo `faster_whisper.WhisperModel.transcribe()` em memória.
3. **Geração e Síntese (LLM + Piper TTS)**:
   - O texto transcrito é enviado ao Ollama.
   - Conforme cada trecho/frase de texto é recebido do Ollama em streaming, a frase é sintetizada pelo **Piper TTS** em memória.
   - Os `bytes` do áudio sintetizado (WAV/PCM) são transmitidos via WebSocket como dados binários (`bytes`), juntamente com os tokens de texto JSON.

### Exemplo do Handler de WebSocket em FastAPI:

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, status
import io
import numpy as np
from faster_whisper import WhisperModel
from ollama import AsyncClient

app = FastAPI()

# Inicializa modelos em memória
whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
ollama_client = AsyncClient(host="http://localhost:11434")

@app.websocket("/ws/voice")
async def voice_websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    # 1. Valida token JWT do Firebase (ver Seção 7)
    user_email = await validate_firebase_jwt(token)
    if not user_email:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    audio_buffer = bytearray()

    try:
        while True:
            message = await websocket.receive()
            
            if "bytes" in message and message["bytes"]:
                # Dados binários PCM recebidos
                audio_buffer.extend(message["bytes"])
                
            elif "text" in message and message["text"] == "SPEECH_END":
                # Converte buffer PCM de 16-bit para float32 numpy array
                raw_pcm = bytes(audio_buffer)
                audio_buffer.clear()
                
                audio_np = np.frombuffer(raw_pcm, dtype=np.int16).astype(np.float32) / 32768.0
                
                # Transcreve via faster-whisper nativo
                segments, _ = whisper_model.transcribe(audio_np, beam_size=5)
                transcribed_text = " ".join([segment.text for segment in segments]).strip()
                
                if not transcribed_text:
                    continue
                
                # Transmite o texto transcrito ao cliente
                await websocket.send_json({"type": "stt_result", "text": transcribed_text})
                
                # Streaming da LLM
                response_stream = await ollama_client.chat(
                    model="llama3",
                    messages=[{"role": "user", "content": transcribed_text}],
                    stream=True
                )
                
                async for chunk in response_stream:
                    token_content = chunk.get("message", {}).get("content", "")
                    if token_content:
                        # Envia o token de texto
                        await websocket.send_json({"type": "text_token", "content": token_content})
                        
                        # Sintetiza com Piper TTS e envia os bytes do áudio sintetizado
                        # audio_bytes = tts_engine.synthesize(token_content)
                        # await websocket.send_bytes(audio_bytes)

    except WebSocketDisconnect:
        print("Cliente desconectado do canal de voz.")
```

---

## 7. Segurança e Autenticação (Firebase JWT & Allowed Emails)

O backend FastAPI implementa a verificação criptográfica de tokens JWT emitidos pelo Firebase Authentication (Google Provider) usando as chaves públicas vigentes publicadas no JWKS da Google.

### Parâmetros de Segurança (`.env`):
```env
FIREBASE_PROJECT_ID=jarvis-1006b
ALLOWED_EMAILS=batistell.labs@gmail.com,gbbts@gmail.com,gbbtstll@gmail.com
```

### Validador de Token JWT em Python:

```python
import jwt
from jwt import PyJWKClient
import os

FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "jarvis-1006b")
ALLOWED_EMAILS = [e.strip() for e in os.getenv("ALLOWED_EMAILS", "").split(",") if e.strip()]
JWKS_URL = "https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com"

jwk_client = PyJWKClient(JWKS_URL)

async def validate_firebase_jwt(token_string: str) -> str:
    try:
        signing_key = jwk_client.get_signing_key_from_jwt(token_string)
        payload = jwt.decode(
            token_string,
            signing_key.key,
            algorithms=["RS256"],
            audience=FIREBASE_PROJECT_ID,
            issuer=f"https://securetoken.google.com/{FIREBASE_PROJECT_ID}"
        )
        
        email = payload.get("email")
        email_verified = payload.get("email_verified", False)
        
        if not email or not email_verified:
            raise ValueError("E-mail ausente ou não verificado.")
            
        if email not in ALLOWED_EMAILS:
            raise ValueError(f"E-mail {email} não está na whitelist autorizada.")
            
        return email
    except Exception as e:
        print(f"Erro na validação do token JWT: {e}")
        return None
```
