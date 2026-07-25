import React from 'react';
import { Lightbulb, Power, ShieldAlert, Cpu, Terminal } from 'lucide-react';

interface ControlPanelProps {
  onQuickAction: (command: string) => void;
}

export const ControlPanel: React.FC<ControlPanelProps> = ({ onQuickAction }) => {
  const quickCommands = [
    { label: '💡 Ligue a Luz', command: 'Ligue a luz do quarto', icon: Lightbulb },
    { label: '🌙 Mudar para Modo Noturno', command: 'Ativar modo noturno nas luzes', icon: Power },
    { label: '🛡️ Status de Segurança', command: 'Verificar status dos sensores de segurança', icon: ShieldAlert },
    { label: '📊 Status do Servidor', command: 'Qual o uso de CPU e memória do servidor?', icon: Cpu }
  ];

  return (
    <div className="hud-card p-4 mt-6">
      <div className="flex items-center gap-2 mb-3 pb-2 border-b border-cyan-500/20 font-orbitron text-xs font-semibold text-cyan-400">
        <Terminal className="w-4 h-4 text-cyan-400" />
        <span>COMANDOS RÁPIDOS & CONTROLE RESIDENCIAL</span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {quickCommands.map((item, idx) => (
          <button
            key={idx}
            onClick={() => onQuickAction(item.command)}
            className="p-3 bg-slate-900/80 hover:bg-cyan-950/50 border border-cyan-500/20 hover:border-cyan-500/60 rounded-xl text-left transition-all hover:shadow-[0_0_10px_rgba(0,240,255,0.2)] group"
          >
            <div className="text-xs font-semibold text-cyan-300 group-hover:text-cyan-200 mb-1">
              {item.label}
            </div>
            <div className="text-[10px] font-mono text-gray-500 truncate">
              "{item.command}"
            </div>
          </button>
        ))}
      </div>
    </div>
  );
};
