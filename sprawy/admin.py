from django.contrib import admin
from django.utils.html import format_html

from .models import Czynnosc, Dokument, Osoba, Postepowanie, Sprawa, Termin, Uczestnik

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
