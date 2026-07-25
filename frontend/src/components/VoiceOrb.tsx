import React from 'react';
import { VoiceState } from '../types';
import { Mic, MicOff, Volume2, Sparkles } from 'lucide-react';

interface VoiceOrbProps {
  voiceState: VoiceState;
  volumeLevel: number; // 0 a 1
  isRecording: boolean;
  onToggleRecord: () => void;
}

export const VoiceOrb: React.FC<VoiceOrbProps> = ({
  voiceState,
  volumeLevel,
  isRecording,
  onToggleRecord
}) => {
  // Ajuste do diâmetro dinâmico da orbe com base no volume
  const orbScale = 1 + volumeLevel * 0.45;
  const glowOpacity = Math.min(1, 0.4 + volumeLevel * 0.6);

  return (
    <div className="hud-card p-6 mb-6 flex flex-col items-center justify-center min-h-[220px] relative">
      <div className="corner-accent-bl"></div>
      <div className="corner-accent-br"></div>

      {/* Orbe Holográfica Central */}
      <div className="relative flex items-center justify-center w-40 h-40 mb-4 cursor-pointer" onClick={onToggleRecord}>
        {/* Outer Pulsing Rings */}
        <div
          className="absolute inset-0 rounded-full border border-cyan-500/30 transition-all duration-150"
          style={{
            transform: `scale(${orbScale * 1.25})`,
            borderColor: voiceState === 'listening' ? 'rgba(57, 255, 20, 0.5)' : 'rgba(0, 240, 255, 0.3)'
          }}
        />
        <div
          className="absolute inset-0 rounded-full border border-cyan-400/20 transition-all duration-300 animate-spin"
          style={{ animationDuration: '12s' }}
        />

        {/* Central Glowing Sphere */}
        <div
          className={`w-28 h-28 rounded-full flex items-center justify-center transition-all duration-200 shadow-2xl relative ${
            voiceState === 'listening'
              ? 'bg-gradient-to-tr from-emerald-950 via-green-900 to-emerald-500 glow-green'
              : voiceState === 'speaking' || voiceState === 'thinking'
              ? 'bg-gradient-to-tr from-cyan-950 via-cyan-800 to-cyan-400 glow-cyan'
              : 'bg-gradient-to-tr from-slate-950 via-slate-900 to-cyan-950/60'
          }`}
          style={{
            transform: `scale(${orbScale})`,
            boxShadow:
              voiceState === 'listening'
                ? `0 0 ${30 + volumeLevel * 40}px rgba(57, 255, 20, ${glowOpacity})`
                : `0 0 ${30 + volumeLevel * 40}px rgba(0, 240, 255, ${glowOpacity})`
          }}
        >
          {voiceState === 'listening' ? (
            <Mic className="w-10 h-10 text-green-400 animate-bounce" />
          ) : voiceState === 'speaking' ? (
            <Volume2 className="w-10 h-10 text-cyan-300 animate-pulse" />
          ) : voiceState === 'thinking' || voiceState === 'transcribing' ? (
            <Sparkles className="w-10 h-10 text-amber-400 animate-spin" />
          ) : isRecording ? (
            <Mic className="w-10 h-10 text-cyan-400" />
          ) : (
            <MicOff className="w-10 h-10 text-gray-500" />
          )}
        </div>
      </div>

      {/* State Caption & Mic Toggle Button */}
      <div className="flex items-center gap-4">
        <button
          onClick={onToggleRecord}
          className={`px-4 py-2 rounded-lg font-orbitron text-xs font-bold tracking-wider transition-all flex items-center gap-2 border ${
            isRecording
              ? 'bg-emerald-950/80 border-green-500/60 text-green-400 hover:bg-emerald-900/80 shadow-[0_0_15px_rgba(57,255,20,0.3)]'
              : 'bg-cyan-950/40 border-cyan-500/40 text-cyan-400 hover:bg-cyan-900/50'
          }`}
        >
          {isRecording ? <Mic className="w-4 h-4" /> : <MicOff className="w-4 h-4" />}
          <span>{isRecording ? 'ALWAYS-LISTENING ATIVO' : 'ATIVAR MICROFONE'}</span>
        </button>
      </div>
    </div>
  );
};
