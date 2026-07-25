# Jarvis 3.0 — Arquitetura Frontend

O frontend do Jarvis 3.0 é uma **SPA (Single Page Application)** construída com **React 18 + Vite + TypeScript**. A interface mantém uma estética HUD futurista escuro com tons neon e se comunica com o backend exclusivamente via **WebSocket binário bidirecional**.

---

## 1. Stack Tecnológico

| Tecnologia | Uso |
|---|---|
| **React 18 + Vite** | Framework e bundler |
| **TypeScript** | Tipagem estática |
| **Web Audio API (`AudioContext`)** | Reprodução de áudio TTS sem `<audio>` no DOM |
| **MediaRecorder / `getUserMedia`** | Captura de microfone |
| **WebSocket API nativa** | Comunicação com o backend |
| **Lucide React** | Ícones |
| **Custom CSS** | Design HUD futurista (sem Tailwind) |
| **Firebase SDK** | Autenticação Google Sign-In |

---

## 2. Estrutura de Componentes

```
App.tsx                         — Orquestrador principal (WebSocket, Audio Queue, state)
├── Header.tsx                  — HUD superior: status, usuário, microfone
│   └── MicrophoneSelector.tsx  — Dropdown de seleção de dispositivo de entrada
├── VoiceOrb.tsx                — Orb animado central (idle → listening → thinking → speaking)
├── ChatWindow.tsx              — Timeline de mensagens com streaming de tokens em tempo real
├── MessageInput.tsx            — Input de texto + botão de gravação
├── ControlPanel.tsx            — Ações rápidas (automação doméstica)
├── GPUHealthWidget.tsx         — Monitoramento em tempo real da GPU e latências dos modelos
└── AuthModal.tsx               — Modal de autenticação Firebase Google
```

---

## 3. Fluxo de Áudio (Gravação e Reprodução)

### Captura de Voz (`useVoiceRecorder.ts`)

```
getUserMedia({ audio: { deviceId, sampleRate: 16000 } })
    │
    ↓ MediaRecorder (chunks 200ms) ou AudioWorklet (PCM raw)
    │
    ↓ WebSocket.send(pcmChunk: ArrayBuffer)  → Backend
```

- O usuário pode selecionar qualquer microfone ativo via `MicrophoneSelector`
- Os dispositivos são enumerados via `navigator.mediaDevices.enumerateDevices()`
- A troca de microfone é suportada em tempo real sem reconectar o WebSocket

### Reprodução de TTS (AudioQueuePlayer em `App.tsx`)

```
WebSocket.onmessage ({ type: "tts_audio", audio: base64 })
    │
    ↓ atob(base64) → ArrayBuffer
    │
    ↓ AudioContext.decodeAudioData(arrayBuffer)
    │
    ↓ AudioBufferSourceNode.start()  → 🔊 Fala no Browser
```

- O áudio é **enfileirado** sequencialmente — nunca há sobreposição de chunks
- Sem elemento `<audio>` no DOM — 100% via Web Audio API
- Funciona em qualquer dispositivo que acesse a interface, mesmo remotamente

---

## 4. Payloads WebSocket Recebidos

| `type` | Ação no Frontend |
|---|---|
| `stt_status` (transcribing) | VoiceOrb → estado `thinking` |
| `stt_result` | Adiciona mensagem do usuário no ChatWindow |
| `partial_stt` | Atualiza transcrição parcial no VoiceOrb |
| `llm_status` (generating) | VoiceOrb → estado `thinking`, `isGenerating = true` |
| `llm_chunk` | Streaming de tokens ao vivo na última mensagem do ChatWindow |
| `llm_result` | Mensagem do assistente finalizada |
| `tts_audio` | Decodifica Base64 → AudioContext → reproduz fala |

---

## 5. Monitoramento de GPU (`GPUHealthWidget.tsx`)

Widget exibido no rodapé da interface que consome `GET /api/health` a cada 5 segundos:

- **VRAM**: Barra visual de uso percentual (verde → amarelo → vermelho em >90%)
- **Carga CUDA**: % de utilização dos shaders CUDA
- **Temperatura**: °C da GPU
- **Latência STT**: Tempo de transcrição do Whisper da última fala (ms)
- **Latência LLM**: Tempo de geração do Qwen 2.5 (ms)
- **Latência TTS**: Tempo de síntese do Remy (ms)
- **Botão LIMPAR VRAM**: Dispara `POST /api/health/gc` para forçar garbage collection

---

## 6. Design Visual

A interface segue uma estética **HUD futurista escuro**:

- **Cor de fundo**: `#0d0f12` (preto profundo)
- **Cyan neon primário**: `#00f0ff`
- **Verde neon secundário**: `#39ff14`
- **Glassmorphism**: Painéis com `backdrop-filter: blur(...)` e bordas `cyan/20`
- **Tipografia**: Font `Orbitron` (HUD/tech) + `Inter` (corpo)
- **Animações**: Pulsação do VoiceOrb, spinner de carregamento, gradientes animados
- **Sem Tailwind** — Custom CSS puro para controle total da estética
