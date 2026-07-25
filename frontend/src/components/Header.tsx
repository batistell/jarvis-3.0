import React from 'react';
import { ConnectionStatus, VoiceState, UserProfile } from '../types';
import { AudioInputDevice } from '../hooks/useVoiceRecorder';
import { MicrophoneSelector } from './MicrophoneSelector';
import { Cpu, Wifi, WifiOff, User as UserIcon, LogOut, ShieldCheck, Activity } from 'lucide-react';

interface HeaderProps {
  connectionStatus: ConnectionStatus;
  voiceState: VoiceState;
  user: UserProfile | null;
  audioDevices: AudioInputDevice[];
  selectedDeviceId: string;
  onSelectDevice: (deviceId: string) => void;
  onRefreshDevices: () => void;
  onOpenAuth: () => void;
  onLogout: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  connectionStatus,
  voiceState,
  user,
  audioDevices,
  selectedDeviceId,
  onSelectDevice,
  onRefreshDevices,
  onOpenAuth,
  onLogout
}) => {
  return (
    <header className="hud-card p-4 mb-6 flex flex-wrap items-center justify-between gap-4">
      <div className="corner-accent-tl"></div>
      <div className="corner-accent-tr"></div>

      {/* Brand Title */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-cyan-950/40 border border-cyan-500/30 flex items-center justify-center glow-cyan">
          <Cpu className="w-6 h-6 text-cyan-400" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-orbitron font-extrabold text-xl tracking-wider text-cyan-400">JARVIS 3.0</h1>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950/80 border border-cyan-500/40 text-cyan-300">
              PYTHON ENGINE
            </span>
          </div>
          <p className="text-xs font-rajdhani text-gray-400 tracking-wide">
            ALWAYS-LISTENING HYPER-INTELLIGENT ASSISTANT
          </p>
        </div>
      </div>

      {/* Status Bar Indicators */}
      <div className="flex flex-wrap items-center gap-3 sm:gap-4">
        {/* Microphone Selector */}
        <MicrophoneSelector
          audioDevices={audioDevices}
          selectedDeviceId={selectedDeviceId}
          onSelectDevice={onSelectDevice}
          onRefreshDevices={onRefreshDevices}
        />

        {/* Voice State Badge */}
        <div className="flex items-center gap-2 font-mono text-xs px-3 py-1.5 rounded-md bg-slate-900/80 border border-cyan-500/20">
          <Activity className={`w-4 h-4 ${voiceState !== 'idle' ? 'text-green-400 animate-pulse' : 'text-cyan-400'}`} />
          <span className="text-gray-400 hidden sm:inline">STATE:</span>
          <span className="text-cyan-300 uppercase tracking-wider font-semibold">{voiceState}</span>
        </div>

        {/* Connection Status Badge */}
        <div className="flex items-center gap-2 font-mono text-xs px-3 py-1.5 rounded-md bg-slate-900/80 border border-cyan-500/20">
          {connectionStatus === 'connected' ? (
            <>
              <Wifi className="w-4 h-4 text-green-400" />
              <span className="text-green-400 uppercase font-semibold tracking-wider">ONLINE</span>
            </>
          ) : connectionStatus === 'connecting' ? (
            <>
              <Wifi className="w-4 h-4 text-amber-400 animate-pulse" />
              <span className="text-amber-400 uppercase font-semibold">CONNECTING...</span>
            </>
          ) : (
            <>
              <WifiOff className="w-4 h-4 text-rose-500" />
              <span className="text-rose-500 uppercase font-semibold">OFFLINE</span>
            </>
          )}
        </div>

        {/* User Card */}
        {user ? (
          <div className="flex items-center gap-3 bg-slate-900/90 border border-cyan-500/30 px-3 py-1.5 rounded-lg">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-cyan-400" />
              <span className="text-xs font-mono text-gray-200">{user.email}</span>
            </div>
            <button
              onClick={onLogout}
              className="text-gray-400 hover:text-rose-400 transition-colors"
              title="Logout"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <button
            onClick={onOpenAuth}
            className="flex items-center gap-2 bg-cyan-950/60 hover:bg-cyan-900/60 border border-cyan-500/50 text-cyan-300 px-3 py-1.5 rounded-lg text-xs font-mono transition-all hover:shadow-[0_0_12px_rgba(0,240,255,0.4)]"
          >
            <UserIcon className="w-4 h-4" />
            <span>LOGIN GOOGLE</span>
          </button>
        )}
      </div>
    </header>
  );
};
