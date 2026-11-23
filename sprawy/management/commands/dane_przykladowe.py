"""python manage.py dane_przykladowe — kilka fikcyjnych spraw, żeby obejrzeć program."""
from datetime import date, time, timedelta

from django.core.management.base import BaseCommand

from sprawy.models import Czynnosc, Osoba, Postepowanie, Sprawa, Termin, Uczestnik, Wplyw


class Command(BaseCommand):
    help = "Dodaje fikcyjne sprawy demonstracyjne"

    def handle(self, *args, **opts):
        d = date.today()
        anna = Osoba.objects.create(nazwa="Anna Przykładowa", email="anna@example.com", telefon="600 000 001",
                                    preferowany_kontakt="e-mail")
        jan = Osoba.objects.create(nazwa="Jan Przykładowy")
        s1 = Sprawa.objects.create(tytul="Przykładowa – rozwód z orzekaniem o winie", klient=anna,
                                   rola_klienta="powódka", dziedzina="rodzinna", rozliczenie="godzinowe",
                                   stawka_godzinowa=300, data_przyjecia=d - timedelta(days=120),
                                   opis="Pozew złożony. Sąd wyznaczył rozprawę. Klientka chce wyłącznej władzy "
                                        "rodzicielskiej i alimentów na syna (8 lat).")
        Postepowanie.objects.create(sprawa=s1, organ="Sąd Okręgowy, I Wydział Cywilny", sygnatura="I C 123/26",
                                    instancja="I instancja")
        Uczestnik.objects.create(sprawa=s1, osoba=jan, rola="pozwany", strona_przeciwna=True,
                                 pelnomocnik="r.pr. (fikcyjny)")
        Termin.objects.create(sprawa=s1, rodzaj="rozprawa", opis="Rozprawa — przesłuchanie stron",
                              data=d + timedelta(days=5), godzina=time(10, 30), miejsce="sala 214")
        Termin.objects.create(sprawa=s1, rodzaj="procesowy", opis="Pismo przygotowawcze (zobowiązanie sądu)",
                              data=d + timedelta(days=2), podstawa="zarządzenie sądu")
        for i, (opis, typ, m) in enumerate([("Pierwsze spotkanie z klientką", "rozmowa", 90),
                                            ("Projekt pozwu rozwodowego", "pismo", 240),
                                            ("Analiza odpowiedzi na pozew", "akta", 60)]):
            Czynnosc.objects.create(sprawa=s1, opis=opis, typ=typ, czas_min=m, data=d - timedelta(days=100 - i * 30))

        tomasz = Osoba.objects.create(nazwa="Tomasz Fikcyjny", telefon="600 000 002")
        s2 = Sprawa.objects.create(tytul="Fikcyjny – art. 286 KK (obrona)", klient=tomasz, rola_klienta="oskarżony",
                                   dziedzina="karna", rozliczenie="ryczalt", wynagrodzenie_ryczalt=6000,
                                   data_przyjecia=d - timedelta(days=40))
        Postepowanie.objects.create(sprawa=s2, organ="Sąd Rejonowy, II Wydział Karny", sygnatura="II K 456/26")
        Termin.objects.create(sprawa=s2, rodzaj="procesowy", opis="Apelacja od wyroku",
                              data=d - timedelta(days=1), podstawa="art. 445 § 1 KPK")
        Czynnosc.objects.create(sprawa=s2, opis="Przegląd akt w czytelni sądu", typ="akta", czas_min=180,
                                data=d - timedelta(days=10))
        Czynnosc.objects.create(sprawa=s2, opis="Wpłynęło zawiadomienie o terminie (portal) — propozycja asystenta",
                                typ="wplyw", zrodlo="asystent", potwierdzona=False, czas_min=0, data=d)
        Wplyw.objects.create(zrodlo="portal", rodzaj="doreczenie", zewn_id="demo:1", data=d - timedelta(days=1),
                             tytul="Wyrok z uzasadnieniem", sygnatura="II K 456/26", sprawa=s2)
        Wplyw.objects.create(zrodlo="portal", rodzaj="czynnosc", zewn_id="demo:2", data=d,
                             tytul="Zarządzenie o wyznaczeniu terminu rozprawy", sygnatura="I C 123/26", sprawa=s1)
        Wplyw.objects.create(zrodlo="poczta", rodzaj="email", zewn_id="demo:3", data=d,
                             nadawca="kancelaria-przeciwnika@example.com", tytul="Propozycja ugody – III RC 77/26",
                             tresc="Szanowna Pani Mecenas, w imieniu mojego klienta…", sygnatura="III RC 77/26")
        self.stdout.write(self.style.SUCCESS("Dodano dane przykładowe."))
