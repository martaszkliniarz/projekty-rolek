"""
Odczyt poczty (IMAP, np. home.pl) i zapis istotnych wiadomości jako wpływów.

Bezpieczeństwo:
  * skrzynka otwierana jest TYLKO DO ODCZYTU (readonly + BODY.PEEK) — program
    niczego nie usuwa, nie przenosi i nie oznacza jako przeczytane,
  * zapisywane są tylko wiadomości z portalu oraz te, w których rozpoznano
    sygnaturę sprawy prowadzonej w kancelarii (reszta poczty jest pomijana).
"""

import email
import html
import imaplib
import logging
import re
from datetime import date, timedelta
from email.policy import default as polityka
from email.utils import parsedate_to_datetime

from django.conf import settings

from .models import Wplyw
from .sygnatury import dopasuj_sprawe

log = logging.getLogger(__name__)
MAKS_TRESC = 5000


def _tekst(msg) -> str:
    czesc = msg.get_body(preferencelist=("plain", "html"))
    if czesc is None:
        return ""
    try:
        t = czesc.get_content()
    except (LookupError, UnicodeDecodeError):
        t = czesc.get_payload(decode=True).decode("utf-8", "replace")
    if czesc.get_content_type() == "text/html":
        t = re.sub(r"(?is)<(script|style).*?</\1>", " ", t)
        t = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>", "\n", t)
        t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    t = re.sub(r"[ \t\xa0]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n\n", t).strip()


def czy_z_portalu(nadawca: str, temat: str) -> bool:
    znaczniki = [z.strip().lower() for z in settings.PORTAL_ZNACZNIKI if z.strip()]
    tekst = f"{nadawca} {temat}".lower()
    return any(z in tekst for z in znaczniki)


def przetworz_wiadomosc(surowa: bytes) -> Wplyw | None:
    """Zamienia jedną wiadomość e-mail na wpływ (albo None, jeśli nieistotna/duplikat)."""
    msg = email.message_from_bytes(surowa, policy=polityka)
    msg_id = (msg.get("Message-ID") or "").strip()
    temat = str(msg.get("Subject") or "(bez tematu)")
    nadawca = str(msg.get("From") or "")
    try:
        data = parsedate_to_datetime(msg["Date"]).date()
    except (TypeError, ValueError):
        data = date.today()
    if not msg_id:
        msg_id = f"brak-id:{nadawca}:{temat}:{msg.get('Date')}"
    if Wplyw.objects.filter(zewn_id=msg_id).exists():
        return None

    tresc = _tekst(msg)
    z_portalu = czy_z_portalu(nadawca, temat)
    sprawa, sygn = dopasuj_sprawe(f"{temat}\n{tresc}")
    if not (z_portalu or sprawa):
        return None
    return Wplyw.objects.create(
        zrodlo=Wplyw.Zrodlo.PORTAL if z_portalu else Wplyw.Zrodlo.POCZTA,
        rodzaj=Wplyw.Rodzaj.POWIADOMIENIE if z_portalu else Wplyw.Rodzaj.EMAIL,
        zewn_id=msg_id[:300], data=data, tytul=temat[:300], tresc=tresc[:MAKS_TRESC],
        nadawca=nadawca[:200], sygnatura=sygn, sprawa=sprawa,
    )


def sprawdz_poczte() -> list[Wplyw]:
    """Łączy się z serwerem IMAP i pobiera wiadomości z ostatnich IMAP_DNI dni."""
    if not settings.IMAP_HOST or not settings.IMAP_USER:
        raise RuntimeError("Brak konfiguracji poczty (IMAP_HOST, IMAP_USER, IMAP_HASLO w pliku .env).")
    nowe = []
    od = (date.today() - timedelta(days=settings.IMAP_DNI)).strftime("%d-%b-%Y")
    with imaplib.IMAP4_SSL(settings.IMAP_HOST, settings.IMAP_PORT) as imap:
        imap.login(settings.IMAP_USER, settings.IMAP_HASLO)
        for folder in settings.IMAP_FOLDERY:
            typ, _ = imap.select(f'"{folder}"', readonly=True)
            if typ != "OK":
                log.warning("Nie ma folderu %s", folder)
                continue
            _, dane = imap.search(None, "SINCE", od)
            for num in dane[0].split():
                _, czesci = imap.fetch(num, "(BODY.PEEK[])")
                surowa = next((c[1] for c in czesci if isinstance(c, tuple)), None)
                if surowa:
                    try:
                        w = przetworz_wiadomosc(surowa)
                    except Exception:  # jedna zła wiadomość nie może zatrzymać reszty
                        log.exception("Błąd przetwarzania wiadomości %s w %s", num, folder)
                        continue
                    if w:
                        nowe.append(w)
    return nowe
