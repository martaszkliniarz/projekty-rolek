"""Eksport terminów do formatu iCalendar (.ics) — do subskrypcji w Kalendarzu Google."""

from datetime import datetime, timedelta, timezone


def _esc(s: str) -> str:
    return (s or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _fold(line: str) -> str:
    # RFC 5545: linie max 75 oktetów
    out, b = [], line.encode()
    while len(b) > 75:
        cut = 75
        while (b[cut] & 0xC0) == 0x80:  # nie tniemy znaku UTF-8
            cut -= 1
        out.append(b[:cut].decode())
        b = b" " + b[cut:]
    out.append(b.decode())
    return "\r\n".join(out)


def kalendarz_ics(terminy, nazwa="Kancelaria – terminy", anonimowy=True) -> str:
    """anonimowy=True: w kalendarzu tylko nr sprawy i rodzaj terminu, bez nazwisk
    i sygnatur (tajemnica adwokacka — dane trafiają na serwery Google)."""
    teraz = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    linie = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Kancelaria//Terminy//PL",
        "CALSCALE:GREGORIAN", "METHOD:PUBLISH", f"X-WR-CALNAME:{_esc(nazwa)}",
        "X-WR-TIMEZONE:Europe/Warsaw",
    ]
    for t in terminy:
        prefiks = "⚖️ " if t.rodzaj == "rozprawa" else "⏰ " if t.rodzaj == "procesowy" else ""
        nazwa_sprawy = t.sprawa.numer if anonimowy else t.sprawa.tytul
        opis = [f"Sprawa: {t.sprawa.numer if anonimowy else t.sprawa}", f"Rodzaj: {t.get_rodzaj_display()}"]
        if t.podstawa:
            opis.append(f"Podstawa: {t.podstawa}")
        if not anonimowy:
            if t.sprawa.sygnatury():
                opis.append(f"Sygn.: {t.sprawa.sygnatury()}")
            if t.wyliczenie:
                opis.append(t.wyliczenie)
        linie += ["BEGIN:VEVENT", f"UID:{t.uid}@kancelaria", f"DTSTAMP:{teraz}"]
        if t.godzina:
            start = datetime.combine(t.data, t.godzina)
            koniec = start + timedelta(hours=1)
            linie += [f"DTSTART;TZID=Europe/Warsaw:{start:%Y%m%dT%H%M%S}",
                      f"DTEND;TZID=Europe/Warsaw:{koniec:%Y%m%dT%H%M%S}"]
        else:
            linie += [f"DTSTART;VALUE=DATE:{t.data:%Y%m%d}",
                      f"DTEND;VALUE=DATE:{t.data + timedelta(days=1):%Y%m%d}"]
        linie += [
            f"SUMMARY:{_esc(prefiks + t.opis + ' – ' + nazwa_sprawy)}",
            f"DESCRIPTION:{_esc(chr(10).join(opis))}",
        ]
        if t.miejsce:
            linie.append(f"LOCATION:{_esc(t.miejsce)}")
        if t.status == "anulowany":
            linie.append("STATUS:CANCELLED")
        linie.append("END:VEVENT")
    linie.append("END:VCALENDAR")
    return "\r\n".join(_fold(l) for l in linie) + "\r\n"
