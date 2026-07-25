import React, { useRef, useEffect } from 'react';
import { Message } from '../types';
import { Bot, User, Wrench, CheckCircle2, AlertTriangle } from 'lucide-react';

interface ChatWindowProps {
  messages: Message[];
  isGenerating: boolean;
}

export const ChatWindow: React.FC<ChatWindowProps> = ({ messages, isGenerating }) => {
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isGenerating]);

  return (
    <div className="hud-card p-4 flex-1 flex flex-col min-h-[360px] max-h-[500px] mb-4">
      <div className="corner-accent-tl"></div>
      <div className="corner-accent-tr"></div>

      {/* Timeline Header */}
      <div className="flex items-center justify-between pb-3 mb-3 border-b border-cyan-500/20">
        <span className="font-orbitron text-xs font-semibold text-cyan-400 tracking-wider flex items-center gap-2">
          <Bot className="w-4 h-4 text-cyan-400" />
          HISTÓRICO DA CONVERSA DE VOZ / TEXTO
        </span>
        <span className="font-mono text-[10px] text-gray-500">CANAL SECURE WS PCM</span>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto space-y-4 pr-2">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 text-gray-500 font-rajdhani">
            <Bot className="w-12 h-12 text-cyan-500/20 mb-2" />
            <p className="text-sm font-semibold text-gray-400">JARVIS 3.0 Pronto para Interação</p>
            <p className="text-xs text-gray-600 mt-1">
              Fale no microfone ou digite um comando abaixo.
            </p>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {msg.role !== 'user' && (
                <div className="w-8 h-8 rounded-lg bg-cyan-950/80 border border-cyan-500/40 flex items-center justify-center shrink-0">
                  <Bot className="w-4 h-4 text-cyan-400" />
                </div>
              )}

              <div
                className={`max-w-[80%] rounded-xl p-3.5 text-sm ${
                  msg.role === 'user'
                    ? 'bg-cyan-950/40 border border-cyan-500/40 text-cyan-100 rounded-tr-none'
                    : 'bg-slate-900/90 border border-slate-800 text-gray-200 rounded-tl-none shadow-lg'
                }`}
              >
                {/* Header info */}
                <div className="flex items-center justify-between gap-2 mb-1.5 font-mono text-[10px] text-gray-400">
                  <span className="font-semibold uppercase tracking-wider text-cyan-400">
                    {msg.role === 'user' ? 'VOCÊ' : 'JARVIS 3.0'}
                  </span>
                  <span>{msg.timestamp}</span>
                </div>

                {/* Message Content */}
                <div className="leading-relaxed whitespace-pre-wrap font-sans text-gray-200">
                  {msg.content || (msg.role === 'assistant' && isGenerating ? '...' : '')}
                </div>

                {/* Home Assistant Tool Execution Badge */}
                {msg.toolCall && (
                  <div className="mt-3 p-2 rounded-lg bg-cyan-950/60 border border-cyan-500/30 font-mono text-xs flex items-center gap-2">
                    <Wrench className="w-3.5 h-3.5 text-amber-400 animate-spin" />
                    <span className="text-amber-300">HA TOOL:</span>
                    <span className="text-gray-300">{msg.toolCall.name}({msg.toolCall.entityId})</span>
                    {msg.toolCall.status === 'success' ? (
                      <CheckCircle2 className="w-3.5 h-3.5 text-green-400 ml-auto" />
                    ) : (
                      <AlertTriangle className="w-3.5 h-3.5 text-rose-400 ml-auto" />
                    )}
                  </div>
                )}
              </div>

              {msg.role === 'user' && (
                <div className="w-8 h-8 rounded-lg bg-slate-900 border border-slate-700 flex items-center justify-center shrink-0">
                  <User className="w-4 h-4 text-gray-300" />
                </div>
              )}
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
};
