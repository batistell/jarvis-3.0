import React, { useState } from 'react';
import { Send, Mic, MicOff } from 'lucide-react';

interface MessageInputProps {
  onSendMessage: (text: string) => void;
  isRecording: boolean;
  onToggleRecord: () => void;
  disabled?: boolean;
}

export const MessageInput: React.FC<MessageInputProps> = ({
  onSendMessage,
  isRecording,
  onToggleRecord,
  disabled
}) => {
  const [text, setText] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim() || disabled) return;
    onSendMessage(text.trim());
    setText('');
  };

  return (
    <form onSubmit={handleSubmit} className="hud-card p-2 flex items-center gap-2">
      <button
        type="button"
        onClick={onToggleRecord}
        className={`p-3 rounded-xl border transition-all ${
          isRecording
            ? 'bg-emerald-950/80 border-green-500/60 text-green-400 glow-green'
            : 'bg-slate-900/80 border-cyan-500/30 text-gray-400 hover:text-cyan-400 hover:border-cyan-500/60'
        }`}
        title={isRecording ? 'Mutar Microfone' : 'Ativar Captura Contínua'}
      >
        {isRecording ? <Mic className="w-5 h-5" /> : <MicOff className="w-5 h-5" />}
      </button>

      <input
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Digite um comando para o Jarvis..."
        disabled={disabled}
        className="flex-1 bg-slate-950/80 border border-cyan-500/20 rounded-xl px-4 py-3 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-cyan-500/60 font-sans transition-colors"
      />

      <button
        type="submit"
        disabled={!text.trim() || disabled}
        className="p-3 bg-cyan-950/80 hover:bg-cyan-900/80 border border-cyan-500/50 rounded-xl text-cyan-400 disabled:opacity-40 disabled:cursor-not-allowed transition-all hover:shadow-[0_0_15px_rgba(0,240,255,0.4)]"
      >
        <Send className="w-5 h-5" />
      </button>
    </form>
  );
};
