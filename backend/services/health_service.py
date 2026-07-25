import subprocess
import gc
import time
import asyncio
from backend.config import settings

class GPUHealthService:
    """
    Serviço de Monitoramento de Saúde da GPU e dos Modelos de IA (STT, LLM, TTS).
    Mede uso de VRAM, temperatura da GPU, latência de inferência e detecta degradação de performance.
    """
    last_stt_latency_ms: float = 0.0
    last_llm_latency_ms: float = 0.0
    last_tts_latency_ms: float = 0.0

    @classmethod
    def record_stt_latency(cls, ms: float):
        cls.last_stt_latency_ms = round(ms, 1)

    @classmethod
    def record_llm_latency(cls, ms: float):
        cls.last_llm_latency_ms = round(ms, 1)

    @classmethod
    def record_tts_latency(cls, ms: float):
        cls.last_tts_latency_ms = round(ms, 1)

    @classmethod
    def get_gpu_metrics(cls) -> dict:
        """Coleta métricas em tempo real da placa de vídeo via nvidia-smi."""
        try:
            res = subprocess.run(
                [
                    'nvidia-smi',
                    '--query-gpu=name,driver_version,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu',
                    '--format=csv,noheader,nounits'
                ],
                capture_output=True,
                text=True,
                timeout=2
            )
            if res.returncode == 0 and res.stdout.strip():
                parts = [p.strip() for p in res.stdout.strip().split(',')]
                if len(parts) >= 7:
                    total_mb = float(parts[2])
                    used_mb = float(parts[3])
                    free_mb = float(parts[4])
                    gpu_util = float(parts[5])
                    temp_c = float(parts[6])
                    vram_percent = (used_mb / total_mb * 100.0) if total_mb > 0 else 0.0

                    status = "OPTIMAL"
                    warning = None
                    if vram_percent >= 90.0:
                        status = "CRITICAL_VRAM_FULL"
                        warning = "⚠️ VRAM da GPU 90%+ cheia! Risco de paginação em RAM e extrema lentidão."
                    elif temp_c >= 82.0:
                        status = "HIGH_TEMPERATURE"
                        warning = "⚠️ Temperatura elevada na GPU (Throttling térmico)."

                    return {
                        "gpu_name": parts[0],
                        "driver_version": parts[1],
                        "vram_total_mb": total_mb,
                        "vram_used_mb": used_mb,
                        "vram_free_mb": free_mb,
                        "vram_used_percent": round(vram_percent, 1),
                        "gpu_utilization_percent": gpu_util,
                        "temperature_c": temp_c,
                        "status": status,
                        "warning": warning
                    }
        except Exception as e:
            pass

        return {
            "gpu_name": "N/A",
            "driver_version": "N/A",
            "vram_total_mb": 0,
            "vram_used_mb": 0,
            "vram_free_mb": 0,
            "vram_used_percent": 0.0,
            "gpu_utilization_percent": 0.0,
            "temperature_c": 0.0,
            "status": "UNKNOWN",
            "warning": "Não foi possível coletar estatísticas da GPU."
        }

    @classmethod
    def release_memory(cls) -> dict:
        """Executa limpeza de memória e coleta de lixo no Python."""
        gc.collect()
        return cls.get_gpu_metrics()

    @classmethod
    async def get_full_health(cls) -> dict:
        """Retorna o raio-x completo do sistema, GPU e modelos de IA."""
        gpu_info = cls.get_gpu_metrics()

        from backend.services.stt_service import stt_service
        from backend.services.llm_service import llm_service
        from backend.services.tts_service import tts_service

        stt_loaded = hasattr(stt_service, "model") and stt_service.model is not None
        llm_loaded = hasattr(llm_service, "generator") and llm_service.generator is not None

        return {
            "timestamp": time.time(),
            "gpu": gpu_info,
            "models": {
                "stt": {
                    "engine": settings.STT_ENGINE,
                    "model_name": settings.WHISPER_MODEL,
                    "device": settings.WHISPER_DEVICE,
                    "compute_type": settings.WHISPER_COMPUTE_TYPE,
                    "is_loaded": stt_loaded,
                    "latency_ms": cls.last_stt_latency_ms
                },
                "llm": {
                    "engine": settings.LLM_ENGINE,
                    "model_name": settings.NATIVE_LLM_MODEL,
                    "is_loaded": llm_loaded,
                    "latency_ms": cls.last_llm_latency_ms
                },
                "tts": {
                    "engine": settings.TTS_ENGINE,
                    "voice": settings.TTS_VOICE,
                    "latency_ms": cls.last_tts_latency_ms
                }
            }
        }

health_service = GPUHealthService()
