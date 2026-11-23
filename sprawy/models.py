import uuid
from datetime import date

from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.urls import reverse


class Osoba(models.Model):
    """Każda osoba lub podmiot: klient, strona przeciwna, świadek, pokrzywdzony…
    Jedna wspólna kartoteka pozwala sprawdzać konflikt interesów."""

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
    """Pozostałe osoby w sprawie (do sprawdzania konfliktu interesów)."""

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


def format_czas(minuty: int) -> str:
    h, m = divmod(minuty or 0, 60)
    if h and m:
        return f"{h} h {m} min"
    if h:
        return f"{h} h"
    return f"{m} min"

