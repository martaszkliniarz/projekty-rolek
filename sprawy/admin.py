from django.contrib import admin
from django.utils.html import format_html

from .models import (Czynnosc, Dokument, Mediacja, Osoba, Posiedzenie, Postepowanie, Sprawa, StronaMediacji,
                     Termin, Uczestnik, WpisMediacji, Wplyw)

admin.site.site_header = "Kancelaria — panel edycji"
admin.site.site_title = "Kancelaria"
admin.site.index_title = "Dane kancelarii"


class PostepowanieInline(admin.TabularInline):
    model = Postepowanie
    extra = 0


class UczestnikInline(admin.TabularInline):
    model = Uczestnik
    extra = 0
    autocomplete_fields = ["osoba"]


class TerminInline(admin.TabularInline):
    model = Termin
    extra = 0
    fields = ["data", "godzina", "rodzaj", "opis", "podstawa", "status", "przypisany"]


class CzynnoscInline(admin.TabularInline):
    model = Czynnosc
    extra = 0
    fields = ["data", "typ", "opis", "czas_min", "rozliczalna", "wykonal", "potwierdzona"]


class DokumentInline(admin.TabularInline):
    model = Dokument
    extra = 0


@admin.register(Sprawa)
class SprawaAdmin(admin.ModelAdmin):
    list_display = ["numer", "tytul", "klient", "dziedzina", "status", "data_przyjecia", "pokaz"]
    list_filter = ["status", "dziedzina", "rozliczenie"]
    search_fields = ["numer", "tytul", "klient__nazwa", "postepowania__sygnatura", "opis"]
    autocomplete_fields = ["klient"]
    readonly_fields = ["numer"]
    inlines = [PostepowanieInline, UczestnikInline, TerminInline, CzynnoscInline, DokumentInline]
    fieldsets = [
        (None, {"fields": ["numer", "tytul", "klient", "rola_klienta", "dziedzina", "status", "prowadzacy"]}),
        ("Daty", {"fields": ["data_przyjecia", "data_zakonczenia"]}),
        ("Treść", {"fields": ["opis", "strategia"]}),
        ("Wynagrodzenie", {"fields": ["rozliczenie", "stawka_godzinowa", "wynagrodzenie_ryczalt"]}),
    ]

    @admin.display(description="")
    def pokaz(self, obj):
        return format_html('<a href="{}">karta sprawy →</a>', obj.get_absolute_url())

    def view_on_site(self, obj):
        return obj.get_absolute_url()


@admin.register(Osoba)
class OsobaAdmin(admin.ModelAdmin):
    list_display = ["nazwa", "typ", "pesel", "email", "telefon"]
    search_fields = ["nazwa", "nazwisko_rodowe", "pesel", "nip", "email"]
    list_filter = ["typ"]


@admin.register(Termin)
class TerminAdmin(admin.ModelAdmin):
    list_display = ["data", "godzina", "opis", "sprawa", "rodzaj", "status", "przypisany"]
    list_filter = ["status", "rodzaj", "przypisany"]
    search_fields = ["opis", "sprawa__tytul", "sprawa__numer"]
    date_hierarchy = "data"
    autocomplete_fields = ["sprawa"]
    list_editable = ["status"]


@admin.register(Czynnosc)
class CzynnoscAdmin(admin.ModelAdmin):
    list_display = ["data", "sprawa", "typ", "opis", "czas_min", "wykonal", "zrodlo", "potwierdzona"]
    list_filter = ["typ", "zrodlo", "potwierdzona", "rozliczalna", "wykonal"]
    search_fields = ["opis", "sprawa__tytul", "sprawa__numer"]
    date_hierarchy = "data"
    autocomplete_fields = ["sprawa"]


admin.site.register(Dokument)


@admin.register(Wplyw)
class WplywAdmin(admin.ModelAdmin):
    list_display = ["data", "zrodlo", "rodzaj", "tytul", "sygnatura", "sprawa", "status"]
    list_filter = ["status", "zrodlo", "rodzaj"]
    search_fields = ["tytul", "tresc", "sygnatura", "nadawca"]
    autocomplete_fields = ["sprawa"]
    readonly_fields = ["zewn_id", "czynnosc"]


class StronaMediacjiInline(admin.TabularInline):
    model = StronaMediacji
    extra = 0
    autocomplete_fields = ["osoba"]


class PosiedzenieInline(admin.TabularInline):
    model = Posiedzenie
    extra = 0
    fields = ["data", "godzina", "rodzaj", "z_kim", "miejsce", "odbyte", "czas_min"]


class WpisMediacjiInline(admin.TabularInline):
    model = WpisMediacji
    extra = 0
    fields = ["data", "opis", "czas_min", "wykonal"]


@admin.register(Mediacja)
class MediacjaAdmin(admin.ModelAdmin):
    list_display = ["numer", "tytul", "rola", "dziedzina", "podstawa", "status", "termin_do", "pokaz"]
    list_filter = ["rola", "status", "dziedzina", "podstawa"]
    search_fields = ["numer", "tytul", "sygnatura", "strony__osoba__nazwa", "mediator"]
    autocomplete_fields = ["sprawa"]
    readonly_fields = ["numer"]
    inlines = [StronaMediacjiInline, PosiedzenieInline, WpisMediacjiInline]
    fieldsets = [
        (None, {"fields": ["numer", "tytul", "rola", "dziedzina", "podstawa", "status", "przedmiot"]}),
        ("Skierowanie", {"fields": ["organ", "sygnatura", "data_skierowania", "termin_do"]}),
        ("Gdy jestem pełnomocnikiem", {"fields": ["sprawa", "mediator"], "classes": ["collapse"]}),
        ("Wynik", {"fields": ["wynik", "data_zakonczenia", "data_protokolu", "tresc_ugody"]}),
        ("Rozliczenie", {"fields": ["platnik", "wynagrodzenie", "wydatki", "data_wniosku_koszty", "data_zaplaty"]}),
        ("Notatki", {"fields": ["notatki"]}),
    ]

    @admin.display(description="")
    def pokaz(self, obj):
        return format_html('<a href="{}">karta mediacji →</a>', obj.get_absolute_url())

    def view_on_site(self, obj):
        return obj.get_absolute_url()
