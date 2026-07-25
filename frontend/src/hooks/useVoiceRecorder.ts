import { useState, useRef, useCallback, useEffect } from 'react';
import { jarvisSocket } from '../services/websocket';

export interface AudioInputDevice {
  deviceId: string;
  label: string;
}

export const useVoiceRecorder = () => {
  const [isRecording, setIsRecording] = useState(false);
  const [volumeLevel, setVolumeLevel] = useState<number>(0);
  const [audioDevices, setAudioDevices] = useState<AudioInputDevice[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>('');

  const audioContextRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);

  // Enumera os microfones físicos/virtuais disponíveis no sistema do navegador
  const refreshDevices = useCallback(async () => {
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
        return;
      }
      const devices = await navigator.mediaDevices.enumerateDevices();
      const audioInputs = devices
        .filter((d) => d.kind === 'audioinput')
        .map((d, index) => ({
          deviceId: d.deviceId,
          label: d.label || `Microfone ${index + 1}`
        }));

      setAudioDevices(audioInputs);
      
      // Seleção inteligente: Prioriza Headsets / Fones e ignora Webcams na inicialização
      if (audioInputs.length > 0 && !selectedDeviceId) {
        let bestDevice = audioInputs.find((d) => {
          const label = d.label.toLowerCase();
          const isHeadset = /headset|headphone|fone|handset|hands-free|bluetooth|comunica[çc]ões|communications|usb audio|fifine|hyperx|logitech|razer|corsair|redragon/i.test(label);
          const isWebcam = /webcam|cam|câmera|camera|integrated|integrado/i.test(label);
          return isHeadset && !isWebcam;
        });

        if (!bestDevice) {
          bestDevice = audioInputs.find((d) => {
            const label = d.label.toLowerCase();
            return !/webcam|cam|câmera|camera|integrated|integrado/i.test(label);
          });
        }

        const chosen = bestDevice || audioInputs[0];
        if (chosen) {
          console.log(`🎤 [AUDIO SELECTION] Microfone auto-selecionado: "${chosen.label}" (${chosen.deviceId})`);
          setSelectedDeviceId(chosen.deviceId);
        }
      }

    } catch (err) {
      console.warn('⚠️ Não foi possível enumerar os microfones:', err);
    }
  }, [selectedDeviceId]);

  useEffect(() => {
    refreshDevices();
  }, [refreshDevices]);

  const startRecording = useCallback(async (overrideDeviceId?: string) => {
    try {
      console.log('🎙️ [STT DEBUG] Solicitando permissão do microfone...');
      jarvisSocket.connect('dev-jwt-token');

      const targetDeviceId = overrideDeviceId || selectedDeviceId;
      const audioConstraints: any = {
        channelCount: 1,
        sampleRate: 16000,
        echoCancellation: true,
        noiseSuppression: true
      };

      if (targetDeviceId) {
        audioConstraints.deviceId = { exact: targetDeviceId };
      }

      let stream: MediaStream;
      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: audioConstraints });
      } catch (err) {
        // Fallback para microfone padrão se o ID exato falhar
        console.warn('⚠️ Falha ao abrir microfone exato, usando padrão:', err);
        stream = await navigator.mediaDevices.getUserMedia({
          audio: { channelCount: 1, sampleRate: 16000, echoCancellation: true, noiseSuppression: true }
        });
      }

      streamRef.current = stream;
      refreshDevices();

      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      const audioContext = new AudioCtx({ sampleRate: 16000 });
      
      if (audioContext.state === 'suspended') {
        await audioContext.resume();
      }

      audioContextRef.current = audioContext;

      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);
        const pcmData = new Int16Array(inputData.length);
        let sumSquares = 0;

        for (let i = 0; i < inputData.length; i++) {
          const s = Math.max(-1, Math.min(1, inputData[i]));
          pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
          sumSquares += s * s;
        }

        jarvisSocket.sendBinary(pcmData.buffer);

        const rms = Math.sqrt(sumSquares / inputData.length);
        setVolumeLevel(Math.min(1, rms * 5));
      };

      source.connect(processor);

      const silenceGain = audioContext.createGain();
      silenceGain.gain.value = 0;
      processor.connect(silenceGain);
      silenceGain.connect(audioContext.destination);

      setIsRecording(true);
      console.log('✅ [STT DEBUG] Captação de microfone ativada e transmitindo em tempo real!');
    } catch (err) {
      console.error('❌ [STT ERROR] Erro ao acessar o microfone selecionado:', err);
    }
  }, [selectedDeviceId, refreshDevices]);

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

  const changeMicrophone = useCallback(async (newDeviceId: string) => {
    setSelectedDeviceId(newDeviceId);
    if (isRecording) {
      stopRecording();
      await startRecording(newDeviceId);
    }
  }, [isRecording, stopRecording, startRecording]);

  return {
    isRecording,
    volumeLevel,
    audioDevices,
    selectedDeviceId,
    setSelectedDeviceId: changeMicrophone,
    refreshDevices,
    startRecording,
    stopRecording
  };
};
