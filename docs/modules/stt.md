# Jarvis 3.0 — Módulo STT (Speech-to-Text)

## Motor Padrão: Faster-Whisper Large-v3-Turbo

### Arquivo
`backend/stt/engines/faster_whisper_engine.py`

### Configuração

| Parâmetro | Valor padrão | Descrição |
|---|---|---|
| `WHISPER_MODEL` | `large-v3-turbo` | Modelo (~1.5GB VRAM, 8x mais rápido que large-v3) |
| `WHISPER_DEVICE` | `cuda` | Execução em GPU CUDA |
| `WHISPER_COMPUTE_TYPE` | `int8_float16` | Pesos INT8 + acumuladores FP16 (menor VRAM) |
| `WHISPER_INITIAL_PROMPT` | `None` | Desativado para evitar concatenação de texto em silêncio |

### Idiomas Suportados

O Whisper usa **two-pass** para restringir a detecção a **Português (pt)** e **Inglês (en)**:

1. **`model.detect_language(audio)`** → retorna dict com score de cada idioma
2. Se o idioma com maior score não for `pt` ou `en`, força o de maior score entre os dois
3. Transcreve com `language=forced_lang` para decodificação otimizada

```python
ALLOWED_LANGUAGES = {"pt", "en"}

lang, all_probs = self.model.detect_language(audio_float32)
if lang not in ALLOWED_LANGUAGES:
    pt_score = all_probs.get("pt", 0.0)
    en_score = all_probs.get("en", 0.0)
    forced_lang = "pt" if pt_score >= en_score else "en"
```

### Parâmetros de Transcrição

```python
segments, info = model.transcribe(
    audio_float32,
    beam_size=1,                          # Greedy decoding (mais rápido)
    vad_filter=True,                      # Remove silêncios internos
    condition_on_previous_text=False,     # Sem contaminação entre frases
    hallucination_silence_threshold=0.5,  # Descarta segmentos em silêncio
    no_speech_threshold=0.6,             # Threshold de detecção de fala
    language=forced_lang                  # PT ou EN (nunca None)
)
```

---

## Filtro de Alucinações e Ruído

### Arquivo
`backend/services/hallucination_filter.py`

### Pipeline de Limpeza

```
texto bruto do Whisper
    │
    ├── PHANTOM_EXACT: lookup O(1) em ~80 frases fantasma
    │   ("thank you", "ok", "bye", "i love you", "[inaudible]", ♪, etc.)
    │
    ├── PHANTOM_PATTERNS: regex patterns
    │   (legendas, subtitles, [colchetes], cirílico, YouTube phrases)
    │
    ├── _is_noise(): < 3 chars alfanuméricos reais, ou tokens de ruído puro
    │   (uh, um, hmm, ah, oh, apenas pontuação)
    │
    ├── Remoção de eco do prompt inicial
    │
    ├── WAKEWORD_VARIANTS: substituição de variações fonéticas para "Jarvis"
    │   (gervis, garvis, jesus, javi, jair, jardim, gervais, jarver, etc.)
    │
    └── Fuzzy matching: SequenceMatcher >= 60% de similaridade com "jarvis"
        na primeira palavra da frase
```

---

## Interface Abstrata

```python
class BaseSTTEngine(ABC):
    def load_model(self) -> None: ...
    def transcribe_pcm(self, pcm_bytes: bytes) -> str: ...
    def transcribe_pcm_with_info(self, pcm_bytes: bytes) -> dict: ...
        # Retorna: {"text": str, "language": str, "probability": float}
    def transcribe_partial_pcm(self, pcm_bytes: bytes) -> str: ...

    async def transcribe_pcm_async(self, pcm_bytes: bytes) -> str: ...
    async def transcribe_pcm_with_info_async(self, pcm_bytes: bytes) -> dict: ...
    async def transcribe_partial_async(self, pcm_bytes: bytes) -> str: ...
```
