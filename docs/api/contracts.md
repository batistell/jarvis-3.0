# Contratos de APIs e WebSockets

Este documento define os contratos de comunicação e formatos de mensagens trocados entre o React Frontend e o FastAPI Backend no Jarvis 3.0.

---

## 1. Conexão WebSocket Principal (`/ws/voice`)

O canal WebSocket em `/ws/voice` é a via de comunicação em tempo real de baixa latência utilizada para o fluxo contínuo de voz e texto (always-listening).

*   **URL de Conexão**: `ws://localhost:8000/ws/voice?token=<FIREBASE_ID_TOKEN>` (ou `wss://` caso o frontend esteja sob HTTPS)
*   **Protocolo**: WS/WSS (WebSocket assíncrono do FastAPI/Starlette)
*   **Autenticação**: O parâmetro query `token` é obrigatório e deve conter um ID Token JWT válido do Firebase Auth.

---

## 2. Mensagens do Cliente para o Servidor (Upload)

O cliente React envia dois tipos de dados pelo canal WebSocket:

### A. Frames de Áudio (Dados Binários)
*   **Tipo**: Mensagem Binária (`bytes` / `ArrayBuffer`)
*   **Frequência**: Transmitido continuamente conforme novos buffers do microfone são capturados.
*   **Formato de Áudio**: PCM linear bruto (16-bit, 16000 Hz, Canal Único Mono, Little-Endian).
*   **Propósito**: Alimenta o buffer de gravação na memória do Python para transcrição direta com `faster-whisper`.

### B. Comandos de Controle (Dados Textuais)
*   `"SPEECH_END"`: Sinaliza que o silêncio local foi detectado no microfone do usuário (VAD no cliente), disparando o processo de transcrição (STT) e envio do prompt para o Ollama.
*   `"INTERRUPT"`: Enviado se o usuário começar a falar enquanto o Jarvis está reproduzindo som. O backend FastAPI intercepta o sinal e cancela o gerador da LLM.

---

## 3. Mensagens do Servidor para o Cliente (Download)

O backend FastAPI envia informações reativas de volta para a interface:

### A. Resultados da Transcrição & Tokens de Texto (JSON)
*   **Tipo**: Mensagem de Texto (JSON)
*   **Estrutura da Mensagem de Transcrição (STT)**:
    ```json
    {
      "type": "stt_result",
      "text": "Ligue a luz da sala"
    }
    ```
*   **Estrutura da Mensagem de Token de Texto da LLM**:
    ```json
    {
      "type": "text_token",
      "content": "Com "
    }
    ```

### B. Chunks de Áudio Sintetizado (Dados Binários)
*   **Tipo**: Mensagem Binária (`bytes` / `ArrayBuffer`)
*   **Frequência**: Transmitido à medida que trechos de texto são sintetizados pelo `piper-tts` no backend Python.
*   **Formato de Áudio**: WAV/PCM linear, 16000 Hz ou 22050 Hz, Mono.
*   **Propósito**: Alimentar a fila de reprodução invisível (Web Audio API) no navegador.

---

## 4. Endpoints REST (Modo Texto / Fallback)

### Enviar Mensagem de Texto (Streaming SSE)
Utilizado para interação via digitação clássica ou fallbacks do sistema.

*   **Endpoint**: `POST /api/chat/stream`
*   **Headers**: 
    *   `Content-Type: application/json`
    *   `Authorization: Bearer <FIREBASE_ID_TOKEN>`
*   **Request Body**:
    ```json
    {
      "message": "Ligue a luz do quarto"
    }
    ```
*   **Response Headers**:
    *   `Content-Type: text/event-stream`
*   **Response Body (Stream de Eventos SSE)**:
    ```text
    data: {"content": "Com"}
    data: {"content": " certeza,"}
    data: {"content": " estou"}
    data: {"content": " ligando"}
    data: {"content": " a"}
    data: {"content": " luz."}
    ```
