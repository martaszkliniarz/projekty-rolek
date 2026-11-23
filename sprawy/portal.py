"""
Portal Informacyjny Sądów Powszechnych — zapis zdarzeń jako wpływów.

Robot logujący się do portalu dostarcza tu znormalizowane zdarzenia z trzech zakładek:
  * „Czynności”   → rodzaj CZYNNOSC   (historia sprawy),
  * „Dokumenty”   → rodzaj DOKUMENT   (pisma z akt — otwieranie NIE powoduje doręczenia),
  * „Doręczenia”  → rodzaj DORECZENIE (tylko LISTA: data umieszczenia i opis; robot NIGDY
                    nie otwiera i nie pobiera dokumentu z tej zakładki — to byłoby doręczenie).

Sam robot (przeglądarka sterowana automatycznie) zostanie dopisany po poznaniu
rzeczywistej struktury stron portalu — patrz docs/PLAN.md.
"""

from dataclasses import dataclass
from datetime import date

from .models import Postepowanie, Wplyw
from .sygnatury import dopasuj_sprawe, normalizuj


@dataclass
class ZdarzeniePortalu:
    sygnatura: str
    rodzaj: str          # Wplyw.Rodzaj.CZYNNOSC / DOKUMENT / DORECZENIE
    data: date           # data czynności / dokumentu / umieszczenia doręczenia
    opis: str
    zewn_id: str         # stały identyfikator z portalu (albo skrót: sygnatura+data+opis)
    tresc: str = ""


def zapisz_zdarzenia(zdarzenia: list[ZdarzeniePortalu]) -> list[Wplyw]:
    mapa = {normalizuj(p.sygnatura): p.sprawa
            for p in Postepowanie.objects.exclude(sygnatura="").select_related("sprawa")}
    nowe = []
    for z in zdarzenia:
        zid = f"portal:{z.zewn_id}"[:300]
        if Wplyw.objects.filter(zewn_id=zid).exists():
            continue
        sprawa = mapa.get(normalizuj(z.sygnatura)) or dopasuj_sprawe(z.sygnatura)[0]
        nowe.append(Wplyw.objects.create(
            zrodlo=Wplyw.Zrodlo.PORTAL, rodzaj=z.rodzaj, zewn_id=zid, data=z.data,
            tytul=z.opis[:300], tresc=z.tresc, sygnatura=z.sygnatura, sprawa=sprawa,
        ))
    return nowe
