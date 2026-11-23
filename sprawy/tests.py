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
            "sprawa": self.sprawa.pk, "preset": "kpc_apelacja", "zdarzenie": "portal", "data": "2026-11-02", "oblicz": "1",
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


# ------------------------------------------------------------------ Etap 2 ---
from email.message import EmailMessage
from unittest import mock

from django.core import mail

from .models import Postepowanie, Wplyw
from .poczta import przetworz_wiadomosc, sprawdz_poczte
from .portal import ZdarzeniePortalu, zapisz_zdarzenia
from .raport import tresc_raportu
from .sygnatury import dopasuj_sprawe, normalizuj, znajdz_sygnatury


def eml(temat, tresc, nadawca="sad@example.pl", msg_id="<1@x>", html=False):
    m = EmailMessage()
    m["Subject"], m["From"], m["To"] = temat, nadawca, "kancelaria@example.pl"
    m["Message-ID"], m["Date"] = msg_id, "Mon, 23 Nov 2026 08:15:00 +0100"
    if html:
        m.set_content("<p>" + tresc + "</p>", subtype="html")
    else:
        m.set_content(tresc)
    return m.as_bytes()


class SygnaturyTest(TestCase):
    def test_rozpoznawanie(self):
        t = "W sprawie III RC 120/26 oraz I ACa 1234/2025; postępowanie PR 2 Ds. 345.2026 i II K 77/26."
        self.assertEqual(znajdz_sygnatury(t), ["III RC 120/26", "I ACa 1234/2025", "II K 77/26", "PR 2 Ds. 345.2026"])

    def test_normalizacja(self):
        self.assertEqual(normalizuj("I C 123 / 2026"), normalizuj("i c 123/26"))
        self.assertNotEqual(normalizuj("I C 123/26"), normalizuj("I C 123/25"))


class PocztaTest(DaneMixin, TestCase):
    def setUp(self):
        super().setUp()
        Postepowanie.objects.create(sprawa=self.sprawa, organ="SO", sygnatura="I C 123/26")

    def test_dopasowanie(self):
        s, sygn = dopasuj_sprawe("Zawiadomienie w sprawie I C 123/2026")
        self.assertEqual((s, sygn), (self.sprawa, "I C 123/2026"))

    def test_mail_z_sygnatura_trafia_do_sprawy(self):
        w = przetworz_wiadomosc(eml("Odpowiedź na pozew – I C 123/26", "W załączeniu…", "pelnomocnik@x.pl"))
        self.assertEqual((w.sprawa, w.zrodlo, w.data), (self.sprawa, "poczta", date(2026, 11, 23)))

    def test_mail_bez_sygnatury_pomijany(self):
        self.assertIsNone(przetworz_wiadomosc(eml("Newsletter", "Promocja!")))

    def test_powiadomienie_portalu_html(self):
        w = przetworz_wiadomosc(eml("Portal Informacyjny – nowe zdarzenie", "Sprawa <b>I C 123/26</b><br>Nowy dokument",
                                    "powiadomienia@portal-informacyjny.example", html=True))
        self.assertEqual((w.zrodlo, w.rodzaj, w.sprawa), ("portal", "powiadomienie", self.sprawa))
        self.assertIn("Nowy dokument", w.tresc)
        self.assertNotIn("<b>", w.tresc)

    def test_powiadomienie_portalu_nieznana_sprawa(self):
        w = przetworz_wiadomosc(eml("Portal informacyjny", "Sprawa IV RC 9/26", "noreply@portal-informacyjny.example"))
        self.assertIsNone(w.sprawa)
        self.assertEqual(w.sygnatura, "IV RC 9/26")

    def test_duplikaty(self):
        przetworz_wiadomosc(eml("I C 123/26", "x"))
        self.assertIsNone(przetworz_wiadomosc(eml("I C 123/26", "x")))

    @override_settings(IMAP_HOST="imap.test", IMAP_USER="u", IMAP_HASLO="p", IMAP_FOLDERY=["INBOX"])
    def test_imap_tylko_do_odczytu(self):
        with mock.patch("sprawy.poczta.imaplib.IMAP4_SSL") as klasa:
            imap = klasa.return_value.__enter__.return_value
            imap.select.return_value = ("OK", [b"1"])
            imap.search.return_value = ("OK", [b"1 2"])
            imap.fetch.side_effect = [("OK", [(b"1", eml("I C 123/26 pismo", "x", msg_id="<a@x>"))]),
                                      ("OK", [(b"2", eml("spam", "x", msg_id="<b@x>"))])]
            nowe = sprawdz_poczte()
        self.assertEqual(len(nowe), 1)
        imap.select.assert_called_with('"INBOX"', readonly=True)
        for c in imap.fetch.call_args_list:
            self.assertIn("PEEK", c.args[1])
        imap.store.assert_not_called()


class PortalTest(DaneMixin, TestCase):
    def test_zapis_zdarzen_bez_duplikatow(self):
        Postepowanie.objects.create(sprawa=self.sprawa, organ="SR", sygnatura="III RC 5/26")
        z = [ZdarzeniePortalu("III RC 5/26", Wplyw.Rodzaj.CZYNNOSC, date(2026, 11, 20), "Wyznaczono termin", "c1"),
             ZdarzeniePortalu("III RC 5/26", Wplyw.Rodzaj.DORECZENIE, date(2026, 11, 21), "Postanowienie", "d1")]
        self.assertEqual(len(zapisz_zdarzenia(z)), 2)
        self.assertEqual(len(zapisz_zdarzenia(z)), 0)
        self.assertEqual(Wplyw.objects.filter(sprawa=self.sprawa).count(), 2)


class WplywyWidokTest(DaneMixin, TestCase):
    def test_przyjecie_do_chronologii_i_kalkulator(self):
        w = Wplyw.objects.create(zrodlo="portal", rodzaj="doreczenie", zewn_id="p:1", data=date(2026, 11, 2),
                                 tytul="Wyrok z uzasadnieniem", sprawa=self.sprawa)
        self.assertContains(self.client.get(reverse("wplywy")), "Wyrok z uzasadnieniem")
        r = self.client.post(reverse("wplyw_akcja", args=[w.pk]), {"akcja": "termin"})
        self.assertIn("zdarzenie=portal", r.url)
        self.assertIn("data=2026-11-02", r.url)
        w.refresh_from_db()
        self.assertEqual(w.status, "przyjety")
        self.assertEqual(w.czynnosc.sprawa, self.sprawa)
        # kalkulator otwiera się wypełniony, ale nie liczy przed kliknięciem „Oblicz”
        r = self.client.get(r.url)
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, "Wybierz rodzaj terminu")

    def test_nieprzypisany_wymaga_sprawy(self):
        w = Wplyw.objects.create(zrodlo="poczta", zewn_id="m:1", data=date.today(), tytul="X")
        self.client.post(reverse("wplyw_akcja", args=[w.pk]), {"akcja": "przyjmij"})
        w.refresh_from_db()
        self.assertEqual(w.status, "nowy")
        self.client.post(reverse("wplyw_akcja", args=[w.pk]), {"akcja": "przyjmij", "sprawa": self.sprawa.pk})
        w.refresh_from_db()
        self.assertEqual((w.status, w.sprawa), ("przyjety", self.sprawa))

    def test_pominiecie(self):
        w = Wplyw.objects.create(zrodlo="poczta", zewn_id="m:2", data=date.today(), tytul="X")
        self.client.post(reverse("wplyw_akcja", args=[w.pk]), {"akcja": "pomin"})
        w.refresh_from_db()
        self.assertEqual(w.status, "pominiety")
        self.assertFalse(Czynnosc.objects.exists())


class RaportTest(DaneMixin, TestCase):
    def test_tresc_i_wysylka(self):
        Termin.objects.create(sprawa=self.sprawa, opis="Apelacja", data=date.today() - timedelta(days=1))
        Wplyw.objects.create(zrodlo="portal", rodzaj="doreczenie", zewn_id="p:9", data=date.today(), tytul="Wyrok")
        temat, tresc = tresc_raportu()
        self.assertIn("po terminie", temat)
        self.assertIn("DORĘCZENIE", tresc)
        self.assertIn("NIEPRZYPISANY", tresc)
        with override_settings(RAPORT_ODBIORCY=["a@example.pl"]):
            from .raport import wyslij_raport
            wyslij_raport()
        self.assertEqual(len(mail.outbox), 1)
