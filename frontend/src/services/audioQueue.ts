/**
 * Fila de reprodução assíncrona de áudio via Web Audio API (sem elementos HTML de player).
 */
export class AudioQueuePlayer {
  private audioContext: AudioContext | null = null;
  private queue: ArrayBuffer[] = [];
  private isPlaying: boolean = false;

  constructor() {
    // Inicialização sob demanda
  }

  private initAudioContext() {
    if (!this.audioContext) {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      this.audioContext = new AudioCtx();
    }
    if (this.audioContext.state === 'suspended') {
      this.audioContext.resume();
    }
  }

  public enqueueChunk(buffer: ArrayBuffer) {
    this.initAudioContext();
    this.queue.push(buffer);
    if (!this.isPlaying) {
      this.processNextChunk();
    }
  }

  private async processNextChunk() {
    if (this.queue.length === 0 || !this.audioContext) {
      this.isPlaying = false;
      return;
    }

    this.isPlaying = true;
    const rawBuffer = this.queue.shift()!;

    try {
      // Clona o ArrayBuffer para decodificação segura
      const bufferCopy = rawBuffer.slice(0);
      const audioBuffer = await this.audioContext.decodeAudioData(bufferCopy);
      
      const source = this.audioContext.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(this.audioContext.destination);

      source.onended = () => {
        this.processNextChunk();
      };

      source.start(0);
    } catch (err) {
      console.warn('Não foi possível decodificar chunk de áudio bruto via Web Audio API:', err);
      this.processNextChunk();
    }
  }

  public clear() {
    this.queue = [];
    this.isPlaying = false;
  }
}

export const audioQueuePlayer = new AudioQueuePlayer();
