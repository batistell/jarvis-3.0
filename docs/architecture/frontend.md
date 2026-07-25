# Jarvis 3.0 - Arquitetura Frontend

O frontend do Jarvis 3.0 é construído em **React** com **TypeScript** e **Vite**, projetado para interação fluida por voz e texto em tempo real com a API assíncrona em **Python (FastAPI)**.

---

## 1. Tecnologias & Visual

*   **Vite + React**: Inicialização instantânea, HMR super-rápido e compatibilidade nativa com TypeScript.
*   **TypeScript**: Garantia de tipagem estática para troca de mensagens e eventos WebSocket.
*   **Vanilla Custom CSS**: Estilização direta sem dependências pesadas.
*   **Identidade Visual (HUD Futurista Escuro)**:
    *   Fundo escuro profundo (`#0d0f12`).
    *   Cores neon: Azul Ciano Neon (`#00f0ff`) para estado de prontidão/conectado e Verde Esmeralda Neon (`#39ff14`) para capturas de áudio/síntese ativa.
    *   Efeitos de vidrofosco (glassmorphism) e micro-animações.

---

## 2. Consumo de Stream em Tempo Real (SSE)

O frontend lê a stream de resposta enviada pelo endpoint FastAPI (`POST /api/chat/stream`) e atualiza o estado da conversa incrementalmente.

```typescript
import React, { useState } from 'react';

export const ChatWindow: React.FC = () => {
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([]);
  const [input, setInput] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);

  const sendMessage = async () => {
    if (!input.trim() || isGenerating) return;

    const userMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsGenerating(true);

    const jarvisMessageIndex = messages.length + 1;
    setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

    try {
      const response = await fetch('http://localhost:8000/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: input })
      });

      if (!response.body) throw new Error('ReadableStream não suportado.');

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let done = false;

      while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;
        
        if (value) {
          const chunk = decoder.decode(value, { stream: !done });
          const lines = chunk.split('\n');
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.substring(6));
                setMessages(prev => {
                  const updated = [...prev];
                  const assistantMsg = updated[jarvisMessageIndex];
                  if (assistantMsg) {
                    assistantMsg.content += data.content;
                  }
                  return updated;
                });
              } catch (e) {
                // ignorar linhas parciais
              }
            }
          }
        }
      }
    } catch (error) {
      console.error('Erro na leitura da stream:', error);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    // Componente JSX
  );
};
```

---

## 3. Captura & Reprodução de Voz (Web Audio API & WebSockets)

O frontend captura áudio bruto do microfone em formato PCM 16-bit Mono a 16000 Hz, monitora a amplitude para detecção de silêncio (VAD no cliente) e transmite chunks binários diretamente para o endpoint `ws://localhost:8000/ws/voice` do FastAPI.

### Mecanismo de Captura PCM e VAD Local:

```typescript
const startVoiceCapture = async (token: string) => {
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${wsProtocol}//localhost:8000/ws/voice?token=${encodeURIComponent(token)}`;
  const socket = new WebSocket(wsUrl);
  
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 });
  const source = audioContext.createMediaStreamSource(stream);
  const processor = audioContext.createScriptProcessor(4096, 1, 1);
  
  let silenceStart = 0;
  const SILENCE_THRESHOLD = 0.025;
  const SILENCE_DURATION_MS = 800;
  
  processor.onaudioprocess = (e) => {
    const inputData = e.inputBuffer.getChannelData(0);
    const pcmData = new Int16Array(inputData.length);
    let sumSquares = 0;
    
    for (let i = 0; i < inputData.length; i++) {
      const s = Math.max(-1, Math.min(1, inputData[i]));
      pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
      sumSquares += s * s;
    }
    
    if (socket.readyState === WebSocket.OPEN) {
      socket.send(pcmData.buffer);
    }
    
    const rms = Math.sqrt(sumSquares / inputData.length);
    if (rms < SILENCE_THRESHOLD) {
      if (silenceStart === 0) {
        silenceStart = Date.now();
      } else if (Date.now() - silenceStart > SILENCE_DURATION_MS) {
        if (socket.readyState === WebSocket.OPEN) {
          socket.send("SPEECH_END");
        }
        silenceStart = 0;
      }
    } else {
      silenceStart = 0;
    }
  };
  
  source.connect(processor);
  processor.connect(audioContext.destination);
};
```

---

## 4. Autenticação do Usuário (Firebase + Google Sign-In)

O frontend integra o SDK do Firebase Auth para obter o ID Token JWT do usuário autenticado e repassá-lo ao backend FastAPI durante o handshake do WebSocket ou via header `Authorization: Bearer <TOKEN>` nas chamadas REST.
