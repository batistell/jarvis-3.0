# Jarvis 3.0 — Assistente Pessoal Inteligente em Python

O **Jarvis 3.0** é um assistente pessoal por voz e texto construído inteiramente em **Python (FastAPI)** no backend e **React (Vite)** no frontend. Ele é projetado para interações contínuas por voz (always-listening), com reconhecimento e síntese de voz reativos em tempo real (integrados nativamente via `faster-whisper` e `piper-tts`) e integração com o ecossistema de casa inteligente **Home Assistant** (executado em um Raspberry Pi local).

Ao contrário das versões anteriores em Java, o Jarvis 3.0 aproveita a integração direta do ecossistema Python para executar a transcrição de voz (STT) e a síntese de fala (TTS) em memória, sem a necessidade de contêineres adicionais ou pontes HTTP intermediárias.

---

## 🚀 Funcionalidades Principais

*   **Reconhecimento de Voz Contínuo (Always-Listening STT)**: O áudio é transmitido em tempo real pelo navegador via WebSockets binários e transcrito nativamente em memória pelo **faster-whisper**.
*   **Respostas Sonoras Reativas (TTS Real-time)**: As respostas textuais geradas pelo Llama 3 via Ollama são sintetizadas diretamente em Python (Piper TTS) e transmitidas ao navegador via WebSockets para execução imediata na Web Audio API.
*   **Integração Residencial (Home Assistant)**: Chamadas de função (*Function Calling / Tool Use*) nativas do modelo para acionar dispositivos físicos (luzes, tomadas, sensores) via API REST assíncrona (`httpx`).
*   **Segurança Local Robusta**: Autenticação via **Firebase Auth** (Google Sign-In) com verificação de tokens JWT via chaves públicas JWKS e restrição a e-mails autorizados na whitelist (`batistell.labs@gmail.com`).

---

## 🛠️ Pré-requisitos de Infraestrutura Local

Para rodar todo o ecossistema offline na rede doméstica:

1.  **Python 3.11+ / 3.12**: Ambiente de execução principal.
2.  **Ollama**: Instalado localmente com o modelo Llama 3 baixado:
    ```bash
    ollama run llama3
    ```
3.  **Bibliotecas STT e TTS Nativas**: Instaladas via PyPI (`faster-whisper`, `piper-tts` ou `kokoro-onnx`).
4.  **Home Assistant**: Instalação ativa na rede local (ex: Raspberry Pi) com Token de Acesso de Longa Duração gerado.
5.  **Firebase Project**: Projeto configurado no console do Firebase (`jarvis-1006b`) com autenticação Google ativada.

---

## 📁 Estrutura de Pastas

```text
jarvis-3.0/
├── AGENTS.md          # Regras globais para agentes de IA
├── README.md          # Guia de onboarding humano (este arquivo)
├── .env.example       # Modelo de variáveis de ambiente
├── docs/
│   ├── architecture/  # Visão detalhada da arquitetura técnica em Python
│   ├── decisions/     # ADRs (Architecture Decision Records)
│   ├── modules/       # Contexto e especificações de domínios
│   ├── api/           # Contratos de APIs REST, SSE e WebSockets
│   └── workflows/     # Processos e fluxos operacionais de controle
```

---

## ⚙️ Configuração e Execução

### 1. Configurando o Ambiente Python Backend
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```
O servidor backend inicializará em `http://localhost:8000` e abrirá o endpoint WebSocket de voz em `ws://localhost:8000/ws/voice`.

### 2. Inicializando o Frontend (React)
Entre na pasta do frontend, instale as dependências e inicie o Vite:
```bash
npm install
npm run dev
```
Acesse `http://localhost:5173` no seu navegador para interagir com o Jarvis 3.0.