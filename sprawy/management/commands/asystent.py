"""
Asystent działający w tle (na serwerze): co kilkanaście minut sprawdza pocztę,
a raz dziennie o ustalonej godzinie wysyła poranny raport.
Uruchomienie:  python manage.py asystent
"""
import time
from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import close_old_connections

from sprawy.poczta import sprawdz_poczte
from sprawy.raport import wyslij_raport


class Command(BaseCommand):
    help = "Asystent w tle: poczta co ASYSTENT_CO_MINUT min, raport o RAPORT_GODZINA"

    def handle(self, *args, **opts):
        ostatni_raport = None
        self.stdout.write("Asystent uruchomiony.")
        while True:
            close_old_connections()
            teraz = datetime.now()
            if settings.IMAP_HOST:
                try:
                    nowe = sprawdz_poczte()
                    if nowe:
                        self.stdout.write(f"{teraz:%H:%M} nowe wpływy: {len(nowe)}")
                except Exception as e:  # serwer poczty chwilowo niedostępny itp.
                    self.stderr.write(f"{teraz:%H:%M} błąd poczty: {e}")
            if (settings.RAPORT_ODBIORCY and teraz.strftime("%H:%M") >= settings.RAPORT_GODZINA
                    and teraz.weekday() < 5 and ostatni_raport != teraz.date()):
                try:
                    wyslij_raport()
                    ostatni_raport = teraz.date()
                    self.stdout.write(f"{teraz:%H:%M} wysłano raport")
                except Exception as e:
                    self.stderr.write(f"{teraz:%H:%M} błąd wysyłki raportu: {e}")
            time.sleep(settings.ASYSTENT_CO_MINUT * 60)
