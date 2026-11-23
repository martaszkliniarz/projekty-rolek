from datetime import date, time, timedelta

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from .ics import kalendarz_ics
from .models import Czynnosc, Osoba, Sprawa, Termin, Uczestnik
from .terminy import (doreczenie_awizo, doreczenie_portal, jest_dniem_roboczym, oblicz_termin,
                      swieta, wielkanoc)


class SwietaTest(TestCase):
    def test_wielkanoc(self):
        self.assertEqual(wielkanoc(2025), date(2025, 4, 20))
        self.assertEqual(wielkanoc(2026), date(2026, 4, 5))
        self.assertEqual(wielkanoc(2027), date(2027, 3, 28))

    def test_swieta_ruchome_2026(self):
        s = swieta(2026)
        self.assertIn(date(2026, 4, 6), s)   # Poniedziałek Wielkanocny
        self.assertIn(date(2026, 5, 24), s)  # Zielone Świątki
        self.assertIn(date(2026, 6, 4), s)   # Boże Ciało

    def test_wigilia_wolna_od_2025(self):
        self.assertNotIn(date(2024, 12, 24), swieta(2024))
        self.assertIn(date(2025, 12, 24), swieta(2025))

    def test_dni_robocze(self):
        self.assertTrue(jest_dniem_roboczym(date(2026, 11, 23)))   # poniedziałek
        self.assertFalse(jest_dniem_roboczym(date(2026, 11, 28)))  # sobota
        self.assertFalse(jest_dniem_roboczym(date(2026, 11, 11)))  # święto


class ObliczTerminTest(TestCase):
    def test_dni_bez_przesuniecia(self):
        # doręczenie w poniedziałek 2.11.2026, 7 dni → poniedziałek 9.11
        w = oblicz_termin(date(2026, 11, 2), 7, "dni")
        self.assertEqual(w.koniec, date(2026, 11, 9))
        self.assertFalse(w.przesuniety)

    def test_tydzien_konczy_sie_tym_samym_dniem(self):
        w = oblicz_termin(date(2026, 11, 18), 2, "tygodnie")  # środa
        self.assertEqual(w.koniec, date(2026, 12, 2))           # środa

    def test_przesuniecie_z_soboty(self):
        w = oblicz_termin(date(2026, 11, 14), 14, "dni")  # sobota + 14 = sobota 28.11
        self.assertEqual(w.koniec_nominalny, date(2026, 11, 28))
        self.assertEqual(w.koniec, date(2026, 11, 30))  # poniedziałek
        self.assertTrue(w.przesuniety)

    def test_przesuniecie_przez_swieta(self):
        # koniec nominalny 24.12.2026 (Wigilia) → 25, 26, 27 wolne → 28.12
        w = oblicz_termin(date(2026, 12, 17), 7, "dni")
        self.assertEqual(w.koniec, date(2026, 12, 28))

    def test_przesuniecie_przez_wielkanoc(self):
        w = oblicz_termin(date(2026, 3, 28), 1, "tygodnie")  # → sobota 4.04
        self.assertEqual(w.koniec, date(2026, 4, 7))          # 4 sob, 5 ndz, 6 pon. Wlk.

    def test_miesiace_koniec_miesiaca(self):
        w = oblicz_termin(date(2026, 12, 31), 2, "miesiace")  # 28.02.2027 = niedziela
        self.assertEqual(w.koniec_nominalny, date(2027, 2, 28))
        self.assertEqual(w.koniec, date(2027, 3, 1))

    def test_lata(self):
        self.assertEqual(oblicz_termin(date(2024, 2, 29), 1, "lata").koniec_nominalny, date(2025, 2, 28))


class DoreczeniaTest(TestCase):
    def test_portal_fikcja(self):
        d, _ = doreczenie_portal(date(2026, 11, 2))
        self.assertEqual(d, date(2026, 11, 16))

    def test_portal_otwarcie(self):
        d, _ = doreczenie_portal(date(2026, 11, 2), date(2026, 11, 5))
        self.assertEqual(d, date(2026, 11, 5))

    def test_portal_otwarcie_po_fikcji_nie_przesuwa(self):
        d, _ = doreczenie_portal(date(2026, 11, 2), date(2026, 11, 20))
        self.assertEqual(d, date(2026, 11, 16))

    def test_awizo(self):
        self.assertEqual(doreczenie_awizo(date(2026, 11, 2))[0], date(2026, 11, 16))


class DaneMixin:
    def setUp(self):
        self.user = User.objects.create_user("adwokat", password="tajne-haslo-123")
        self.klient = Osoba.objects.create(nazwa="Anna Kowalska", pesel="85010112345")
        self.sprawa = Sprawa.objects.create(tytul="Kowalska – rozwód", klient=self.klient,
                                            rola_klienta="powódka", data_przyjecia=date(2026, 3, 1))
        self.client.login(username="adwokat", password="tajne-haslo-123")


class ModeleTest(DaneMixin, TestCase):
    def test_numeracja_spraw(self):
        self.assertEqual(self.sprawa.numer, "2026/001")
        s2 = Sprawa.objects.create(tytul="druga", klient=self.klient, data_przyjecia=date(2026, 5, 1))
        self.assertEqual(s2.numer, "2026/002")

    def test_suma_czasu(self):
        Czynnosc.objects.create(sprawa=self.sprawa, opis="pozew", czas_min=150)
        Czynnosc.objects.create(sprawa=self.sprawa, opis="rozmowa", czas_min=45)
        self.assertEqual(self.sprawa.czas_minuty(), 195)


class WidokiTest(DaneMixin, TestCase):
    def test_wymaga_logowania(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("pulpit")).status_code, 302)

    def test_strony_dzialaja(self):
        Termin.objects.create(sprawa=self.sprawa, opis="Apelacja", data=date.today() + timedelta(days=3))
        Termin.objects.create(sprawa=self.sprawa, opis="Zaległy", data=date.today() - timedelta(days=2))
        for nazwa, args in [("pulpit", []), ("lista_spraw", []), ("sprawa", [self.sprawa.pk]),
                            ("terminy", []), ("kalkulator", []), ("raport_czasu", [])]:
            r = self.client.get(reverse(nazwa, args=args))
            self.assertEqual(r.status_code, 200, nazwa)
        self.assertContains(self.client.get(reverse("pulpit")), "2 dni po terminie")

    def test_karta_sprawy_z_wpisem_asystenta(self):
        Czynnosc.objects.create(sprawa=self.sprawa, opis="wpływ z portalu", zrodlo="asystent", potwierdzona=False)
        r = self.client.get(reverse("sprawa", args=[self.sprawa.pk]))
        self.assertContains(r, "do potwierdzenia")

    def test_dodanie_czynnosci_z_czasem(self):
        r = self.client.post(reverse("sprawa", args=[self.sprawa.pk]), {
            "dodaj_czynnosc": "1", "c-data": "2026-11-20", "c-typ": "pismo",
            "c-opis": "Projekt pozwu", "c-godziny": "2", "c-minuty": "30", "c-rozliczalna": "on",
        })
        self.assertEqual(r.status_code, 302)
        c = Czynnosc.objects.get()
        self.assertEqual((c.czas_min, c.wykonal), (150, self.user))

    def test_kalkulator_i_zapis_terminu(self):
        r = self.client.get(reverse("kalkulator"), {
            "sprawa": self.sprawa.pk, "preset": "kpc_apelacja", "zdarzenie": "portal", "data": "2026-11-02",
        })
        # portal 2.11 → doręczenie 16.11 → +2 tyg. = 30.11.2026
        self.assertContains(r, "30.11.2026")
        r = self.client.post(reverse("sprawa", args=[self.sprawa.pk]), {
            "dodaj_termin": "1", "t-data": "2026-11-30", "t-rodzaj": "procesowy",
            "t-opis": "Apelacja", "t-podstawa": "art. 369 § 1 KPC", "t-wyliczenie": "x",
        })
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Termin.objects.get().data, date(2026, 11, 30))

    def test_oznaczenie_wykonania(self):
        t = Termin.objects.create(sprawa=self.sprawa, opis="X", data=date.today())
        self.client.post(reverse("termin_status", args=[t.pk]), {"status": "wykonany"})
        t.refresh_from_db()
        self.assertEqual((t.status, t.wykonano), ("wykonany", date.today()))

    def test_csv(self):
        Czynnosc.objects.create(sprawa=self.sprawa, opis="pozew", czas_min=90, data=date.today())
        r = self.client.get(reverse("raport_czasu"), {"format": "csv"})
        self.assertIn("pozew", r.content.decode())


class KalendarzTest(DaneMixin, TestCase):
    def test_ics_anonimowy(self):
        Termin.objects.create(sprawa=self.sprawa, opis="Rozprawa", rodzaj="rozprawa",
                              data=date(2026, 12, 3), godzina=time(10, 30), miejsce="sala 12")
        ics = kalendarz_ics(Termin.objects.all())
        self.assertIn("DTSTART;TZID=Europe/Warsaw:20261203T103000", ics)
        self.assertNotIn("Kowalska", ics)
        self.assertIn("Kowalska", kalendarz_ics(Termin.objects.all(), anonimowy=False))

    @override_settings(KALENDARZ_TOKEN="sekret123")
    def test_token(self):
        self.client.logout()
        self.assertEqual(self.client.get("/kalendarz/zly.ics").status_code, 404)
        r = self.client.get("/kalendarz/sekret123.ics")
        self.assertEqual(r.status_code, 200)
        self.assertIn("BEGIN:VCALENDAR", r.content.decode())

    @override_settings(KALENDARZ_TOKEN="")
    def test_brak_tokenu_wylacza(self):
        self.assertEqual(self.client.get("/kalendarz/.ics").status_code, 404)
