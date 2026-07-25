# Registros de Decisão de Arquitetura (ADRs)

Este diretório contém as decisões formais de arquitetura tomadas para o desenvolvimento do **Jarvis 3.0**.

## Índice de ADRs

1.  **[ADR-001: Escolha do Framework Backend (Python & FastAPI)](file:///f:/projects/jarvis-3.0/docs/decisions/0001-backend-framework-fastapi.md)**
    *   Uso do ecossistema Python com FastAPI e asyncio para simplificar integrações diretas de IA (STT, TTS e Ollama).
2.  **[ADR-002: Protocolo de Streaming (Server-Sent Events vs WebSockets)](file:///f:/projects/jarvis-3.0/docs/decisions/0002-realtime-communication-sse.md)**
    *   Definição de SSE e WebSockets assíncronos no FastAPI para transporte de dados em tempo real.
3.  **[ADR-003: Execução Local de LLM com Ollama Python SDK (Llama 3)](file:///f:/projects/jarvis-3.0/docs/decisions/0003-local-llm-ollama.md)**
    *   Uso da biblioteca oficial `ollama.AsyncClient` para interação assíncrona local com a LLM.
4.  **[ADR-004: Escolha do Framework Frontend (React & Vite)](file:///f:/projects/jarvis-3.0/docs/decisions/0004-frontend-framework-react.md)**
    *   Manutenção da pilha React + Vite no frontend para controle dinâmico da stream e áudio.
5.  **[ADR-005: Banco de Dados de Desenvolvimento (SQLite Assíncrono com SQLAlchemy & Alembic)](file:///f:/projects/jarvis-3.0/docs/decisions/0005-database-sqlite-development.md)**
    *   Utilização do SQLite assíncrono com SQLAlchemy 2.0 e Alembic para migrações leves.
6.  **[ADR-006: Integração com Home Assistant via REST API Assíncrona (httpx)](file:///f:/projects/jarvis-3.0/docs/decisions/0006-home-assistant-integration.md)**
    *   Integração do Llama 3 via Function Calling do Ollama com chamadas HTTP assíncronas via `httpx`.
7.  **[ADR-007: Protocolo para Transmissão de Voz (WebSockets com STT e TTS Nativos em Memória)](file:///f:/projects/jarvis-3.0/docs/decisions/0007-realtime-voice-communication-websockets.md)**
    *   Uso do WebSockets no FastAPI com `faster-whisper` e `piper-tts` rodando nativamente em memória.
8.  **[ADR-008: Autenticação via Firebase (Google Sign-In) e Restrição de E-mail em Python](file:///f:/projects/jarvis-3.0/docs/decisions/0008-authentication-firebase-allowed-emails.md)**
    *   Validação criptográfica de tokens Firebase JWT via PyJWT e JWKS do Google com whitelist de e-mails.
