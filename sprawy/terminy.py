"""
Kalkulator terminów procesowych (KPC i KPK).

Zasady (wspólne dla obu kodeksów):
  * nie wlicza się dnia zdarzenia, od którego biegnie termin
    (art. 111 § 2 KC w zw. z art. 165 § 1 KPC; art. 123 § 1 KPK),
  * termin w tygodniach kończy się z upływem dnia, który nazwą odpowiada
    dniowi zdarzenia (art. 112 KC),
  * termin w miesiącach/latach kończy się z upływem dnia, który datą
    odpowiada dniowi zdarzenia, a gdyby takiego dnia nie było —
    w ostatnim dniu miesiąca (art. 112 KC; art. 123 § 2 KPK),
  * jeżeli koniec terminu przypada na sobotę albo dzień ustawowo wolny
    od pracy, termin upływa następnego dnia, który nie jest sobotą ani
    dniem wolnym (art. 115 KC; art. 123 § 3 KPK).

Doręczenia:
  * portal informacyjny — dokument uważa się za doręczony w chwili jego
    otwarcia, a w razie nieotwarcia — po upływie 14 dni od umieszczenia
    w portalu (art. 131¹ KPC),
  * awizo pocztowe — doręczenie uważa się za dokonane z upływem
    ostatniego dnia 14-dniowego okresu od pierwszego zawiadomienia
    (art. 139 § 1 KPC, art. 133 § 1 KPK).

UWAGA: wynik kalkulatora jest pomocą, a nie opinią prawną — przy
każdym terminie warto spojrzeć na wyliczenie i podstawę prawną.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date, timedelta
from functools import lru_cache

DNI_TYGODNIA = ["poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota", "niedziela"]


# ---------------------------------------------------------------- święta ---

def wielkanoc(rok: int) -> date:
    """Data Niedzieli Wielkanocnej (algorytm Meeusa/Jonesa/Butchera)."""
    a = rok % 19
    b, c = divmod(rok, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    miesiac, dzien = divmod(h + l - 7 * m + 114, 31)
    return date(rok, miesiac, dzien + 1)


@lru_cache(maxsize=64)
def swieta(rok: int) -> dict[date, str]:
    """Dni ustawowo wolne od pracy (ustawa z 18.01.1951 r.), bez niedziel."""
    w = wielkanoc(rok)
    dni = {
        date(rok, 1, 1): "Nowy Rok",
        date(rok, 1, 6): "Trzech Króli",
        w: "Wielkanoc",
        w + timedelta(days=1): "Poniedziałek Wielkanocny",
        date(rok, 5, 1): "Święto Pracy",
        date(rok, 5, 3): "Święto Konstytucji 3 Maja",
        w + timedelta(days=49): "Zielone Świątki",
        w + timedelta(days=60): "Boże Ciało",
        date(rok, 8, 15): "Wniebowzięcie NMP",
        date(rok, 11, 1): "Wszystkich Świętych",
        date(rok, 11, 11): "Święto Niepodległości",
        date(rok, 12, 25): "Boże Narodzenie (1. dzień)",
        date(rok, 12, 26): "Boże Narodzenie (2. dzień)",
    }
    if rok >= 2025:  # Wigilia wolna od 2025 r.
        dni[date(rok, 12, 24)] = "Wigilia"
    return dni


def nazwa_dnia_wolnego(d: date) -> str | None:
    """Zwraca powód, dla którego dzień nie jest roboczym (albo None)."""
    if d in swieta(d.year):
        return swieta(d.year)[d]
    if d.weekday() == 6:
        return "niedziela"
    if d.weekday() == 5:
        return "sobota"
    return None


def jest_dniem_roboczym(d: date) -> bool:
    return nazwa_dnia_wolnego(d) is None


def nastepny_dzien_roboczy(d: date) -> date:
    while not jest_dniem_roboczym(d):
        d += timedelta(days=1)
    return d


# ---------------------------------------------------------------- okresy ---

JEDNOSTKI = {
    "dni": "dni",
    "tygodnie": "tygodnie",
    "miesiace": "miesiące",
    "lata": "lata",
}


def _dodaj_miesiace(d: date, miesiace: int) -> date:
    m = d.month - 1 + miesiace
    rok, mies = d.year + m // 12, m % 12 + 1
    ostatni = calendar.monthrange(rok, mies)[1]
    return date(rok, mies, min(d.day, ostatni))


def dodaj_okres(start: date, ilosc: int, jednostka: str) -> date:
    if jednostka == "dni":
        return start + timedelta(days=ilosc)
    if jednostka == "tygodnie":
        return start + timedelta(weeks=ilosc)
    if jednostka == "miesiace":
        return _dodaj_miesiace(start, ilosc)
    if jednostka == "lata":
        return _dodaj_miesiace(start, 12 * ilosc)
    raise ValueError(f"Nieznana jednostka: {jednostka}")


@dataclass
class WynikTerminu:
    data_zdarzenia: date
    koniec_nominalny: date
    koniec: date
    wyjasnienie: list[str] = field(default_factory=list)

    @property
    def przesuniety(self) -> bool:
        return self.koniec != self.koniec_nominalny


def fmt(d: date) -> str:
    return f"{d:%d.%m.%Y} ({DNI_TYGODNIA[d.weekday()]})"


def oblicz_termin(data_zdarzenia: date, ilosc: int, jednostka: str) -> WynikTerminu:
    nominalny = dodaj_okres(data_zdarzenia, ilosc, jednostka)
    koniec = nastepny_dzien_roboczy(nominalny)
    opis = [
        f"Zdarzenie: {fmt(data_zdarzenia)} — dnia zdarzenia nie wlicza się.",
        f"{ilosc} {JEDNOSTKI[jednostka]} → koniec nominalny: {fmt(nominalny)}.",
    ]
    if koniec != nominalny:
        d, powody = nominalny, []
        while d < koniec:
            powody.append(f"{d:%d.%m} – {nazwa_dnia_wolnego(d)}")
            d += timedelta(days=1)
        opis.append(
            "Dzień wolny/sobota (" + "; ".join(powody) + ") → przesunięcie na "
            f"najbliższy dzień roboczy: {fmt(koniec)} (art. 115 KC / art. 123 § 3 KPK)."
        )
    else:
        opis.append("Koniec przypada na dzień roboczy — bez przesunięcia.")
    return WynikTerminu(data_zdarzenia, nominalny, koniec, opis)


# ------------------------------------------------------------- doręczenia ---

DNI_FIKCJI = 14


def doreczenie_portal(umieszczenie: date, otwarcie: date | None = None) -> tuple[date, str]:
    """Data doręczenia przez portal informacyjny (art. 131¹ KPC)."""
    fikcja = umieszczenie + timedelta(days=DNI_FIKCJI)
    if otwarcie and otwarcie < fikcja:
        return otwarcie, f"Otwarcie dokumentu w portalu {fmt(otwarcie)} = doręczenie."
    return fikcja, (
        f"Umieszczenie w portalu {fmt(umieszczenie)}; brak otwarcia → "
        f"doręczenie z upływem 14 dni: {fmt(fikcja)}."
    )


def doreczenie_awizo(pierwsze_awizo: date) -> tuple[date, str]:
    """Doręczenie zastępcze po dwukrotnym awizo (art. 139 § 1 KPC)."""
    d = pierwsze_awizo + timedelta(days=DNI_FIKCJI)
    return d, f"Pierwsze awizo {fmt(pierwsze_awizo)} → doręczenie zastępcze z upływem 14 dni: {fmt(d)}."


# ---------------------------------------------------------------- presety ---
# Najczęstsze terminy w sprawach rodzinnych i karnych. Proszę zweryfikować
# z aktualnym brzmieniem przepisów — łatwo dopisać kolejne.

PRESETY = [
    # KPC (sprawy rodzinne, procesowe i nieprocesowe)
    {"kod": "kpc_uzasadnienie", "tryb": "KPC", "nazwa": "Wniosek o uzasadnienie wyroku",
     "ilosc": 1, "jednostka": "tygodnie", "podstawa": "art. 328 § 1 KPC",
     "od": "od ogłoszenia wyroku / doręczenia sentencji"},
    {"kod": "kpc_apelacja", "tryb": "KPC", "nazwa": "Apelacja",
     "ilosc": 2, "jednostka": "tygodnie", "podstawa": "art. 369 § 1 KPC",
     "od": "od doręczenia wyroku z uzasadnieniem"},
    {"kod": "kpc_zazalenie", "tryb": "KPC", "nazwa": "Zażalenie",
     "ilosc": 1, "jednostka": "tygodnie", "podstawa": "art. 394 § 2 KPC",
     "od": "od doręczenia postanowienia"},
    {"kod": "kpc_skarga_kasacyjna", "tryb": "KPC", "nazwa": "Skarga kasacyjna",
     "ilosc": 2, "jednostka": "miesiace", "podstawa": "art. 398⁵ § 1 KPC",
     "od": "od doręczenia orzeczenia z uzasadnieniem"},
    {"kod": "kpc_sprzeciw_nakaz", "tryb": "KPC", "nazwa": "Sprzeciw od nakazu zapłaty",
     "ilosc": 2, "jednostka": "tygodnie", "podstawa": "art. 505 § 1 KPC",
     "od": "od doręczenia nakazu"},
    {"kod": "kpc_sprzeciw_zaoczny", "tryb": "KPC", "nazwa": "Sprzeciw od wyroku zaocznego",
     "ilosc": 2, "jednostka": "tygodnie", "podstawa": "art. 344 § 2 KPC",
     "od": "od doręczenia wyroku"},
    # KPK
    {"kod": "kpk_uzasadnienie", "tryb": "KPK", "nazwa": "Wniosek o uzasadnienie wyroku",
     "ilosc": 7, "jednostka": "dni", "podstawa": "art. 422 § 1 KPK",
     "od": "od ogłoszenia wyroku"},
    {"kod": "kpk_apelacja", "tryb": "KPK", "nazwa": "Apelacja",
     "ilosc": 14, "jednostka": "dni", "podstawa": "art. 445 § 1 KPK",
     "od": "od doręczenia wyroku z uzasadnieniem"},
    {"kod": "kpk_zazalenie", "tryb": "KPK", "nazwa": "Zażalenie",
     "ilosc": 7, "jednostka": "dni", "podstawa": "art. 460 KPK",
     "od": "od ogłoszenia / doręczenia postanowienia"},
    {"kod": "kpk_kasacja", "tryb": "KPK", "nazwa": "Kasacja",
     "ilosc": 30, "jednostka": "dni", "podstawa": "art. 524 § 1 KPK",
     "od": "od doręczenia orzeczenia z uzasadnieniem"},
    {"kod": "kpk_sprzeciw_nakazowy", "tryb": "KPK", "nazwa": "Sprzeciw od wyroku nakazowego",
     "ilosc": 7, "jednostka": "dni", "podstawa": "art. 506 § 1 KPK",
     "od": "od doręczenia wyroku nakazowego"},
    {"kod": "kpk_zazalenie_umorzenie", "tryb": "KPK", "nazwa": "Zażalenie na umorzenie postępowania przygotowawczego",
     "ilosc": 7, "jednostka": "dni", "podstawa": "art. 306 § 1 w zw. z art. 460 KPK",
     "od": "od doręczenia postanowienia"},
]

PRESETY_PO_KODZIE = {p["kod"]: p for p in PRESETY}
