import React from 'react';
import { X, ShieldCheck, Lock } from 'lucide-react';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onLoginGoogle: () => void;
  onBypassDev: () => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({
  isOpen,
  onClose,
  onLoginGoogle,
  onBypassDev
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-4">
      <div className="hud-card p-6 max-w-md w-full relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-cyan-400 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-lg bg-cyan-950/80 border border-cyan-500/40 flex items-center justify-center glow-cyan">
            <Lock className="w-5 h-5 text-cyan-400" />
          </div>
          <div>
            <h2 className="font-orbitron font-bold text-lg text-cyan-400">AUTENTICAÇÃO LOCAL</h2>
            <p className="text-xs font-mono text-gray-400">FIREBASE OIDC & WHITELIST DE E-MAIL</p>
          </div>
        </div>

        <p className="text-xs text-gray-300 mb-6 leading-relaxed">
          O Jarvis 3.0 restringe o acesso às funções físicas e histórico de conversas aos e-mails autorizados (ex: <code className="text-cyan-300">batistell.labs@gmail.com</code>).
        </p>

        <div className="space-y-3">
          <button
            onClick={onLoginGoogle}
            className="w-full py-3 px-4 bg-cyan-950/80 hover:bg-cyan-900/80 border border-cyan-500/50 rounded-xl text-sm font-semibold text-cyan-300 flex items-center justify-center gap-2 transition-all hover:shadow-[0_0_15px_rgba(0,240,255,0.4)]"
          >
            <ShieldCheck className="w-5 h-5 text-cyan-400" />
            <span>ENTRAR COM CONTA GOOGLE (FIREBASE)</span>
          </button>

          <button
            onClick={onBypassDev}
            className="w-full py-2 px-4 bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded-xl text-xs font-mono text-gray-400 hover:text-gray-200 transition-colors"
          >
            MODO DESENVOLVIMENTO (DEV PREVIEW)
          </button>
        </div>
      </div>
    </div>
  );
};
