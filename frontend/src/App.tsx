import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { VoiceOrb } from './components/VoiceOrb';
import { ChatWindow } from './components/ChatWindow';
import { MessageInput } from './components/MessageInput';
import { ControlPanel } from './components/ControlPanel';
import { GPUHealthWidget } from './components/GPUHealthWidget';
import { AuthModal } from './components/AuthModal';
import { ConnectionStatus, VoiceState, Message, UserProfile } from './types';
import { useVoiceRecorder } from './hooks/useVoiceRecorder';
import { jarvisSocket } from './services/websocket';
import { audioQueuePlayer } from './services/audioQueue';
import { loginWithGoogle, logoutFirebase, auth } from './services/firebase';
import { onAuthStateChanged } from 'firebase/auth';

export const App: React.FC = () => {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const [voiceState, setVoiceState] = useState<VoiceState>('idle');
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [partialTranscript, setPartialTranscript] = useState<string>('');

  // Hook de gravação de voz PCM 16kHz com seleção de microfone
  const {
    isRecording,
    volumeLevel,
    audioDevices,
    selectedDeviceId,
    setSelectedDeviceId,
    refreshDevices,
    startRecording,
    stopRecording
  } = useVoiceRecorder();

  // Monitora estado de autenticação do Firebase
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (fbUser) => {
      if (fbUser) {
        setUser({
          uid: fbUser.uid,
          email: fbUser.email || '',
          displayName: fbUser.displayName,
          photoURL: fbUser.photoURL
        });
      } else {
        // Fallback em Dev Preview se não autenticado
        setUser({
          uid: 'dev-uid-123',
          email: 'batistell.labs@gmail.com',
          displayName: 'Batistell (Dev)',
          photoURL: null
        });
      }
    });
    return () => unsubscribe();
  }, []);

  // Sincroniza VoiceState com o estado real de reprodução de áudio do TTS
  useEffect(() => {
    const unsub = audioQueuePlayer.onPlayingChange((playing) => {
      setVoiceState((prev) => {
        // Só altera para 'speaking' ou 'idle' quando o áudio muda de estado
        // Não sobrescreve 'listening', 'transcribing' ou 'thinking'
        if (playing) return 'speaking';
        if (prev === 'speaking') return 'idle';
        return prev;
      });
    });
    return unsub;
  }, []);

  // Inicializa o WebSocket
  useEffect(() => {
    const unsubState = jarvisSocket.onStateChange((status) => {
      setConnectionStatus(status);
    });

    const unsubText = jarvisSocket.onTextMessage((data) => {
      if (data.type === 'stt_partial') {
        setPartialTranscript(data.text);
        setVoiceState('listening');
        // Interrompe o áudio TTS se o usuário começou a falar enquanto o Jarvis falava
        if (audioQueuePlayer.isPlaying) {
          audioQueuePlayer.interrupt();
        }
      } else if (data.type === 'stt_status') {
        if (data.status === 'transcribing') {
          setVoiceState('transcribing');
        } else if (data.status === 'idle') {
          setVoiceState('idle');
          setPartialTranscript('');
        }
      } else if (data.type === 'stt_result') {
        setPartialTranscript('');
        setVoiceState('thinking');
        const userMsg: Message = {
          id: Date.now().toString(),
          role: 'user',
          content: data.text,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        };
        setMessages((prev) => {
          const lastMsg = prev[prev.length - 1];
          if (lastMsg && lastMsg.role === 'user' && lastMsg.content === data.text) {
            return prev;
          }
          return [...prev, userMsg];
        });
      } else if (data.type === 'llm_chunk' || data.type === 'text_token') {
        const tokenText = data.text || data.content || '';
        setVoiceState('speaking');
        setIsGenerating(true);
        setMessages((prev) => {
          const updated = [...prev];
          const lastMsg = updated[updated.length - 1];
          if (lastMsg && lastMsg.role === 'assistant') {
            return [
              ...updated.slice(0, updated.length - 1),
              { ...lastMsg, content: lastMsg.content + tokenText }
            ];
          } else {
            return [
              ...updated,
              {
                id: Date.now().toString(),
                role: 'assistant',
                content: tokenText,
                timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
              }
            ];
          }
        });
      } else if (data.type === 'llm_result') {
        // Só vai para idle se não houver áudio ainda tocando
        setIsGenerating(false);
        if (!audioQueuePlayer.isPlaying) {
          setVoiceState('idle');
        }
      } else if (data.type === 'tts_audio' && data.audio) {
        try {
          const binaryString = window.atob(data.audio);
          const len = binaryString.length;
          const bytes = new Uint8Array(len);
          for (let i = 0; i < len; i++) {
            bytes[i] = binaryString.charCodeAt(i);
          }
          audioQueuePlayer.enqueueChunk(bytes.buffer);
        } catch (err) {
          console.error('Erro ao decodificar e tocar áudio TTS no navegador:', err);
        }
      }
    });

    jarvisSocket.connect('dev-jwt-token');

    return () => {
      unsubText();
      unsubState();
      jarvisSocket.disconnect();
    };
  }, []);

  const handleToggleRecord = () => {
    if (isRecording) {
      stopRecording();
      setVoiceState('idle');
      setPartialTranscript('');
    } else {
      // Interrompe o TTS antes de começar a gravar
      if (audioQueuePlayer.isPlaying) {
        audioQueuePlayer.interrupt();
      }
      startRecording();
      setVoiceState('listening');
    }
  };

  const handleSendMessage = (text: string) => {
    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
    setMessages((prev) => [...prev, userMsg]);

    setIsGenerating(true);
    setVoiceState('thinking');

    // Envia o comando via WebSocket
    jarvisSocket.sendText(text);
  };

  const handleLoginGoogle = async () => {
    const u = await loginWithGoogle();
    if (u) {
      setUser({
        uid: u.uid,
        email: u.email || '',
        displayName: u.displayName,
        photoURL: u.photoURL
      });
      setIsAuthModalOpen(false);
    }
  };

  const handleLogout = async () => {
    await logoutFirebase();
    setUser(null);
  };

  return (
    <div className="min-h-screen p-4 md:p-8 flex flex-col max-w-6xl mx-auto">
      {/* Top Header */}
      <Header
        connectionStatus={connectionStatus}
        voiceState={voiceState}
        user={user}
        audioDevices={audioDevices}
        selectedDeviceId={selectedDeviceId}
        onSelectDevice={setSelectedDeviceId}
        onRefreshDevices={refreshDevices}
        onOpenAuth={() => setIsAuthModalOpen(true)}
        onLogout={handleLogout}
      />

      {/* Main Content Layout */}
      <main className="flex-1 flex flex-col gap-4">
        {/* Holographic Central Voice Orb */}
        <VoiceOrb
          voiceState={voiceState}
          volumeLevel={volumeLevel}
          isRecording={isRecording}
          onToggleRecord={handleToggleRecord}
          partialTranscript={partialTranscript}
        />

        {/* Chat Timeline */}
        <ChatWindow messages={messages} isGenerating={isGenerating} />

        {/* Input Controls */}
        <MessageInput
          onSendMessage={handleSendMessage}
          isRecording={isRecording}
          onToggleRecord={handleToggleRecord}
        />

        {/* Home Assistant Quick Actions */}
        <ControlPanel onQuickAction={handleSendMessage} />

        {/* GPU & AI Models Health Monitoring Widget */}
        <GPUHealthWidget />
      </main>

      {/* Auth Modal */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        onLoginGoogle={handleLoginGoogle}
        onBypassDev={() => setIsAuthModalOpen(false)}
      />
    </div>
  );
};
