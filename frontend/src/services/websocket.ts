import { audioQueuePlayer } from './audioQueue';

export type WebSocketMessageCallback = (data: any) => void;
export type WebSocketBinaryCallback = (buffer: ArrayBuffer) => void;

export class JarvisWebSocketClient {
  private socket: WebSocket | null = null;
  private url: string = '';
  private onTextMessageCallbacks: WebSocketMessageCallback[] = [];
  private onBinaryMessageCallbacks: WebSocketBinaryCallback[] = [];
  private onStateChangeCallbacks: ((status: 'disconnected' | 'connecting' | 'connected' | 'error') => void)[] = [];

  constructor(baseUrl: string = 'ws://localhost:8000/ws/voice') {
    this.url = baseUrl;
  }

  public connect(token: string = 'dev-token') {
    if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this.notifyState('connecting');
    const fullUrl = `${this.url}?token=${encodeURIComponent(token)}`;
    
    try {
      this.socket = new WebSocket(fullUrl);
      this.socket.binaryType = 'arraybuffer';

      this.socket.onopen = () => {
        console.log('⚡ Conexão WebSocket com Jarvis 3.0 estabelecida.');
        this.notifyState('connected');
      };

      this.socket.onmessage = (event: MessageEvent) => {
        if (typeof event.data === 'string') {
          try {
            const parsed = JSON.parse(event.data);
            this.onTextMessageCallbacks.forEach(cb => cb(parsed));
          } catch {
            this.onTextMessageCallbacks.forEach(cb => cb({ type: 'text_token', content: event.data }));
          }
        } else if (event.data instanceof ArrayBuffer) {
          audioQueuePlayer.enqueueChunk(event.data);
          this.onBinaryMessageCallbacks.forEach(cb => cb(event.data));
        }
      };

      this.socket.onerror = (err) => {
        console.error('❌ Erro no WebSocket do Jarvis:', err);
        this.notifyState('error');
      };

      this.socket.onclose = () => {
        console.log('🔌 Conexão WebSocket encerrada.');
        this.notifyState('disconnected');
      };
    } catch (e) {
      console.error('Falha ao abrir WebSocket:', e);
      this.notifyState('error');
    }
  }

  public sendBinary(data: ArrayBuffer) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(data);
    }
  }

  public sendText(text: string) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(text);
    }
  }

  public disconnect() {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }

  public onTextMessage(cb: WebSocketMessageCallback) {
    this.onTextMessageCallbacks.push(cb);
  }

  public onStateChange(cb: (status: 'disconnected' | 'connecting' | 'connected' | 'error') => void) {
    this.onStateChangeCallbacks.push(cb);
  }

  private notifyState(status: 'disconnected' | 'connecting' | 'connected' | 'error') {
    this.onStateChangeCallbacks.forEach(cb => cb(status));
  }
}

export const jarvisSocket = new JarvisWebSocketClient();
