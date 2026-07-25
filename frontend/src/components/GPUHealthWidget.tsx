import React, { useState, useEffect } from 'react';
import { Cpu, Thermometer, RefreshCw, AlertTriangle, CheckCircle } from 'lucide-react';

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

export const GPUHealthWidget: React.FC = () => {
  const [gpuData, setGpuData] = useState<GPUHealthData | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchHealth = async () => {
    try {
      setLoading(true);
      const res = await fetch('http://localhost:8000/api/health');
      if (res.ok) {
        const data = await res.json();
        setGpuData(data.gpu);
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
        const data = await res.json();
        setGpuData(data);
      }
    } catch (err) {
      console.warn('Erro ao disparar GC:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 10000); // Atualiza estatísticas a cada 10s
    return () => clearInterval(interval);
  }, []);

  if (!gpuData) return null;

  const isCritical = gpuData.vram_used_percent >= 90;

  return (
    <div className="hud-card p-4 mt-4">
      <div className="flex items-center justify-between pb-2 border-b border-cyan-500/20 mb-3">
        <div className="flex items-center gap-2 font-orbitron text-xs font-semibold text-cyan-400">
          <Cpu className="w-4 h-4 text-cyan-400" />
          <span>MONITORAMENTO DE SAÚDE DA GPU & MODELOS</span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={triggerGc}
            disabled={loading}
            className="flex items-center gap-1.5 text-[11px] font-mono px-2.5 py-1 rounded bg-cyan-950/60 hover:bg-cyan-900/60 border border-cyan-500/40 text-cyan-300 transition-all hover:shadow-[0_0_10px_rgba(0,240,255,0.3)] disabled:opacity-50"
            title="Limpar memória RAM/VRAM não utilizada"
          >
            <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
            <span>LIMPAR VRAM</span>
          </button>
        </div>
      </div>

      {gpuData.warning && (
        <div className="flex items-center gap-2 p-2 mb-3 rounded bg-amber-950/50 border border-amber-500/40 text-amber-300 text-xs font-mono">
          <AlertTriangle className="w-4 h-4 shrink-0 text-amber-400" />
          <span>{gpuData.warning}</span>
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 font-mono text-xs">
        {/* Placa de Vídeo */}
        <div className="p-2.5 rounded-lg bg-slate-900/80 border border-cyan-500/20">
          <div className="text-gray-400 text-[10px]">GPU HARDWARE</div>
          <div className="text-cyan-300 font-bold text-xs truncate mt-0.5">{gpuData.gpu_name}</div>
          <div className="text-[10px] text-gray-500 mt-1">Driver {gpuData.driver_version}</div>
        </div>

        {/* Uso de VRAM */}
        <div className="p-2.5 rounded-lg bg-slate-900/80 border border-cyan-500/20">
          <div className="flex justify-between text-[10px]">
            <span className="text-gray-400">VRAM GPU</span>
            <span className={isCritical ? 'text-rose-400 font-bold' : 'text-cyan-400'}>
              {gpuData.vram_used_percent}%
            </span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-2 mt-1.5 overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${
                isCritical ? 'bg-rose-500' : gpuData.vram_used_percent > 75 ? 'bg-amber-400' : 'bg-cyan-400'
              }`}
              style={{ width: `${gpuData.vram_used_percent}%` }}
            ></div>
          </div>
          <div className="text-[10px] text-gray-400 mt-1">
            {(gpuData.vram_used_mb / 1024).toFixed(1)}GB / {(gpuData.vram_total_mb / 1024).toFixed(1)}GB
          </div>
        </div>

        {/* Carga da GPU */}
        <div className="p-2.5 rounded-lg bg-slate-900/80 border border-cyan-500/20">
          <div className="text-gray-400 text-[10px]">CARGA GPU</div>
          <div className="text-cyan-300 font-bold text-sm mt-0.5">{gpuData.gpu_utilization_percent}%</div>
          <div className="text-[10px] text-gray-500 mt-1">Uso de Cores CUDA</div>
        </div>

        {/* Temperatura */}
        <div className="p-2.5 rounded-lg bg-slate-900/80 border border-cyan-500/20">
          <div className="flex items-center gap-1 text-gray-400 text-[10px]">
            <Thermometer className="w-3 h-3 text-cyan-400" />
            <span>TEMPERATURA</span>
          </div>
          <div className="text-cyan-300 font-bold text-sm mt-0.5">{gpuData.temperature_c} °C</div>
          <div className="text-[10px] text-emerald-400 mt-1 flex items-center gap-1">
            <CheckCircle className="w-3 h-3" />
            <span>Status Normal</span>
          </div>
        </div>
      </div>
    </div>
  );
};
