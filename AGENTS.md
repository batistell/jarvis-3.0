# Regras Globais para Agentes — Jarvis 3.0

Este documento serve como diretriz global para qualquer agente de Inteligência Artificial que execute tarefas, refatore códigos ou adicione novas funcionalidades a este repositório. **Siga estas regras sem exceções.**

---

## 1. Visão Geral da Stack & Arquitetura

O **Jarvis 3.0** é um assistente pessoal local projetado para interações de voz contínuas (always-listening) construído inteiramente com o ecossistema Python.

*   **Backend**: Python 3.11+, FastAPI, Uvicorn, `asyncio`, Ollama Python SDK, `faster-whisper`, `piper-tts`.
*   **Frontend**: React (Vite), TypeScript, Web Audio API.
*   **Banco de Dados**: SQLite com SQLAlchemy 2.0 Async (desenvolvimento), migrável para PostgreSQL via `asyncpg`.
*   **Migrações**: **Alembic** para versionamento de schema SQL.
*   **Segurança**: Autenticação Firebase (Google Provider) local com PyJWT / JWKS e whitelist de e-mails. **Sem exposição via túnel de internet (Cloudflare desativado).**

---

## 2. Padrões de Código e Diretrizes

### Backend (Python + FastAPI)
1.  **Assincronismo Native**: Use `async`/`await` em todas as rotas e manipuladores de WebSockets. Evite operações bloqueantes de I/O na thread principal da chamada do `asyncio`.
2.  **WebSocket Handler**: O handler principal de voz é o `/ws/voice` (WebSocket binário bidirecional). Evite endpoints REST síncronos para o fluxo principal de voz.
3.  **Processamento de Áudio Nativo**: O Whisper e o Piper/Kokoro devem ser executados em memória no processo Python (ou via executores em threads separadas com `asyncio.to_thread` se CPU-bound) para não bloquear o event loop.
4.  **Autenticação**: Todos os endpoints REST e handshakes de WebSocket devem validar o ID Token do Firebase via chaves JWKS do Google (`https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com`), filtrando pelo e-mail verificado na whitelist (`batistell.labs@gmail.com`).

### Frontend (React + TypeScript)
1.  **Fila de Áudio (Audio Queue)**: A reprodução sonora da resposta da IA deve ser feita via Web Audio API (`AudioContext`), decodificando e tocando chunks binários sequencialmente de forma assíncrona, **sem expor nenhum elemento HTML de player de áudio na interface**.
2.  **Captação de Microfone**: Use `MediaRecorder` ou `AudioWorklet` / `ScriptProcessorNode` para empacotar frames curtos de áudio PCM 16-bit Mono (ex: 200ms) e enviar via conexão ativa do WebSocket.
3.  **Estilo Visual**: Use Custom CSS para manter a estética premium estilo HUD futurista escuro (tons de preto profundo `#0d0f12`, azul ciano neon `#00f0ff` e verde neon `#39ff14`). Evite frameworks pesados.

---

## 3. Modificações de Banco de Dados
*   Toda alteração de banco de dados deve ser versionada com migrações **Alembic** na pasta `alembic/versions/`.
*   Nunca altere schemas diretamente no banco sem criar uma nova migração com o Alembic (`alembic revision --autogenerate -m "descrição"`).

---

## 4. O que NÃO Fazer
*   **NÃO** tente expor a aplicação na internet usando túneis como Cloudflare ou ngrok no código principal, a não ser que explicitamente instruído pelo usuário.
*   **NÃO** remova a validação de token do Firebase de endpoints REST/WebSocket.
*   **NÃO** utilize arquivos de chave de serviço locais do Firebase Admin SDK (`serviceAccountKey.json`). A validação deve ser puramente criptográfica (JWKS).
*   **NÃO** crie wrappers HTTP ou contêineres Docker separados para o Whisper ou TTS se eles puderem ser invocados nativamente pela aplicação Python.
