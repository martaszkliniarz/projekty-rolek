from django.core.management.base import BaseCommand

from sprawy.raport import tresc_raportu, wyslij_raport


class Command(BaseCommand):
    help = "Wysyła poranny raport e-mailem (--podglad: tylko wyświetla)"

    def add_arguments(self, parser):
        parser.add_argument("--podglad", action="store_true")

    def handle(self, *args, podglad=False, **opts):
        if podglad:
            temat, tresc = tresc_raportu()
            self.stdout.write(f"Temat: {temat}\n\n{tresc}")
        else:
            self.stdout.write(self.style.SUCCESS(f"Wysłano: {wyslij_raport()}"))
