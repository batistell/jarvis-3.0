# Jarvis 3.0 — Módulo LLM (Large Language Model)

## Motor Padrão: Qwen 2.5 3B Instruct (Nativo CTranslate2)

### Arquivo
`backend/llm/engines/native_qwen_engine.py`

### Modelo Usado
`jncraton/Qwen2.5-3B-Instruct-ct2-int8` — HuggingFace (baixado na primeira execução)

### Por que CTranslate2 e não Ollama?

- **Sem servidor separado**: o modelo roda no mesmo processo Python do FastAPI
- **Menor latência** de inicialização (sem handshake HTTP)
- **Controle total** de parâmetros de geração (beam_size, temperature, etc.)
- **Integração nativa** com `asyncio.to_thread` para não bloquear o event loop

### Configuração de Carga

```python
ctranslate2.Generator(
    model_dir,
    device="cuda",
    compute_type="int8_float16",  # Pesos INT8 + acumuladores FP16 → ~1.9GB VRAM
    inter_threads=1,              # 1 stream CUDA (sem duplicação de contexto)
    intra_threads=4,              # 4 threads internas por operação
    max_queued_batches=1          # Sem acumulação de batches em memória
)
```

### Instruções de Idioma Dinâmico

O idioma detectado pelo Whisper é injetado no system prompt de cada turno:

```python
lang_prompt = (
    f"{base_system_prompt}\n\n"
    f"Instrução Estrita de Idioma: O usuário falou no idioma '{detected_lang.upper()}'.\n"
    f"Você DEVE responder obrigatoriamente no idioma '{detected_lang.upper()}'.\n"
    f"NÃO use nenhum outro idioma — nem misture idiomas na resposta."
)
```

Isso garante que ao falar em PT o Jarvis responde em PT, e ao falar em EN responde em EN.

### System Prompt Padrão

```
Você é o Jarvis 3.0, um assistente pessoal conciso, fluente e multilíngue.
RESPONDA SEMPRE NO MESMO IDIOMA EM QUE O USUÁRIO FALOU OU ESCREVEU
(Português, Inglês, Espanhol, Francês, etc.).
Mantenha as respostas diretas e curtas para serem lidas em voz alta pelo sistema TTS.
```

### Parâmetros de Geração

```python
results = generator.generate_batch(
    [tokens],
    max_length=512,
    beam_size=1,
    sampling_temperature=0.7,
    repetition_penalty=1.1,
    end_token=eos_token_ids
)
```

---

## Interface Abstrata

```python
class BaseLLMEngine(ABC):
    async def ensure_model_loaded(self) -> bool: ...
    async def generate(self, prompt: str, system_prompt: str | None, history: list | None) -> str: ...
    async def generate_stream(self, prompt: str, system_prompt: str | None, history: list | None) -> AsyncGenerator[str, None]: ...
```
