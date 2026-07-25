# Jarvis 3.0 - Visão Geral da Arquitetura

Este documento apresenta a visão técnica geral do **Jarvis 3.0**, um assistente pessoal inteligente construído com foco em interações por voz e texto em tempo real em **Python**, utilizando o framework assíncrono **FastAPI**, modelos de linguagem locais via **Ollama**, automação residencial via **Home Assistant**, síntese e reconhecimento de voz nativos em memória e segurança criptográfica via **Firebase Auth**.

---

## 1. Visão Geral do Sistema

O Jarvis 3.0 roda localmente na rede doméstica do usuário. O acesso à interface web e ao backend é protegido por autenticação **Firebase Authentication** integrada ao provedor de identidade do Google. O backend FastAPI valida a assinatura digital do ID Token do Firebase (via JWKS) e restringe o acesso estritamente aos e-mails autorizados (ex: `batistell.labs@gmail.com`), interagindo com o Ollama local e comandando o Home Assistant em um Raspberry Pi.

```mermaid
graph TD
    User([Usuário]) <-->|Voz / Texto / HTTP| FE[React Frontend]
    FE <-->|1. Stream de Áudio / WebSockets| BE[FastAPI Backend]
    BE <-->|Autenticação Google| FB[Firebase Auth / OIDC]
    BE <-->|2. Comandos Assíncronos / httpx| HA[Home Assistant (Raspberry Pi)]
    BE <-->|3. Áudio p/ Texto / Nativo em Memória| STT[faster-whisper (Python)]
    BE <-->|4. Texto p/ LLM / Ollama Python SDK| OL[Ollama Service]
    OL <-->|5. Chat / Tool Calls| LLM[Llama 3 Model]
    BE -->|6. Texto p/ Áudio / Nativo em Memória| TTS[Piper TTS (Python)]
```

---

## 2. Fluxo de Autenticação e Voz

1. **Autenticação Inicial (Frontend)**: O usuário tenta acessar a interface web local. Ele é direcionado para a autenticação do Firebase (Google Provider).
2. **Geração do Token**: O Firebase autentica o usuário e emite um ID Token JWT assinado pelo Google.
3. **Estabelecimento de Conexão WebSocket**:
   - O React Frontend estabelece conexão via WebSocket (`ws://localhost:8000/ws/voice?token=JWT_TOKEN`).
   - O FastAPI intercepta a requisição de handshake no endpoint WebSocket, decodifica o JWT do Firebase, valida a assinatura contra as chaves públicas da Google (JWKS URI), verifica se o e-mail está na lista de e-mails permitidos (ex: `batistell.labs@gmail.com`) e se foi verificado (`email_verified == true`).
   - Se aprovado, a conexão assíncrona bidirecional é liberada.
4. **Fluxo de Voz Contínuo**: A transmissão e reprodução do áudio ocorrem sob este canal seguro conforme descrito no fluxo de voz padrão.

---

## 3. Requisitos de Ambiente

Para o funcionamento completo da arquitetura local, a máquina de desenvolvimento/hospedagem deve atender aos seguintes requisitos:

*   **Python 3.11+ / 3.12**: Interpretador e ecossistema de dependências.
*   **Ollama**: Instalado e rodando como serviço em `http://localhost:11434` com o modelo `llama3`.
*   **Biblioteca STT (faster-whisper)**: Execução nativa de transcrição de voz em memória GPU/CPU via CTranslate2/PyTorch.
*   **Biblioteca TTS (piper-tts / kokoro-onnx)**: Motor nativo de síntese de voz em Python.
*   **Home Assistant**: Servidor local (Raspberry Pi) configurado com token de acesso de longa duração.
*   **Firebase Project**: Configurado na nuvem (`jarvis-1006b`) para realizar o login social Google.
*   **Node.js v18+**: Para compilação e execução do frontend React/Vite.
