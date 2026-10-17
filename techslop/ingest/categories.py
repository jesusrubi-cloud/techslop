"""Deterministic Spanish classification, with manual override in raw_data."""
from __future__ import annotations

import re
import unicodedata

CATEGORIES = ("politica_internacional", "economia", "ciencia", "tecnologia", "actualidad_general")


def normalize(text: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFKD', text.casefold()) if not unicodedata.combining(c))


def classify(title: str, tags: list[str] | None = None) -> str:
    text = normalize(' '.join([title, *(tags or [])]))
    keywords = {
        "tecnologia": r"tecnolog\w*|inteligencia artificial|software|ciber\w*|semiconductores|internet",
        "ciencia": r"ciencia|cientific\w*|investig\w*|vacuna\w*|espacial|nasa|salud|clima",
        "economia": r"econom\w*|inflacion|banco\w*|comercio|arancel\w*|finanza\w*|mercado\w*|pib",
        "politica_internacional": r"politica|guerra|eleccion\w*|gobierno\w*|presiden\w*|diplomac\w*|onu|conflicto\w*|internacional",
    }
    for category, pattern in keywords.items():
        if re.search(r'\b(?:' + pattern + r')\b', text):
            return category
    return "actualidad_general"
