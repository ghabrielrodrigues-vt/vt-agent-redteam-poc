"""PII redaction helpers for storage writes."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable
from functools import lru_cache
from typing import Any


EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
PHONE_RE = re.compile(
    r"(?<!\d)(?:\+1[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}(?!\d)"
)
CREDIT_CARD_RE = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")
LEARNER_ID_RE = re.compile(
    r"\b(?:synthetic\.learner_id|learner_id)\s*[:=]\s*[A-Za-z0-9_-]+\b",
    re.IGNORECASE,
)
FALLBACK_ENTITY_RE = re.compile(
    r"\b(?:[A-Z][a-z]+(?:'s)?\s+){2,}[A-Z][a-z]+(?:'s)?\b"
)

NER_LABELS = {"PERSON", "GPE", "LOC", "DATE"}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalise_allowlist(allowlist: Iterable[str] | None) -> set[str]:
    return {item.lower() for item in allowlist or [] if item}


def _is_allowed(text: str, allowlist: set[str]) -> bool:
    lowered = text.lower()
    return any(item in lowered for item in allowlist)


def _valid_luhn(number: str) -> bool:
    total = 0
    reverse_digits = [int(char) for char in number[::-1]]
    for index, digit in enumerate(reverse_digits):
        if index % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def _redact_credit_card(match: re.Match[str]) -> str:
    digits = re.sub(r"\D", "", match.group(0))
    if 13 <= len(digits) <= 19 and _valid_luhn(digits):
        return "[REDACTED-CREDIT-CARD]"
    return match.group(0)


@lru_cache(maxsize=1)
def _spacy_nlp() -> Any | None:
    try:
        import spacy
    except ImportError:
        return None

    for model in ("en_core_web_sm", "en_core_web_md"):
        try:
            return spacy.load(model)
        except OSError:
            continue
    return None


def _redact_spacy_entities(text: str, allowlist: set[str]) -> str:
    nlp = _spacy_nlp()
    if nlp is None:
        return text

    doc = nlp(text)
    replacements: list[tuple[int, int, str]] = []
    for ent in doc.ents:
        if ent.label_ not in NER_LABELS or len(ent.text.split()) <= 2:
            continue
        if _is_allowed(ent.text, allowlist):
            continue
        replacements.append((ent.start_char, ent.end_char, f"[REDACTED-{ent.label_}]"))

    if not replacements:
        return text

    redacted = []
    last = 0
    for start, end, replacement in replacements:
        redacted.append(text[last:start])
        redacted.append(replacement)
        last = end
    redacted.append(text[last:])
    return "".join(redacted)


def _redact_fallback_entities(text: str, allowlist: set[str]) -> str:
    def replace(match: re.Match[str]) -> str:
        value = match.group(0)
        if _is_allowed(value, allowlist):
            return value
        return "[REDACTED-PERSON]"

    return FALLBACK_ENTITY_RE.sub(replace, text)


def redact_text(text: str, *, allowlist: Iterable[str] | None = None) -> str:
    allowlist_values = _normalise_allowlist(allowlist)
    redacted = EMAIL_RE.sub("[REDACTED-EMAIL]", text)
    redacted = SSN_RE.sub("[REDACTED-SSN]", redacted)
    redacted = PHONE_RE.sub("[REDACTED-PHONE]", redacted)
    redacted = LEARNER_ID_RE.sub("[REDACTED-LEARNER-ID]", redacted)
    redacted = CREDIT_CARD_RE.sub(_redact_credit_card, redacted)
    redacted = _redact_spacy_entities(redacted, allowlist_values)
    redacted = _redact_fallback_entities(redacted, allowlist_values)
    return redacted
