import { useState, useRef, useCallback } from 'react';
import { jarvisSocket } from '../services/websocket';

export const useVoiceRecorder = () => {
  const [isRecording, setIsRecording] = useState(false);
  const [volumeLevel, setVolumeLevel] = useState<number>(0);
  const audioContextRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);

  const startRecording = useCallback(async () => {
    try {
      console.log('🎙️ [STT DEBUG] Solicitando permissão de microfone...');
      
      // Garantir conexão WebSocket ativa
      jarvisSocket.connect('dev-jwt-token');

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true
        }
      });
      streamRef.current = stream;

      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      const audioContext = new AudioCtx({ sampleRate: 16000 });
      
      if (audioContext.state === 'suspended') {
        await audioContext.resume();
        console.log('🎙️ [STT DEBUG] AudioContext resumido de suspended para running.');
      }

      audioContextRef.current = audioContext;

      const source = audioContext.createMediaStreamSource(stream);
      // bufferSize=4096 (~256ms por frame PCM a 16kHz)
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor; // Evita garbage collection do node no browser

      let frameCount = 0;

      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);
        const pcmData = new Int16Array(inputData.length);
        let sumSquares = 0;

        for (let i = 0; i < inputData.length; i++) {
          const s = Math.max(-1, Math.min(1, inputData[i]));
          pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
          sumSquares += s * s;
        }

        frameCount++;
        if (frameCount % 10 === 0) {
          console.log(`🎙️ [STT STREAMING] Enviando frame #${frameCount} (${pcmData.byteLength} bytes PCM) ao backend...`);
        }

        // Transmite o buffer PCM bruto via WebSocket
        jarvisSocket.sendBinary(pcmData.buffer);

        // Atualiza o medidor visual de volume
        const rms = Math.sqrt(sumSquares / inputData.length);
        setVolumeLevel(Math.min(1, rms * 5));
      };

      source.connect(processor);

      // Conecta o processor a um canal mudo para manter o audioContext ativo sem microfonia
      const silenceGain = audioContext.createGain();
      silenceGain.gain.value = 0;
      processor.connect(silenceGain);
      silenceGain.connect(audioContext.destination);

      setIsRecording(true);
      console.log('✅ [STT DEBUG] Captação de microfone ativada e transmitindo em tempo real!');
    } catch (err) {
      console.error('❌ [STT ERROR] Erro ao acessar microfone:', err);
    }
  }, []);

  const stopRecording = useCallback(() => {
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    setIsRecording(false);
    setVolumeLevel(0);
    console.log('🛑 [STT DEBUG] Captação de microfone encerrada.');
  }, []);

  return {
    isRecording,
    volumeLevel,
    startRecording,
    stopRecording
  };
};
