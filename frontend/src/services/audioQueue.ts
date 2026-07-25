/**
 * AudioQueuePlayer — Reprodução gapless de chunks TTS via Web Audio API.
 *
 * Sentence-streaming: o backend envia N chunks tts_audio (um por frase).
 * Este player os agenda por tempo absoluto no AudioContext para reprodução
 * contínua sem gaps entre frases.
 */
export class AudioQueuePlayer {
  private audioContext: AudioContext | null = null;

  /** Fila de ArrayBuffers aguardando decode + agendamento. */
  private pendingQueue: ArrayBuffer[] = [];

  /** Ponto no tempo (AudioContext) onde o próximo chunk deve começar. */
  private scheduledEndTime: number = 0;

  /** Fontes ativas — necessário para interrupção imediata. */
  private activeSources: AudioBufferSourceNode[] = [];

  /** Callbacks externos */
  private _onPlayingChange: ((playing: boolean) => void) | null = null;
  private _isPlaying: boolean = false;
  private _isProcessing: boolean = false;

  // -------------------------------------------------------------------------
  // Public API
  // -------------------------------------------------------------------------

  /** Registra callback chamado quando o estado de reprodução muda. */
  public onPlayingChange(fn: (playing: boolean) => void): () => void {
    this._onPlayingChange = fn;
    return () => { this._onPlayingChange = null; };
  }

  /**
   * Enfileira um ArrayBuffer (MP3) para reprodução.
   * O decode é feito imediatamente de forma assíncrona para minimizar gaps.
   */
  public enqueueChunk(buffer: ArrayBuffer): void {
    this._ensureAudioContext();
    this.pendingQueue.push(buffer);
    if (!this._isProcessing) {
      this._processPending();
    }
  }

  /**
   * Interrompe toda a reprodução imediatamente e limpa a fila.
   * Útil quando o usuário começa a falar enquanto o Jarvis ainda fala.
   */
  public interrupt(): void {
    // Para todas as fontes ativas
    for (const source of this.activeSources) {
      try { source.stop(); source.disconnect(); } catch { /* já parada */ }
    }
    this.activeSources = [];
    this.pendingQueue = [];
    this.scheduledEndTime = 0;
    this._isProcessing = false;
    this._setPlaying(false);
  }

  /** Retorna true se houver áudio tocando ou na fila. */
  public get isPlaying(): boolean {
    return this._isPlaying;
  }

  // -------------------------------------------------------------------------
  // Internal
  // -------------------------------------------------------------------------

  private _ensureAudioContext(): void {
    if (!this.audioContext) {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      this.audioContext = new AudioCtx();
    }
    if (this.audioContext.state === 'suspended') {
      this.audioContext.resume();
    }
  }

  private async _processPending(): Promise<void> {
    if (this._isProcessing || !this.audioContext) return;
    this._isProcessing = true;

    while (this.pendingQueue.length > 0) {
      const raw = this.pendingQueue.shift()!;
      try {
        // Decode assíncrono (CPU — não bloqueia o main thread)
        const bufferCopy = raw.slice(0);
        const audioBuffer = await this.audioContext.decodeAudioData(bufferCopy);

        const ctx = this.audioContext;
        const now = ctx.currentTime;

        // O próximo chunk começa logo após o anterior terminar (gapless)
        const startAt = Math.max(now + 0.01, this.scheduledEndTime);
        this.scheduledEndTime = startAt + audioBuffer.duration;

        const source = ctx.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(ctx.destination);
        this.activeSources.push(source);

        // Atualiza o VoiceOrb assim que o primeiro chunk começar
        if (!this._isPlaying) {
          this._setPlaying(true);
        }

        source.onended = () => {
          this.activeSources = this.activeSources.filter(s => s !== source);
          // Verifica se foi a última fonte ativa e a fila está vazia
          if (this.activeSources.length === 0 && this.pendingQueue.length === 0) {
            this._setPlaying(false);
          }
        };

        source.start(startAt);
      } catch (err) {
        console.warn('[AudioQueue] Erro ao decodificar chunk MP3:', err);
      }
    }

    this._isProcessing = false;
  }

  private _setPlaying(playing: boolean): void {
    if (this._isPlaying !== playing) {
      this._isPlaying = playing;
      this._onPlayingChange?.(playing);
    }
  }
}

export const audioQueuePlayer = new AudioQueuePlayer();
