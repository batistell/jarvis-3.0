# Processos e Fluxos de Controle (Workflows)

Este documento mapeia os fluxos operacionais detalhados do **Jarvis 3.0**, conectando os componentes físicos, APIs assíncronas do FastAPI e bibliotecas nativas em Python.

---

## 1. Loop de Voz Contínuo (Always-Listening Loop)

Este processo descreve como o sistema captura a voz do usuário em tempo real na rede local, transcreve com `faster-whisper` nativo em memória, processa na LLM via Ollama e retorna o áudio sintetizado com `piper-tts`.

```mermaid
sequenceDiagram
    autonumber
    actor User as Usuário
    participant FE as React Frontend (Navegador)
    participant BE as FastAPI Backend (Python)
    participant STT as faster-whisper (Em Memória)
    participant LLM as Llama 3 (Ollama AsyncClient)
    participant TTS as Piper TTS (Em Memória)

    User->>FE: Fala continuamente no microfone
    loop A cada 200ms
        FE->>BE: Transmite chunks binários PCM (WebSocket)
    end
    Note over FE, BE: VAD Local detecta silêncio prolongado no microfone
    FE->>BE: Envia mensagem de texto "SPEECH_END"
    BE->>STT: Passa o buffer de memória (NumPy array) para o modelo Whisper
    STT-->>BE: Retorna texto transcrito (ex: "Qual a previsão do tempo?")
    BE->>LLM: Envia texto transcrito com histórico de conversas (AsyncClient)
    
    loop Stream de resposta assíncrona
        LLM-->>BE: Retorna token de texto
        BE->>FE: Envia JSON com token de texto (WebSocket)
        BE->>TTS: Sintetiza token/frase em memória
        TTS-->>BE: Retorna bytes de áudio WAV/PCM
        BE->>FE: Envia bytes de áudio (WebSocket)
        FE->>User: Reproduz som via Web Audio API (player invisível)
    end
```

---

## 2. Fluxo de Execução de Automação Residencial (Tool Use / Function Calling)

Este processo descreve as chamadas de ferramentas dinâmicas disparadas pela inteligência artificial do Llama 3 para acionar lâmpadas e sensores integrados ao Home Assistant no Raspberry Pi.

```mermaid
sequenceDiagram
    autonumber
    actor User as Usuário
    participant FE as React Frontend
    participant BE as FastAPI Backend
    participant LLM as Llama 3 (Ollama)
    participant HA as Home Assistant (Raspberry Pi)

    User->>FE: Fala "Ligue a luz do quarto"
    Note over FE, BE: Streaming de voz e transcrição em memória via faster-whisper
    BE->>LLM: Envia texto transcrito com o esquema de ferramentas (tools)
    Note over LLM: LLM reconhece a intenção de ação e gera chamada de função
    LLM-->>BE: Retorna requisição de tool call: control_home_device(light.bedroom, turn_on)
    
    BE->>HA: Envia POST assíncrono via httpx (/api/services/light/turn_on com Bearer Token)
    Note over HA: Raspberry Pi aciona o relé/dispositivo físico do quarto
    HA-->>BE: Retorna resposta HTTP 200 OK (Sucesso)
    
    BE->>LLM: Retorna o resultado da execução da ferramenta para a LLM
    Note over LLM: Modelo reformula resposta final combinada com o resultado da ação
    LLM-->>BE: Retorna texto final ("Pronto! A luz do quarto já está ligada.")
    Note over BE, FE: Backend sintetiza para áudio em memória (Piper TTS) e envia texto + áudio
    FE->>User: Exibe texto na tela e reproduz som
```
