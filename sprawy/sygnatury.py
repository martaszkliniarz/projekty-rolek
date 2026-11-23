"""Rozpoznawanie sygnatur akt w tekście i dopasowanie do spraw kancelarii."""

import re

# Sygnatury sądowe, np.: I C 123/26, II K 456/2026, IV RC 12/25, III Nsm 100/26, VI Ka 12/26, I ACa 1234/25,
# także z prefiksem typu "IV RCa", oraz prokuratorskie, np. PR 2 Ds. 123.2026, 1 Ds 456/26.
WZOR_SAD = re.compile(r"\b[IVXL]{1,6}\s+[A-Z][A-Za-z]{0,4}(?:\s+[A-Z][a-z]{0,3})?\s+\d{1,6}\s*/\s*\d{2,4}\b")
WZOR_PROK = re.compile(r"\bPR\s+\d{1,2}\s+[A-Z][a-z]{1,2}\.?\s+\d{1,6}\.\d{4}\b|\b\d\s+Ds\.?\s+\d{1,6}[./]\d{2,4}\b")


def normalizuj(sygn: str) -> str:
    """'I C 123 / 2026' i 'i c 123/26' → 'ic123/26' (rok skrócony do 2 cyfr)."""
    s = re.sub(r"\s+", "", sygn).lower().rstrip(".").replace("ds.", "ds")
    s = re.sub(r"([/.])(?:19|20)(\d{2})$", r"\1\2", s)
    return s


def znajdz_sygnatury(tekst: str) -> list[str]:
    wyniki = []
    for wzor in (WZOR_SAD, WZOR_PROK):
        for m in wzor.finditer(tekst or ""):
            s = re.sub(r"\s+", " ", m.group(0)).strip()
            if s not in wyniki:
                wyniki.append(s)
    return wyniki


def dopasuj_sprawe(tekst: str):
    """Zwraca (sprawa albo None, pierwsza rozpoznana sygnatura albo '')."""
    from .models import Postepowanie

    znalezione = znajdz_sygnatury(tekst)
    if not znalezione:
        return None, ""
    mapa = {}
    for p in Postepowanie.objects.exclude(sygnatura="").select_related("sprawa"):
        mapa.setdefault(normalizuj(p.sygnatura), p.sprawa)
    for s in znalezione:
        if normalizuj(s) in mapa:
            return mapa[normalizuj(s)], s
    return None, znalezione[0]
