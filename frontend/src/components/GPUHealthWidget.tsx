import React, { useState, useEffect } from 'react';
import { Cpu, Thermometer, RefreshCw, AlertTriangle, CheckCircle, Mic, MessageSquare, Volume2 } from 'lucide-react';

export interface GPUHealthData {
  gpu_name: string;
  driver_version: string;
  vram_total_mb: number;
  vram_used_mb: number;
  vram_free_mb: number;
  vram_used_percent: number;
  gpu_utilization_percent: number;
  temperature_c: number;
  status: string;
  warning?: string | null;
}

export interface ModelMetrics {
  stt: {
    engine: string;
    model_name: string;
    device: string;
    compute_type: string;
    is_loaded: boolean;
    latency_ms: number;
  };
  llm: {
    engine: string;
    model_name: string;
    is_loaded: boolean;
    latency_ms: number;
  };
  tts: {
    engine: string;
    voice: string;
    latency_ms: number;
  };
}

export interface FullHealthData {
  timestamp: number;
  gpu: GPUHealthData;
  models: ModelMetrics;
}

export const GPUHealthWidget: React.FC = () => {
  const [healthData, setHealthData] = useState<FullHealthData | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchHealth = async () => {
    try {
      setLoading(true);
      const res = await fetch('http://localhost:8000/api/health');
      if (res.ok) {
        const data: FullHealthData = await res.json();
        setHealthData(data);
      }
    } catch (err) {
      console.warn('Não foi possível obter health check da GPU:', err);
    } finally {
      setLoading(false);
    }
  };

  const triggerGc = async () => {
    try {
      setLoading(true);
      const res = await fetch('http://localhost:8000/api/health/gc', { method: 'POST' });
      if (res.ok) {
        await fetchHealth();
      }
    } catch (err) {
      console.warn('Erro ao disparar GC:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 5000); // Atualiza estatísticas a cada 5s
    return () => clearInterval(interval);
  }, []);

  if (!healthData) return null;

  const { gpu, models } = healthData;
  const isCriticalVram = gpu.vram_used_percent >= 90;

  return (
    <div className="hud-card p-4 mt-4">
      {/* Header do Widget */}
      <div className="flex items-center justify-between pb-2 border-b border-cyan-500/20 mb-3">
        <div className="flex items-center gap-2 font-orbitron text-xs font-semibold text-cyan-400">
          <Cpu className="w-4 h-4 text-cyan-400" />
          <span>DIAGNÓSTICO DE PERFORMANCE DA GPU & MODELOS DE IA</span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={triggerGc}
            disabled={loading}
            className="flex items-center gap-1.5 text-[11px] font-mono px-2.5 py-1 rounded bg-cyan-950/60 hover:bg-cyan-900/60 border border-cyan-500/40 text-cyan-300 transition-all hover:shadow-[0_0_10px_rgba(0,240,255,0.3)] disabled:opacity-50"
            title="Forçar limpeza de memória VRAM e coleta de lixo"
          >
            <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
            <span>LIMPAR VRAM</span>
          </button>
        </div>
      </div>

      {/* Alertas de VRAM Crítica / Temperatura */}
      {gpu.warning && (
        <div className="flex items-center gap-2 p-2.5 mb-3 rounded-lg bg-rose-950/60 border border-rose-500/50 text-rose-300 text-xs font-mono animate-pulse">
          <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
          <span>{gpu.warning}</span>
        </div>
      )}

      {/* Grid de Métricas da GPU */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 font-mono text-xs mb-4">
        {/* Hardware GPU */}
        <div className="p-2.5 rounded-lg bg-slate-900/80 border border-cyan-500/20">
          <div className="text-gray-400 text-[10px]">GPU HARDWARE</div>
          <div className="text-cyan-300 font-bold text-xs truncate mt-0.5">{gpu.gpu_name}</div>
          <div className="text-[10px] text-gray-500 mt-1">Driver {gpu.driver_version}</div>
        </div>

        {/* Uso de VRAM */}
        <div className="p-2.5 rounded-lg bg-slate-900/80 border border-cyan-500/20">
          <div className="flex justify-between text-[10px]">
            <span className="text-gray-400">VRAM GPU</span>
            <span className={isCriticalVram ? 'text-rose-400 font-bold' : 'text-cyan-400'}>
              {gpu.vram_used_percent}%
            </span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-2 mt-1.5 overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${
                isCriticalVram ? 'bg-rose-500' : gpu.vram_used_percent > 75 ? 'bg-amber-400' : 'bg-cyan-400'
              }`}
              style={{ width: `${gpu.vram_used_percent}%` }}
            ></div>
          </div>
          <div className="text-[10px] text-gray-400 mt-1">
            {(gpu.vram_used_mb / 1024).toFixed(1)}GB / {(gpu.vram_total_mb / 1024).toFixed(1)}GB
          </div>
        </div>

        {/* Uso de CUDA */}
        <div className="p-2.5 rounded-lg bg-slate-900/80 border border-cyan-500/20">
          <div className="text-gray-400 text-[10px]">CARGA CUDA GPU</div>
          <div className="text-cyan-300 font-bold text-sm mt-0.5">{gpu.gpu_utilization_percent}%</div>
          <div className="text-[10px] text-gray-500 mt-1">Processamento</div>
        </div>

        {/* Temperatura */}
        <div className="p-2.5 rounded-lg bg-slate-900/80 border border-cyan-500/20">
          <div className="flex items-center gap-1 text-gray-400 text-[10px]">
            <Thermometer className="w-3 h-3 text-cyan-400" />
            <span>TEMPERATURA</span>
          </div>
          <div className="text-cyan-300 font-bold text-sm mt-0.5">{gpu.temperature_c} °C</div>
          <div className="text-[10px] text-emerald-400 mt-1 flex items-center gap-1">
            <CheckCircle className="w-3 h-3" />
            <span>{gpu.status}</span>
          </div>
        </div>
      </div>

      {/* Grid de Latência e Saúde dos Modelos de IA */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 font-mono text-xs">
        {/* STT (Whisper Large-v3) */}
        <div className="p-3 rounded-lg bg-slate-900/90 border border-cyan-500/30">
          <div className="flex items-center justify-between text-cyan-400 font-bold mb-1">
            <div className="flex items-center gap-1.5">
              <Mic className="w-4 h-4 text-cyan-400" />
              <span>STT (WHISPER)</span>
            </div>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-cyan-950 border border-cyan-500/40 text-cyan-300">
              {models.stt.model_name}
            </span>
          </div>
          <div className="text-gray-400 text-[11px] mt-2">
            Latência do Reconhecimento:
          </div>
          <div className="flex items-center justify-between mt-1">
            <span className="text-sm font-bold text-cyan-300">
              {models.stt.latency_ms > 0 ? `${models.stt.latency_ms} ms` : 'Aguardando fala...'}
            </span>
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
              models.stt.latency_ms > 0 && models.stt.latency_ms < 600
                ? 'bg-emerald-950 text-emerald-400 border border-emerald-500/40'
                : models.stt.latency_ms >= 600
                ? 'bg-amber-950 text-amber-400 border border-amber-500/40'
                : 'bg-slate-800 text-gray-400'
            }`}>
              {models.stt.latency_ms > 0 && models.stt.latency_ms < 600 ? '⚡ RÁPIDO' : models.stt.latency_ms >= 600 ? '⚠️ LENTO' : 'IDLE'}
            </span>
          </div>
          <div className="text-[10px] text-gray-500 mt-2">Dispositivo: {models.stt.device.toUpperCase()} ({models.stt.compute_type})</div>
        </div>

        {/* LLM (Qwen 2.5 3B) */}
        <div className="p-3 rounded-lg bg-slate-900/90 border border-cyan-500/30">
          <div className="flex items-center justify-between text-cyan-400 font-bold mb-1">
            <div className="flex items-center gap-1.5">
              <MessageSquare className="w-4 h-4 text-cyan-400" />
              <span>LLM (QWEN 2.5)</span>
            </div>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-cyan-950 border border-cyan-500/40 text-cyan-300">
              CTranslate2
            </span>
          </div>
          <div className="text-gray-400 text-[11px] mt-2">
            Tempo de Resposta do Modelo:
          </div>
          <div className="flex items-center justify-between mt-1">
            <span className="text-sm font-bold text-cyan-300">
              {models.llm.latency_ms > 0 ? `${models.llm.latency_ms} ms` : 'Aguardando prompt...'}
            </span>
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
              models.llm.latency_ms > 0 && models.llm.latency_ms < 1500
                ? 'bg-emerald-950 text-emerald-400 border border-emerald-500/40'
                : models.llm.latency_ms >= 1500
                ? 'bg-amber-950 text-amber-400 border border-amber-500/40'
                : 'bg-slate-800 text-gray-400'
            }`}>
              {models.llm.latency_ms > 0 && models.llm.latency_ms < 1500 ? '⚡ RÁPIDO' : models.llm.latency_ms >= 1500 ? '⚠️ LENTO' : 'IDLE'}
            </span>
          </div>
          <div className="text-[10px] text-gray-500 mt-2">Engine: {models.llm.engine.toUpperCase()} (GPU CUDA)</div>
        </div>

        {/* TTS (Edge-TTS) */}
        <div className="p-3 rounded-lg bg-slate-900/90 border border-cyan-500/30">
          <div className="flex items-center justify-between text-cyan-400 font-bold mb-1">
            <div className="flex items-center gap-1.5">
              <Volume2 className="w-4 h-4 text-cyan-400" />
              <span>TTS (VOZ NEURAL)</span>
            </div>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-cyan-950 border border-cyan-500/40 text-cyan-300">
              Remy
            </span>
          </div>
          <div className="text-gray-400 text-[11px] mt-2">
            Tempo de Síntese de Voz:
          </div>
          <div className="flex items-center justify-between mt-1">
            <span className="text-sm font-bold text-cyan-300">
              {models.tts.latency_ms > 0 ? `${models.tts.latency_ms} ms` : 'Aguardando síntese...'}
            </span>
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
              models.tts.latency_ms > 0 && models.tts.latency_ms < 500
                ? 'bg-emerald-950 text-emerald-400 border border-emerald-500/40'
                : models.tts.latency_ms >= 500
                ? 'bg-amber-950 text-amber-400 border border-amber-500/40'
                : 'bg-slate-800 text-gray-400'
            }`}>
              {models.tts.latency_ms > 0 && models.tts.latency_ms < 500 ? '⚡ RÁPIDO' : models.tts.latency_ms >= 500 ? '⚠️ LENTO' : 'IDLE'}
            </span>
          </div>
          <div className="text-[10px] text-gray-500 mt-2">Voz: {models.tts.voice}</div>
        </div>
      </div>
    </div>
  );
};
