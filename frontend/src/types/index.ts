export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';
export type VoiceState = 'idle' | 'listening' | 'transcribing' | 'thinking' | 'speaking';

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  status?: 'sending' | 'sent' | 'error';
  toolCall?: {
    name: string;
    entityId?: string;
    action?: string;
    status: 'executing' | 'success' | 'failed';
  };
}

export interface UserProfile {
  uid: string;
  email: string;
  displayName: string | null;
  photoURL: string | null;
}
