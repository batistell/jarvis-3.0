# ADR-002: Protocolo de Streaming (Server-Sent Events vs WebSockets)

## Status
Aceito

## Contexto
O modelo de linguagem local (Llama 3) gera respostas token por token. Para proporcionar uma experiência interativa sem tempo de espera perceptível no modo texto, o servidor precisa enviar fragmentos de texto à medida que são produzidos.

## Decisão
Adotamos **Server-Sent Events (SSE)** via `StreamingResponse` no FastAPI para o modo de chat por texto/fallback e **WebSockets** em `/ws/voice` para a comunicação integrada de áudio bidirecional.

### Motivação:
* **SSE (`StreamingResponse`)**:
  * Funciona sobre HTTP padrão (porta 8000), facilitando tratamento de erros, cabeçalhos de autorização e reconexão automática no cliente.
  * Baixa complexidade para respostas unidirecionais baseadas em texto.
* **WebSockets**:
  * Escolhido para a transmissão contínua de voz (upload PCM do microfone e download de áudio sintetizado TTS + texto).

## Consequências
* **Positivas**:
  * Respostas por texto renderizam dinamicamente estilo máquina de escrever.
  * Separação clara de responsabilidades entre o fluxo de voz contínuo e a API REST/SSE.
