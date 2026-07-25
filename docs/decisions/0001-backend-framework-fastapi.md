# ADR-001: Escolha do Framework Backend (Python & FastAPI)

## Status
Aceito

## Contexto
O Jarvis 2.0 foi construído em Java Spring Boot. No entanto, os principais motores de inteligência artificial de código aberto — como Whisper (Speech-To-Text), Piper/Kokoro (Text-To-Speech) e bibliotecas de modelos de linguagem — possuem suporte primário, otimizações em C++/CUDA e bindings nativos de altíssimo desempenho no ecossistema **Python**.

Precisamos de um framework backend em Python que suporte concorrência assíncrona de alta performance, manipulação nativa de WebSockets (dados binários e texto), suporte a Server-Sent Events (SSE) e validação estrita de dados.

## Decisão
Decidimos utilizar **Python 3.11+** com o framework **FastAPI** executado sobre o servidor ASGI **Uvicorn** como a base da arquitetura do backend do Jarvis 3.0.

### Principais Motivos:
1. **Integração Direta com IA & Som**: Permite carregar e executar o modelo de transcrição (`faster-whisper`) e de fala (`piper-tts`) diretamente na memória do processo Python, eliminando dependências de serviços HTTP externos intermediários.
2. **Performance Assíncrona Nativa**: Construído sobre Starlette e `asyncio`, o FastAPI lida eficientemente com conexões WebSocket persistentes e streams de longo término.
3. **Pydantic v2**: Validação estrita e de alto desempenho dos dados transmitidos nas requisições e nos esquemas de Function Calling.

## Consequências
* **Positivas**:
  * Menor consumo de memória e latência reduzida no processamento de voz.
  * Código extremamente limpo, moderno e legível com `async`/`await`.
  * Ecossistema totalmente unificado de machine learning e áudio.
* **Negativas**:
  * É necessário tomar cuidado para não executar rotas bloqueantes de CPU (CPU-bound) diretamente na thread principal do event loop do `asyncio` (usando `asyncio.to_thread` quando necessário).
