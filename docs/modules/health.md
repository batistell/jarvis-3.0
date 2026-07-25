# Jarvis 3.0 — Monitoramento de GPU e Saúde dos Modelos

## Arquivo
`backend/services/health_service.py`

## Endpoints

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/health` | Retorna estado completo de GPU e latências |
| `POST` | `/api/health/gc` | Força coleta de lixo Python + limpeza de VRAM CUDA |

## Resposta JSON do `GET /api/health`

```json
{
  "gpu": {
    "gpu_name": "NVIDIA GeForce RTX 3060",
    "driver_version": "591.86",
    "vram_total_mb": 12288,
    "vram_used_mb": 3464,
    "vram_free_mb": 8824,
    "vram_used_percent": 28.2,
    "gpu_utilization_percent": 8,
    "temperature_c": 48,
    "status": "OPTIMAL"
  },
  "models": {
    "stt": {
      "engine": "faster-whisper",
      "model_name": "large-v3-turbo",
      "device": "cuda",
      "compute_type": "int8_float16",
      "latency_ms": 485,
      "status": "ready"
    },
    "llm": {
      "engine": "qwen-native",
      "model_name": "jncraton/Qwen2.5-3B-Instruct-ct2-int8",
      "device": "cuda",
      "compute_type": "int8_float16",
      "latency_ms": 820,
      "status": "ready"
    },
    "tts": {
      "engine": "edge-tts",
      "voice": "fr-FR-RemyMultilingualNeural",
      "latency_ms": 220,
      "status": "ready"
    }
  },
  "timestamp": "2026-07-25T06:50:00Z"
}
```

## Status da GPU

| Status | Condição | Cor no HUD |
|---|---|---|
| `OPTIMAL` | VRAM < 60% | Verde |
| `NORMAL` | VRAM 60–80% | Amarelo |
| `HIGH` | VRAM 80–90% | Laranja |
| `CRITICAL` | VRAM > 90% | Vermelho |
| `UNAVAILABLE` | nvidia-smi não encontrado | Cinza |

## Como Funciona a Coleta de VRAM

```
POST /api/health/gc
    ↓
gc.collect()           # Python garbage collector
torch.cuda.empty_cache()  # (se torch disponível)
    ↓
nvidia-smi novamente → retorna VRAM atualizada
```

> **Nota**: O principal consumidor de VRAM no Windows não são os modelos de IA, mas sim os contextos gráficos WDDM de Chrome, Discord, Edge, IDE Electron, etc. O `gc` não libera essa memória — apenas a memória Python CUDA não referenciada.

## Widget no Frontend (`GPUHealthWidget.tsx`)

O widget consome `GET /api/health` a cada **5 segundos** e exibe:

- Barra de VRAM com gradiente de cor por criticidade
- % de utilização CUDA e temperatura
- Últimas latências STT / LLM / TTS em ms
- Botão **"LIMPAR VRAM"** → `POST /api/health/gc`
