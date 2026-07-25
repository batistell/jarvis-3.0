import React from 'react';
import { Mic, RefreshCw } from 'lucide-react';
import { AudioInputDevice } from '../hooks/useVoiceRecorder';

interface MicrophoneSelectorProps {
  audioDevices: AudioInputDevice[];
  selectedDeviceId: string;
  onSelectDevice: (deviceId: string) => void;
  onRefreshDevices: () => void;
}

export const MicrophoneSelector: React.FC<MicrophoneSelectorProps> = ({
  audioDevices,
  selectedDeviceId,
  onSelectDevice,
  onRefreshDevices
}) => {
  return (
    <div className="flex items-center gap-2 font-mono text-xs px-3 py-1.5 rounded-md bg-slate-900/80 border border-cyan-500/30 shadow-[0_0_10px_rgba(0,240,255,0.1)] hover:border-cyan-500/60 transition-all">
      <Mic className="w-4 h-4 text-cyan-400 shrink-0 animate-pulse" />
      <span className="text-gray-400 shrink-0 hidden sm:inline">MIC:</span>
      {audioDevices.length > 0 ? (
        <select
          value={selectedDeviceId}
          onChange={(e) => onSelectDevice(e.target.value)}
          className="bg-transparent text-cyan-300 outline-none cursor-pointer text-xs pr-1 font-semibold max-w-[160px] md:max-w-[240px] truncate"
        >
          {audioDevices.map((dev) => (
            <option key={dev.deviceId} value={dev.deviceId} className="bg-slate-900 text-cyan-300">
              {dev.label}
            </option>
          ))}
        </select>
      ) : (
        <span className="text-amber-400 text-xs truncate">Detectando microfones...</span>
      )}
      <button
        onClick={onRefreshDevices}
        className="text-gray-400 hover:text-cyan-400 transition-colors p-0.5 ml-1"
        title="Atualizar lista de microfones"
      >
        <RefreshCw className="w-3.5 h-3.5" />
      </button>
    </div>
  );
};
