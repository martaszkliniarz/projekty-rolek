"""Poranny raport — zestawienie wysyłane e-mailem."""

from datetime import date, timedelta

from django.conf import settings
from django.core.mail import send_mail

from .models import Czynnosc, Posiedzenie, Termin, Wplyw


def _termin(t):
    godz = f" {t.godzina:%H:%M}" if t.godzina else ""
    return f"  • {t.data:%d.%m}{godz} — {t.opis} [{t.sprawa.numer} {t.sprawa.tytul}]"


def tresc_raportu(dzis: date | None = None) -> tuple[str, str]:
    dzis = dzis or date.today()
    otwarte = Termin.objects.filter(status=Termin.Status.OTWARTY).select_related("sprawa")
    zalegle = list(otwarte.filter(data__lt=dzis))
    na_dzis = list(otwarte.filter(data=dzis))
    tydzien = list(otwarte.filter(data__gt=dzis, data__lte=dzis + timedelta(days=7)))
    wplywy = list(Wplyw.objects.filter(status=Wplyw.Status.NOWY).select_related("sprawa"))
    do_potw = Czynnosc.objects.filter(potwierdzona=False).count()

    linie = [f"Dzień dobry! Raport na {dzis:%d.%m.%Y}.", ""]
    if zalegle:
        linie += ["⚠️ TERMINY PO CZASIE — PILNE:"] + [_termin(t) for t in zalegle] + [""]
    linie += ["DZIŚ:"] + ([_termin(t) for t in na_dzis] or ["  brak"]) + [""]
    linie += ["NAJBLIŻSZE 7 DNI:"] + ([_termin(t) for t in tydzien] or ["  brak"]) + [""]
    posiedzenia = Posiedzenie.objects.filter(odbyte=False, data__gte=dzis, data__lte=dzis + timedelta(days=7)) \
        .select_related("mediacja")
    if posiedzenia:
        linie.append("MEDIACJE — POSIEDZENIA (7 dni):")
        for p in posiedzenia:
            godz = f" {p.godzina:%H:%M}" if p.godzina else ""
            linie.append(f"  • {p.data:%d.%m}{godz} — {p.get_rodzaj_display()} [{p.mediacja.numer}]")
        linie.append("")
    from .views import mediacje_alarmy
    alarmy = mediacje_alarmy(dzis)
    if alarmy:
        linie += ["MEDIACJE — DO UWAGI:"] + [f"  • {m.numer}: {txt}" for m, txt in alarmy] + [""]
    linie.append(f"NOWE WPŁYWY (poczta i portal): {len(wplywy)}")
    for w in wplywy[:30]:
        gdzie = w.sprawa.numer if w.sprawa else "NIEPRZYPISANY"
        alarm = " ⚠️ DORĘCZENIE" if w.rodzaj == Wplyw.Rodzaj.DORECZENIE else ""
        linie.append(f"  • {w.data:%d.%m} [{gdzie}]{alarm} {w.tytul}")
    if do_potw:
        linie += ["", f"Wpisy asystenta do potwierdzenia: {do_potw}"]
    if settings.ADRES_PROGRAMU:
        linie += ["", f"Program: {settings.ADRES_PROGRAMU}"]

    temat = f"Kancelaria — raport {dzis:%d.%m}: {len(na_dzis)} na dziś, {len(wplywy)} nowych wpływów"
    if zalegle:
        temat = f"⚠️ {len(zalegle)} po terminie! " + temat
    return temat, "\n".join(linie)


def wyslij_raport(dzis: date | None = None) -> str:
    if not settings.RAPORT_ODBIORCY:
        raise RuntimeError("Ustaw RAPORT_ODBIORCY w pliku .env.")
    temat, tresc = tresc_raportu(dzis)
    send_mail(temat, tresc, None, settings.RAPORT_ODBIORCY)
    return temat
