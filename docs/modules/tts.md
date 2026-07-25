# Jarvis 3.0 — Módulo TTS (Text-to-Speech)

## Motor Padrão: Microsoft Edge TTS — Remy Multilingual

### Arquivo
`backend/tts/engines/edge_tts_engine.py`

### Voz Configurada
`fr-FR-RemyMultilingualNeural` — voz masculina francesa da Microsoft, capaz de sintetizar idiomas múltiplos com entonação natural:
- 🇧🇷 **Português Brasileiro** (pt-BR)
- 🇺🇸 **Inglês Americano** (en-US)
- 🇫🇷 **Francês** (fr-FR)
- 🇪🇸 **Espanhol** (es)
- E outros idiomas do catálogo Microsoft Neural

### Como Funciona

```python
communicate = edge_tts.Communicate(text.strip(), "fr-FR-RemyMultilingualNeural")
buffer = io.BytesIO()

async for chunk in communicate.stream():
    if chunk["type"] == "audio":
        buffer.write(chunk["data"])

mp3_bytes = buffer.getvalue()  # Áudio MP3 completo em memória
```

O áudio é sintetizado **em memória** sem salvar arquivo em disco, e enviado como **Base64** via WebSocket:

```python
await websocket.send_json({
    "type": "tts_audio",
    "audio": base64.b64encode(mp3_bytes).decode()
})
```

### Reprodução no Cliente

O **frontend** decodifica o Base64 e usa a Web Audio API para reproduzir:

```typescript
const arrayBuffer = Uint8Array.from(atob(base64), c => c.charCodeAt(0)).buffer;
const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
const source = audioContext.createBufferSource();
source.buffer = audioBuffer;
source.connect(audioContext.destination);
source.start();
```

> **Importante**: O áudio **não toca na máquina host** (servidor). Ele toca exclusivamente no browser do dispositivo que acessa a interface web.

### Por que a Voz Remy?

- A voz Remy é **multilíngue** — sintetiza o texto no idioma que o Jarvis responder automaticamente, sem precisar trocar de voz para PT ou EN
- A qualidade neural é superior às vozes TTS locais (Piper, Coqui) para este caso de uso
- Latência típica: **150–400ms** (dependência de conexão à internet)

### Configuração via `.env`

```env
TTS_VOICE=fr-FR-RemyMultilingualNeural
```

Outras vozes multilíngues compatíveis:
- `en-US-AndrewMultilingualNeural`
- `en-US-AvaMultilingualNeural`
- `pt-BR-AntonioNeural` (apenas PT)

---

## Interface Abstrata

```python
class BaseTTSEngine(ABC):
    async def synthesize(self, text: str) -> bytes: ...
        # Retorna bytes de áudio (MP3 ou WAV) em memória
```
