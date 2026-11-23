from django.core.management.base import BaseCommand

from sprawy.poczta import sprawdz_poczte


class Command(BaseCommand):
    help = "Sprawdza skrzynkę IMAP i dodaje nowe wpływy (tylko odczyt skrzynki)"

    def handle(self, *args, **opts):
        nowe = sprawdz_poczte()
        for w in nowe:
            self.stdout.write(f"+ [{w.sprawa.numer if w.sprawa else '?'}] {w.tytul}")
        self.stdout.write(self.style.SUCCESS(f"Nowych wpływów: {len(nowe)}"))
