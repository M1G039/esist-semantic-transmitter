from __future__ import annotations

import re
from collections import Counter


_TOKEN_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9']+")
_NUMBER_RE = re.compile(r"\b\d+(?:[.,]\d+)?\b")
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_URL_RE = re.compile(r"\bhttps?://[^\s]+\b", re.IGNORECASE)

_STOPWORDS = {
    "a",
    "about",
    "after",
    "again",
    "all",
    "am",
    "an",
    "and",
    "any",
    "are",
    "as",
    "at",
    "be",
    "because",
    "been",
    "before",
    "being",
    "but",
    "by",
    "can",
    "could",
    "de",
    "do",
    "does",
    "e",
    "em",
    "for",
    "from",
    "have",
    "how",
    "i",
    "if",
    "in",
    "is",
    "it",
    "la",
    "me",
    "my",
    "na",
    "no",
    "not",
    "o",
    "of",
    "on",
    "or",
    "os",
    "para",
    "por",
    "que",
    "se",
    "she",
    "so",
    "the",
    "their",
    "them",
    "there",
    "they",
    "this",
    "to",
    "um",
    "uma",
    "un",
    "we",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "with",
    "you",
    "your",
}

_COMMAND_STARTERS = {
    "abre",
    "add",
    "adiciona",
    "ativa",
    "call",
    "close",
    "create",
    "delete",
    "envia",
    "open",
    "play",
    "send",
    "set",
    "show",
    "start",
    "stop",
}


def normalize_transcript(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    return cleaned

def prepare_transcript(manual_transcript: str) -> str:
    return normalize_transcript(manual_transcript)

def _guess_language(text: str) -> str:
    lower = text.lower()
    pt_markers = (" de ", " que ", " não ", " para ", " com ", " uma ")
    en_markers = (" the ", " and ", " with ", " for ", " not ", " this ")
    pt_score = sum(1 for marker in pt_markers if marker in f" {lower} ")
    en_score = sum(1 for marker in en_markers if marker in f" {lower} ")
    if pt_score > en_score and pt_score > 0:
        return "pt"
    if en_score > pt_score and en_score > 0:
        return "en"
    return "unknown"


def _detect_intent(text: str) -> str:
    lowered = text.lower().strip()
    if not lowered:
        return "unknown"
    first_token = _TOKEN_RE.findall(lowered[:40])
    if first_token and first_token[0] in _COMMAND_STARTERS:
        return "command"
    if "?" in text:
        return "question"
    return "statement"


def _detect_tone(text: str) -> str:
    lowered = text.lower()
    urgent_terms = ("urgent", "asap", "rápido", "agora", "socorro")
    if any(term in lowered for term in urgent_terms):
        return "urgent"
    if "!" in text:
        return "excited"
    return "neutral"


def _extract_keywords(text: str, limit: int = 8) -> list[str]:
    tokens = [token.lower() for token in _TOKEN_RE.findall(text)]
    filtered = [
        token
        for token in tokens
        if token not in _STOPWORDS and len(token) > 2 and not token.isdigit()
    ]
    ranked = Counter(filtered).most_common(limit)
    return [token for token, _ in ranked]


def _summary(text: str, max_chars: int = 160) -> str:
    if len(text) <= max_chars:
        return text
    sentence = text.split(".")[0].strip()
    if sentence and len(sentence) <= max_chars:
        return sentence
    return f"{text[:max_chars - 3].rstrip()}..."


def encode_semantics(transcript: str) -> dict:
    normalized = normalize_transcript(transcript)
    keywords = _extract_keywords(normalized)

    return {
        "language_guess": _guess_language(normalized),
        "intent": _detect_intent(normalized),
        "tone": _detect_tone(normalized),
        "keywords": keywords,
        "entities": {
            "numbers": _NUMBER_RE.findall(normalized),
            "emails": _EMAIL_RE.findall(normalized),
            "urls": _URL_RE.findall(normalized),
        },
        "semantic_summary": _summary(normalized),
        "word_count": len(_TOKEN_RE.findall(normalized)),
        "character_count": len(normalized),
    }


