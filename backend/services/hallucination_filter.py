import re
from difflib import SequenceMatcher

class HallucinationFilter:
    """
    Filtro e Normalizador Fonético para Eliminação de Alucinações do Whisper.
    Normaliza variações fonéticas de 'Jarvis' e descarta frases fantasma de legendas em silêncio.
    """

    # Regex para capturar variações fonéticas e ortográficas de 'Jarvis'
    WAKEWORD_VARIANTS = re.compile(
        r'\b(gervis|garvis|jesus|javi|jair|jardim|jairis|jarviz|jabes|javier|javes|charvis|javeson|já vi|j\'enviu|jaris|jairus|jarvi)\b',
        re.IGNORECASE
    )

    # Frases fantasma que o Whisper costuma alucinar em silêncios/ruídos de fundo
    PHANTOM_PATTERNS = [
        re.compile(r'legenda por.*', re.IGNORECASE),
        re.compile(r'subtitles by.*', re.IGNORECASE),
        re.compile(r'se inscreva no canal.*', re.IGNORECASE),
        re.compile(r'obrigado por assistir.*', re.IGNORECASE),
        re.compile(r'inscreva-se.*', re.IGNORECASE),
        re.compile(r'transmissão ao vivo.*', re.IGNORECASE),
        re.compile(r'deixe seu like.*', re.IGNORECASE),
        re.compile(r'curta e compartilhe.*', re.IGNORECASE),
    ]

    @classmethod
    def clean_text(cls, text: str) -> str:
        """
        Limpa alucinações e corrige variações fonéticas para 'Jarvis'.
        """
        if not text:
            return ""

        cleaned = text.strip()

        # 1. Filtra frases fantasma de legendas do Whisper e ecos do prompt inicial
        for pattern in cls.PHANTOM_PATTERNS:
            if pattern.search(cleaned):
                return ""

        # Remove vazamento de trechos do prompt inicial caso ocorram
        cleaned = re.sub(r'comandos de voz em português e inglês\.?', '', cleaned, flags=re.IGNORECASE).strip()
        if not cleaned:
            return ""

        # 2. Normaliza variações fonéticas diretas para 'Jarvis'
        cleaned = cls.WAKEWORD_VARIANTS.sub("Jarvis", cleaned)

        # 3. Fuzzy matching fonético no início da frase para termos similares a 'Jarvis'
        words = cleaned.split()
        if words:
            first_word_raw = words[0]
            first_word_clean = re.sub(r'[^\w]', '', first_word_raw).lower()
            if first_word_clean != "jarvis" and len(first_word_clean) >= 3:
                ratio = SequenceMatcher(None, first_word_clean, "jarvis").ratio()
                if ratio >= 0.60: # 60% de similaridade fonética com 'jarvis'
                    punct = first_word_raw[len(first_word_clean):] if len(first_word_raw) > len(first_word_clean) else ""
                    words[0] = "Jarvis" + punct
                    cleaned = " ".join(words)

        return cleaned

hallucination_filter = HallucinationFilter()
