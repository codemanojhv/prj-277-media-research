from __future__ import annotations

import re

LANGUAGE_RANGES = {
    "hi": (0x0900, 0x097F),
    "kn": (0x0C80, 0x0CFF),
    "ta": (0x0B80, 0x0BFF),
    "te": (0x0C00, 0x0C7F),
}


def detect_language(text: str, declared: str | None = None) -> tuple[str, float]:
    letters = [char for char in text if char.isalpha()]
    if not letters:
        return (declared if declared in {"en", *LANGUAGE_RANGES} else "und", 0.0)
    counts = {
        language: sum(start <= ord(char) <= end for char in letters)
        for language, (start, end) in LANGUAGE_RANGES.items()
    }
    best_language = max(counts, key=counts.get)
    proportion = counts[best_language] / len(letters)
    if proportion >= 0.18:
        return best_language, round(min(0.99, 0.58 + proportion * 0.41), 3)
    latin = sum("LATIN" in __import__("unicodedata").name(char, "") for char in letters) / len(letters)
    if latin >= 0.6:
        return "en", round(min(0.88, 0.58 + latin * 0.3), 3)
    if declared in {"en", *LANGUAGE_RANGES}:
        return declared, 0.45
    return "und", 0.2


def clean_text(value: str) -> str:
    value = re.sub(r"\s+", " ", value or "")
    return value.strip()
