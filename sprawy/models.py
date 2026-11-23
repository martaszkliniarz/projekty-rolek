import uuid
from datetime import date

from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.urls import reverse


class Osoba(models.Model):
    """Każda osoba lub podmiot: klient, strona przeciwna, świadek, pokrzywdzony…"""

    class Typ(models.TextChoices):
        FIZYCZNA = "fizyczna", "osoba fizyczna"
        PRAWNA = "prawna", "osoba prawna / instytucja"

    typ = models.CharField(max_length=10, choices=Typ.choices, default=Typ.FIZYCZNA)
    nazwa = models.CharField("imię i nazwisko / nazwa", max_length=200)
    nazwisko_rodowe = models.CharField(max_length=100, blank=True)
    pesel = models.CharField("PESEL", max_length=11, blank=True)
    nip = models.CharField("NIP", max_length=13, blank=True)
    email = models.EmailField(blank=True)
    telefon = models.CharField(max_length=30, blank=True)
    adres = models.TextField(blank=True)
    preferowany_kontakt = models.CharField(max_length=50, blank=True, help_text="np. e-mail, telefon po 17:00")
    notatki = models.TextField(blank=True)
    utworzono = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "osoba"
        verbose_name_plural = "osoby"
        ordering = ["nazwa"]

    def __str__(self):
        return self.nazwa


class Sprawa(models.Model):
    class Dziedzina(models.TextChoices):
        RODZINNA = "rodzinna", "rodzinna"
        KARNA = "karna", "karna"
        WYKROCZENIOWA = "wykroczeniowa", "wykroczeniowa"
        CYWILNA = "cywilna", "cywilna"
        INNA = "inna", "inna"

    class Status(models.TextChoices):
        AKTYWNA = "aktywna", "aktywna"
        ZAWIESZONA = "zawieszona", "zawieszona"
        ZAKONCZONA = "zakonczona", "zakończona"
        ARCHIWUM = "archiwum", "w archiwum"

    class Rozliczenie(models.TextChoices):
        GODZINOWE = "godzinowe", "godzinowe"
        RYCZALT = "ryczalt", "ryczałt"
        RYCZALT_SUCCESS = "ryczalt_success", "ryczałt + premia za wynik"
        Z_URZEDU = "z_urzedu", "z urzędu"
        PRO_BONO = "pro_bono", "pro bono"

    numer = models.CharField("nr wewnętrzny", max_length=20, unique=True, blank=True,
                             help_text="Nadawany automatycznie, np. 2026/014")
    tytul = models.CharField("nazwa sprawy", max_length=200, help_text="np. Kowalska – rozwód")
    dziedzina = models.CharField(max_length=15, choices=Dziedzina.choices, default=Dziedzina.RODZINNA)
    klient = models.ForeignKey(Osoba, on_delete=models.PROTECT, related_name="sprawy_klienta")
    rola_klienta = models.CharField(max_length=60, blank=True,
                                    help_text="np. powódka, wnioskodawca, oskarżony, pokrzywdzona")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.AKTYWNA)
    data_przyjecia = models.DateField(default=date.today)
    data_zakonczenia = models.DateField(null=True, blank=True)
    opis = models.TextField("stan sprawy / streszczenie", blank=True,
                            help_text="Krótkie streszczenie — co jest istotą sprawy, cel klienta.")
    strategia = models.TextField(blank=True)
    rozliczenie = models.CharField(max_length=16, choices=Rozliczenie.choices, default=Rozliczenie.RYCZALT)
    stawka_godzinowa = models.DecimalField("stawka godzinowa (zł netto)", max_digits=8,
                                           decimal_places=2, null=True, blank=True)
    wynagrodzenie_ryczalt = models.DecimalField("ryczałt (zł netto)", max_digits=10,
                                                decimal_places=2, null=True, blank=True)
    prowadzacy = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name="sprawy")
    utworzono = models.DateTimeField(auto_now_add=True)
    zmieniono = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "sprawa"
        verbose_name_plural = "sprawy"
        ordering = ["-data_przyjecia", "-id"]

    def __str__(self):
        return f"{self.numer} {self.tytul}"

    def save(self, *args, **kwargs):
        if not self.numer:
            rok = (self.data_przyjecia or date.today()).year
            n = Sprawa.objects.filter(numer__startswith=f"{rok}/").count() + 1
            while Sprawa.objects.filter(numer=f"{rok}/{n:03d}").exists():
                n += 1
            self.numer = f"{rok}/{n:03d}"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("sprawa", args=[self.pk])

    @property
    def tryb(self):
        return "KPK" if self.dziedzina in (self.Dziedzina.KARNA, self.Dziedzina.WYKROCZENIOWA) else "KPC"

    def czas_minuty(self):
        return self.czynnosci.aggregate(s=Sum("czas_min"))["s"] or 0

    def sygnatury(self):
        return ", ".join(p.sygnatura for p in self.postepowania.all() if p.sygnatura)


class Postepowanie(models.Model):
    """Konkretne postępowanie w sprawie — sąd/prokuratura, sygnatura, instancja.
    Jedna sprawa klienta może mieć kilka (np. I i II instancja, zabezpieczenie)."""

    sprawa = models.ForeignKey(Sprawa, on_delete=models.CASCADE, related_name="postepowania")
    organ = models.CharField("sąd / prokuratura / policja", max_length=200,
                             help_text="np. Sąd Rejonowy dla Krakowa-Śródmieścia, IV Wydział Rodzinny i Nieletnich")
    sygnatura = models.CharField(max_length=60, blank=True)
    instancja = models.CharField(max_length=40, blank=True, help_text="np. I instancja, apelacja, postępowanie przygotowawcze")
    referent = models.CharField("sędzia / prokurator referent", max_length=120, blank=True)
    aktywne = models.BooleanField(default=True)

    class Meta:
        verbose_name = "postępowanie"
        verbose_name_plural = "postępowania"

    def __str__(self):
        return f"{self.sygnatura or '(bez sygn.)'} – {self.organ}"


class Uczestnik(models.Model):
    """Pozostałe osoby w sprawie (strona przeciwna, małoletni, świadkowie…)."""

    sprawa = models.ForeignKey(Sprawa, on_delete=models.CASCADE, related_name="uczestnicy")
    osoba = models.ForeignKey(Osoba, on_delete=models.PROTECT, related_name="udzialy")
    rola = models.CharField(max_length=80, help_text="np. pozwany, małoletni syn, pokrzywdzony, świadek")
    pelnomocnik = models.CharField("pełnomocnik / obrońca", max_length=200, blank=True)
    strona_przeciwna = models.BooleanField(default=False)

    class Meta:
        verbose_name = "uczestnik sprawy"
        verbose_name_plural = "uczestnicy sprawy"

    def __str__(self):
        return f"{self.osoba} ({self.rola})"


class Termin(models.Model):
    class Rodzaj(models.TextChoices):
        PROCESOWY = "procesowy", "termin procesowy"
        ROZPRAWA = "rozprawa", "rozprawa / posiedzenie"
        CZYNNOSC = "czynnosc", "czynność (przesłuchanie, mediacja…)"
        WEWNETRZNY = "wewnetrzny", "termin wewnętrzny / zadanie"
        PRZEDAWNIENIE = "przedawnienie", "przedawnienie"
        ARESZT = "areszt", "koniec tymczasowego aresztowania"
        SPOTKANIE = "spotkanie", "spotkanie z klientem"

    class Status(models.TextChoices):
        OTWARTY = "otwarty", "do zrobienia"
        WYKONANY = "wykonany", "wykonany"
        ANULOWANY = "anulowany", "nieaktualny"

    sprawa = models.ForeignKey(Sprawa, on_delete=models.CASCADE, related_name="terminy")
    rodzaj = models.CharField(max_length=15, choices=Rodzaj.choices, default=Rodzaj.PROCESOWY)
    opis = models.CharField(max_length=250)
    data = models.DateField()
    godzina = models.TimeField(null=True, blank=True)
    miejsce = models.CharField(max_length=200, blank=True, help_text="np. sala 214 / rozprawa zdalna")
    podstawa = models.CharField("podstawa prawna", max_length=120, blank=True)
    wyliczenie = models.TextField("sposób wyliczenia", blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OTWARTY)
    przypisany = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name="terminy")
    wykonano = models.DateField(null=True, blank=True)
    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    utworzono = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "termin"
        verbose_name_plural = "terminy"
        ordering = ["data", "godzina"]

    def __str__(self):
        return f"{self.data:%d.%m.%Y} {self.opis}"

    @property
    def dni_do(self):
        return (self.data - date.today()).days

    @property
    def dni_po(self):
        return -self.dni_do

    @property
    def pilnosc(self):
        if self.status != self.Status.OTWARTY:
            return "zamkniety"
        d = self.dni_do
        if d < 0:
            return "po-terminie"
        if d <= 1:
            return "pilne"
        if d <= 7:
            return "wkrotce"
        return "pozniej"


class Czynnosc(models.Model):
    """Chronologia sprawy: co zostało zrobione i ile czasu to zajęło."""

    class Typ(models.TextChoices):
        ROZMOWA = "rozmowa", "rozmowa / spotkanie z klientem"
        PISMO = "pismo", "sporządzenie pisma"
        ROZPRAWA = "rozprawa", "udział w rozprawie / czynności"
        AKTA = "akta", "przegląd akt / analiza"
        KORESPONDENCJA = "korespondencja", "korespondencja"
        DOJAZD = "dojazd", "dojazd"
        WPLYW = "wplyw", "wpływ pisma / doręczenie"
        NOTATKA = "notatka", "notatka"
        INNE = "inne", "inne"

    class Zrodlo(models.TextChoices):
        RECZNIE = "recznie", "wpis ręczny"
        ASYSTENT = "asystent", "asystent AI (do potwierdzenia)"
        PORTAL = "portal", "portal informacyjny"
        POCZTA = "poczta", "poczta e-mail"

    sprawa = models.ForeignKey(Sprawa, on_delete=models.CASCADE, related_name="czynnosci")
    data = models.DateField(default=date.today)
    typ = models.CharField(max_length=15, choices=Typ.choices, default=Typ.INNE)
    opis = models.TextField()
    czas_min = models.PositiveIntegerField("czas (minuty)", default=0)
    rozliczalna = models.BooleanField(default=True)
    wykonal = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                null=True, blank=True, related_name="czynnosci")
    zrodlo = models.CharField(max_length=10, choices=Zrodlo.choices, default=Zrodlo.RECZNIE)
    potwierdzona = models.BooleanField(default=True,
                                       help_text="Wpisy asystenta AI czekają na potwierdzenie.")
    utworzono = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "czynność"
        verbose_name_plural = "czynności (chronologia i czas)"
        ordering = ["-data", "-utworzono"]

    def __str__(self):
        return f"{self.data:%d.%m.%Y} {self.opis[:60]}"

    @property
    def czas_txt(self):
        return format_czas(self.czas_min)


def sciezka_dokumentu(instance, filename):
    return f"sprawy/{instance.sprawa.numer.replace('/', '-')}/{filename}"


class Dokument(models.Model):
    sprawa = models.ForeignKey(Sprawa, on_delete=models.CASCADE, related_name="dokumenty")
    nazwa = models.CharField(max_length=200)
    plik = models.FileField(upload_to=sciezka_dokumentu, blank=True)
    data = models.DateField("data wpływu / sporządzenia", default=date.today)
    opis = models.TextField(blank=True)

    class Meta:
        verbose_name = "dokument"
        verbose_name_plural = "dokumenty"
        ordering = ["-data"]

    def __str__(self):
        return self.nazwa


class Wplyw(models.Model):
    """Skrzynka wpływów: wszystko, co asystent znalazł w poczcie i w portalu.
    Po przejrzeniu wpływ trafia do chronologii sprawy (albo zostaje pominięty)."""

    class Zrodlo(models.TextChoices):
        POCZTA = "poczta", "poczta e-mail"
        PORTAL = "portal", "portal informacyjny"

    class Rodzaj(models.TextChoices):
        EMAIL = "email", "e-mail"
        POWIADOMIENIE = "powiadomienie", "powiadomienie z portalu"
        CZYNNOSC = "czynnosc", "czynność w sprawie (portal)"
        DOKUMENT = "dokument", "nowy dokument w aktach (portal)"
        DORECZENIE = "doreczenie", "doręczenie (portal) — uwaga na termin!"

    class Status(models.TextChoices):
        NOWY = "nowy", "nowy"
        PRZYJETY = "przyjety", "dodany do chronologii"
        POMINIETY = "pominiety", "pominięty"

    zrodlo = models.CharField(max_length=10, choices=Zrodlo.choices)
    rodzaj = models.CharField(max_length=15, choices=Rodzaj.choices, default=Rodzaj.EMAIL)
    zewn_id = models.CharField("identyfikator źródłowy", max_length=300, unique=True,
                               help_text="Message-ID e-maila lub identyfikator z portalu — chroni przed duplikatami")
    data = models.DateField()
    tytul = models.CharField(max_length=300)
    tresc = models.TextField(blank=True)
    nadawca = models.CharField(max_length=200, blank=True)
    sygnatura = models.CharField("rozpoznana sygnatura", max_length=60, blank=True)
    sprawa = models.ForeignKey(Sprawa, on_delete=models.SET_NULL, null=True, blank=True, related_name="wplywy")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.NOWY)
    czynnosc = models.OneToOneField(Czynnosc, on_delete=models.SET_NULL, null=True, blank=True)
    utworzono = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "wpływ"
        verbose_name_plural = "wpływy (poczta i portal)"
        ordering = ["-data", "-utworzono"]

    def __str__(self):
        return f"{self.data:%d.%m.%Y} {self.tytul}"


class Mediacja(models.Model):
    """Mediacja — osobny rejestr. Kancelaria występuje jako mediator albo jako pełnomocnik strony."""

    class Rola(models.TextChoices):
        MEDIATOR = "mediator", "jestem mediatorem"
        PELNOMOCNIK = "pelnomocnik", "jestem pełnomocnikiem strony"

    class Dziedzina(models.TextChoices):
        RODZINNA = "rodzinna", "rodzinna"
        KARNA = "karna", "karna"
        CYWILNA = "cywilna", "cywilna"
        GOSPODARCZA = "gospodarcza", "gospodarcza"
        INNA = "inna", "inna"

    class Podstawa(models.TextChoices):
        SAD = "sad", "skierowanie przez sąd"
        PROKURATOR = "prokurator", "skierowanie przez prokuratora / policję"
        UMOWA = "umowa", "umowa o mediację (prywatna)"

    class Status(models.TextChoices):
        SKIEROWANA = "skierowana", "skierowana / nowa"
        W_TOKU = "w_toku", "w toku"
        ZAKONCZONA = "zakonczona", "zakończona"
        ROZLICZONA = "rozliczona", "zakończona i rozliczona"

    class Wynik(models.TextChoices):
        UGODA = "ugoda", "ugoda"
        CZESCIOWA = "czesciowa", "ugoda częściowa"
        BRAK_UGODY = "brak_ugody", "brak ugody"
        BRAK_ZGODY = "brak_zgody", "brak zgody na mediację"
        REZYGNACJA = "rezygnacja", "rezygnacja / wycofanie strony"

    numer = models.CharField("nr", max_length=20, unique=True, blank=True, help_text="Nadawany automatycznie, np. M/2026/003")
    tytul = models.CharField("nazwa", max_length=200, help_text="np. Nowak / Nowak – kontakty z dzieckiem")
    rola = models.CharField(max_length=12, choices=Rola.choices, default=Rola.MEDIATOR)
    dziedzina = models.CharField(max_length=12, choices=Dziedzina.choices, default=Dziedzina.RODZINNA)
    podstawa = models.CharField(max_length=12, choices=Podstawa.choices, default=Podstawa.SAD)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.SKIEROWANA)

    organ = models.CharField("sąd / prokuratura kierująca", max_length=200, blank=True)
    sygnatura = models.CharField("sygnatura akt", max_length=60, blank=True)
    data_skierowania = models.DateField("data doręczenia skierowania / zawarcia umowy", null=True, blank=True)
    termin_do = models.DateField("termin na przeprowadzenie mediacji", null=True, blank=True,
                                 help_text="Z postanowienia o skierowaniu (w sprawach cywilnych zwykle do 3 miesięcy).")
    przedmiot = models.TextField("przedmiot mediacji", blank=True,
                                 help_text="np. kontakty z małoletnim, alimenty, podział majątku, naprawienie szkody")

    # rola: pełnomocnik
    sprawa = models.ForeignKey(Sprawa, on_delete=models.SET_NULL, null=True, blank=True, related_name="mediacje",
                               help_text="Sprawa klienta, w której toczy się mediacja (gdy jestem pełnomocnikiem).")
    mediator = models.CharField("mediator (imię, nazwisko, kontakt)", max_length=200, blank=True)

    # wynik
    wynik = models.CharField(max_length=12, choices=Wynik.choices, blank=True)
    data_zakonczenia = models.DateField(null=True, blank=True)
    data_protokolu = models.DateField("protokół złożony w sądzie / u prokuratora", null=True, blank=True)
    tresc_ugody = models.TextField("ustalenia / treść ugody", blank=True)

    # rozliczenie (mediator)
    platnik = models.CharField(max_length=120, blank=True, help_text="np. strony po połowie, Skarb Państwa")
    wynagrodzenie = models.DecimalField("wynagrodzenie (zł)", max_digits=10, decimal_places=2, null=True, blank=True)
    wydatki = models.DecimalField("wydatki (zł)", max_digits=10, decimal_places=2, null=True, blank=True)
    data_wniosku_koszty = models.DateField("wniosek o wynagrodzenie / rachunek z dnia", null=True, blank=True)
    data_zaplaty = models.DateField("zapłacono dnia", null=True, blank=True)

    notatki = models.TextField("notatki (poufne)", blank=True)
    utworzono = models.DateTimeField(auto_now_add=True)
    zmieniono = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "mediacja"
        verbose_name_plural = "mediacje"
        ordering = ["-utworzono"]

    def __str__(self):
        return f"{self.numer} {self.tytul}"

    def save(self, *args, **kwargs):
        if not self.numer:
            rok = (self.data_skierowania or date.today()).year
            n = Mediacja.objects.filter(numer__startswith=f"M/{rok}/").count() + 1
            while Mediacja.objects.filter(numer=f"M/{rok}/{n:03d}").exists():
                n += 1
            self.numer = f"M/{rok}/{n:03d}"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("mediacja", args=[self.pk])

    @property
    def aktywna(self):
        return self.status in (self.Status.SKIEROWANA, self.Status.W_TOKU)

    @property
    def dni_do_konca(self):
        return (self.termin_do - date.today()).days if self.termin_do else None

    @property
    def protokol_do_zlozenia(self):
        return (self.rola == self.Rola.MEDIATOR and self.podstawa != self.Podstawa.UMOWA
                and bool(self.wynik) and not self.data_protokolu)

    def czas_minuty(self):
        return ((self.posiedzenia.filter(odbyte=True).aggregate(s=Sum("czas_min"))["s"] or 0)
                + (self.wpisy.aggregate(s=Sum("czas_min"))["s"] or 0))


class StronaMediacji(models.Model):
    mediacja = models.ForeignKey(Mediacja, on_delete=models.CASCADE, related_name="strony")
    osoba = models.ForeignKey(Osoba, on_delete=models.PROTECT, related_name="mediacje")
    rola = models.CharField(max_length=80, help_text="np. wnioskodawczyni, uczestnik, pokrzywdzony, podejrzany")
    pelnomocnik = models.CharField("pełnomocnik", max_length=200, blank=True)
    moj_klient = models.BooleanField("mój klient", default=False, help_text="Gdy jestem pełnomocnikiem tej strony")

    class Meta:
        verbose_name = "strona mediacji"
        verbose_name_plural = "strony mediacji"

    def __str__(self):
        return f"{self.osoba} ({self.rola})"


class Posiedzenie(models.Model):
    class Rodzaj(models.TextChoices):
        WSTEPNE = "wstepne", "spotkanie informacyjne / wstępne"
        WSPOLNE = "wspolne", "posiedzenie wspólne"
        INDYWIDUALNE = "indywidualne", "spotkanie indywidualne"

    mediacja = models.ForeignKey(Mediacja, on_delete=models.CASCADE, related_name="posiedzenia")
    data = models.DateField()
    godzina = models.TimeField(null=True, blank=True)
    rodzaj = models.CharField(max_length=12, choices=Rodzaj.choices, default=Rodzaj.WSPOLNE)
    z_kim = models.CharField("uczestnicy", max_length=200, blank=True, help_text="przy spotkaniu indywidualnym — z kim")
    miejsce = models.CharField(max_length=200, blank=True, help_text="np. kancelaria / online (link)")
    odbyte = models.BooleanField(default=False)
    czas_min = models.PositiveIntegerField("czas (minuty)", default=0)
    notatka = models.TextField("notatka (poufna)", blank=True)
    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        verbose_name = "posiedzenie mediacyjne"
        verbose_name_plural = "posiedzenia mediacyjne"
        ordering = ["data", "godzina"]

    def __str__(self):
        return f"{self.data:%d.%m.%Y} {self.get_rodzaj_display()}"


class WpisMediacji(models.Model):
    """Chronologia mediacji poza posiedzeniami: telefony, korespondencja, protokół, rachunek…"""

    mediacja = models.ForeignKey(Mediacja, on_delete=models.CASCADE, related_name="wpisy")
    data = models.DateField(default=date.today)
    opis = models.TextField()
    czas_min = models.PositiveIntegerField("czas (minuty)", default=0)
    wykonal = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    utworzono = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "wpis w mediacji"
        verbose_name_plural = "wpisy w mediacjach"
        ordering = ["-data", "-utworzono"]

    @property
    def czas_txt(self):
        return format_czas(self.czas_min)


def format_czas(minuty: int) -> str:
    h, m = divmod(minuty or 0, 60)
    if h and m:
        return f"{h} h {m} min"
    if h:
        return f"{h} h"
    return f"{m} min"

