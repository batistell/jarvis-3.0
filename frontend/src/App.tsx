import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { VoiceOrb } from './components/VoiceOrb';
import { ChatWindow } from './components/ChatWindow';
import { MessageInput } from './components/MessageInput';
import { ControlPanel } from './components/ControlPanel';
import { AuthModal } from './components/AuthModal';
import { ConnectionStatus, VoiceState, Message, UserProfile } from './types';
import { useVoiceRecorder } from './hooks/useVoiceRecorder';
import { jarvisSocket } from './services/websocket';
import { loginWithGoogle, logoutFirebase, auth } from './services/firebase';
import { onAuthStateChanged } from 'firebase/auth';

export const App: React.FC = () => {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const [voiceState, setVoiceState] = useState<VoiceState>('idle');
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);

  // Hook de gravação de voz PCM 16kHz
  const { isRecording, volumeLevel, startRecording, stopRecording } = useVoiceRecorder({
    onSpeechEnd: () => {
      setVoiceState('transcribing');
    }
  });

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

  // Inicializa o WebSocket
  useEffect(() => {
    jarvisSocket.onStateChange((status) => {
      setConnectionStatus(status);
    });

    jarvisSocket.onTextMessage((data) => {
      if (data.type === 'stt_status') {
        if (data.status === 'transcribing') {
          setVoiceState('transcribing');
        } else if (data.status === 'idle') {
          setVoiceState('idle');
        }
      } else if (data.type === 'stt_result') {
        setVoiceState('thinking');
        const userMsg: Message = {
          id: Date.now().toString(),
          role: 'user',
          content: data.text,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        };
        setMessages((prev) => [...prev, userMsg]);
      } else if (data.type === 'text_token') {
        setVoiceState('speaking');
        setMessages((prev) => {
          const updated = [...prev];
          const lastMsg = updated[updated.length - 1];
          if (lastMsg && lastMsg.role === 'assistant') {
            lastMsg.content += data.content;
          }
          return [...updated];
        });
      }
    });

    jarvisSocket.connect('dev-jwt-token');

    return () => {
      jarvisSocket.disconnect();
    };
  }, []);

  const handleToggleRecord = () => {
    if (isRecording) {
      stopRecording();
      setVoiceState('idle');
    } else {
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

    const jarvisMsg: Message = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: '',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
    setMessages((prev) => [...prev, jarvisMsg]);

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
