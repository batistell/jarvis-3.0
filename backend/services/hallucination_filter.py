import re
from difflib import SequenceMatcher

class HallucinationFilter:
    """
    Filtro e Normalizador Fonético para Eliminação de Alucinações do Whisper.
    - Filtra frases fantasma de silêncio/ruído geradas pelo Whisper
    - Filtra ruído de fundo (muito curto, apenas pontuação, etc.)
    - Normaliza variações fonéticas de 'Jarvis'
    """

    # Regex para capturar variações fonéticas e ortográficas de 'Jarvis'
    WAKEWORD_VARIANTS = re.compile(
        r'\b(gervis|garvis|jesus|javi|jair|jardim|jairis|jarviz|jabes|javier|javes|charvis|javeson|já vi|j\'enviu|jaris|jairus|jarvi|gervais|gerves|garves|jarbes|jarver)\b',
        re.IGNORECASE
    )

    # -------------------------------------------------------------------------
    # Frases fantasma — Whisper alucina estas frases em silêncio/ruído de fundo
    # Inclui variações PT, EN, ES, FR e caracteres unicode comuns de alucinação
    # -------------------------------------------------------------------------
    PHANTOM_EXACT = {
        # EN — as mais comuns do Whisper
        "thank you", "thank you.", "thanks", "thanks.", "thank you so much",
        "thank you very much", "thank you for watching", "thanks for watching",
        "thank you for listening", "please subscribe", "don't forget to subscribe",
        "like and subscribe", "see you next time", "see you in the next video",
        "bye", "bye bye", "bye.", "goodbye", "goodbye.", "you're welcome",
        "you're welcome.", "okay", "okay.", "ok", "ok.", "hmm", "hmm.",
        "uh", "uh.", "um", "um.", "uh huh", "uh-huh", "mm-hmm", "mm hmm",
        "never mind", "never mind.", "alright", "alright.", "right", "right.",
        "sure", "sure.", "yeah", "yeah.", "yes", "yes.", "no", "no.",
        "i see", "i see.", "i love you", "i love you.", "i love you too",
        "i love you too.", "oh", "oh.", "ah", "ah.", "oh, okay", "oh okay",
        "got it", "got it.", "of course", "of course.", "absolutely",
        "absolutely.", "exactly", "exactly.", "indeed", "indeed.",
        "continue", "continue.", "go on", "go on.", "proceed", "proceed.",
        "you can proceed if you wish", "you can proceed if you wish.",
        "one moment", "one moment.", "just a moment", "just a moment.",
        "♪", "♪♪", "♫", "[music]", "[applause]", "[laughter]",
        "[inaudible]", "[silence]", "[noise]", "[background noise]",
        "subtítulos realizados por la comunidad de amara.org",
        # PT — alucinações comuns
        "obrigado", "obrigado.", "obrigada", "obrigada.", "de nada", "de nada.",
        "com licença", "com licença.", "por favor", "por favor.", "sim", "sim.",
        "não", "não.", "ok.", "tá", "tá.", "tudo bem", "tudo bem.",
        "até logo", "até logo.", "tchau", "tchau.", "oi", "oi.", "olá", "olá.",
        "obrigado por assistir", "inscreva-se no canal", "curta o vídeo",
        "deixe seu comentário", "ative o sininho",
        # Cyrillics / outros idiomas alucinados em silêncio longo
        "продолжение следует", "印刷",
    }

    # Padrões regex para frases mais longas de alucinação
    PHANTOM_PATTERNS = [
        re.compile(r'legenda por', re.IGNORECASE),
        re.compile(r'subtitles by', re.IGNORECASE),
        re.compile(r'se inscreva no canal', re.IGNORECASE),
        re.compile(r'obrigado por assistir', re.IGNORECASE),
        re.compile(r'inscreva-?se', re.IGNORECASE),
        re.compile(r'transmiss[aã]o ao vivo', re.IGNORECASE),
        re.compile(r'deixe seu like', re.IGNORECASE),
        re.compile(r'curta e compartilhe', re.IGNORECASE),
        re.compile(r'ative o sininho', re.IGNORECASE),
        re.compile(r'amara\.org', re.IGNORECASE),
        re.compile(r'please\s+(like|subscribe|share)', re.IGNORECASE),
        re.compile(r'don\'?t forget to (like|subscribe|share)', re.IGNORECASE),
        re.compile(r'see you (next|in the next)', re.IGNORECASE),
        re.compile(r'you can proceed if you wish', re.IGNORECASE),
        re.compile(r'печать на', re.IGNORECASE),           # Russo fantasma
        re.compile(r'продолжение следует', re.IGNORECASE), # Russo fantasma
        re.compile(r'^\[.*?\]$'),                          # Qualquer coisa entre colchetes [...]
        re.compile(r'^♪.*?♪?$'),                           # Notas musicais
        re.compile(r'^\(.*?\)$'),                          # Qualquer coisa entre parênteses (...)
    ]

    # -------------------------------------------------------------------------
    # Filtro de ruído: texto muito curto ou sem conteúdo real de fala
    # -------------------------------------------------------------------------
    # Tokens que sozinhos não constituem fala real e devem ser filtrados
    NOISE_ONLY_TOKENS = {
        ".", ",", "!", "?", "...", "..", "-", "--", "—", "–",
        "uh", "um", "hmm", "hm", "ah", "oh", "mm", "eh",
        "mhm", "uh-huh", "mm-hmm",
    }

    @classmethod
    def _is_noise(cls, text: str) -> bool:
        """
        Retorna True se o texto for apenas ruído/artefato sonoro sem fala real.
        Critérios:
        - Comprimento < 3 caracteres alfanuméricos
        - Todos os tokens são marcadores de ruído conhecidos
        - Apenas pontuação/símbolos
        """
        stripped = text.strip()
        # Texto com menos de 2 caracteres alfanuméricos reais
        alnum_chars = re.sub(r'[^a-zA-ZÀ-ÿ0-9]', '', stripped)
        if len(alnum_chars) < 3:
            return True

        # Todos os tokens são ruído
        tokens = [t.lower().strip('.,!?;:') for t in stripped.split()]
        if tokens and all(t in cls.NOISE_ONLY_TOKENS for t in tokens):
            return True

        return False

    @classmethod
    def clean_text(cls, text: str) -> str:
        """
        Pipeline completo de limpeza de transcrição do Whisper:
        1. Filtra frases exatas de alucinação (case-insensitive)
        2. Filtra padrões regex de frases fantasma
        3. Filtra ruído (texto muito curto ou sem conteúdo)
        4. Normaliza variações fonéticas de 'Jarvis'
        5. Fuzzy matching de wake-word no início da frase
        """
        if not text:
            return ""

        cleaned = text.strip()

        # 1. Verificação exata de frases fantasma (set lookup O(1))
        if cleaned.lower() in cls.PHANTOM_EXACT:
            return ""

        # 2. Filtro de padrões regex de alucinação
        for pattern in cls.PHANTOM_PATTERNS:
            if pattern.search(cleaned):
                return ""

        # 3. Filtro de ruído / texto sem conteúdo real
        if cls._is_noise(cleaned):
            return ""

        # 4. Remove vazamento de trechos de prompt inicial
        cleaned = re.sub(r'comandos de voz em português e inglês\.?', '', cleaned, flags=re.IGNORECASE).strip()
        if not cleaned:
            return ""

        # 5. Normaliza variações fonéticas diretas para 'Jarvis'
        cleaned = cls.WAKEWORD_VARIANTS.sub("Jarvis", cleaned)

        # 6. Fuzzy matching fonético no início da frase
        words = cleaned.split()
        if words:
            first_word_raw = words[0]
            first_word_clean = re.sub(r'[^\w]', '', first_word_raw).lower()
            if first_word_clean != "jarvis" and len(first_word_clean) >= 3:
                ratio = SequenceMatcher(None, first_word_clean, "jarvis").ratio()
                if ratio >= 0.60:
                    punct = first_word_raw[len(first_word_clean):] if len(first_word_raw) > len(first_word_clean) else ""
                    words[0] = "Jarvis" + punct
                    cleaned = " ".join(words)

        return cleaned

hallucination_filter = HallucinationFilter()
