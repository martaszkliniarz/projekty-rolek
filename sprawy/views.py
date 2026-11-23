import csv
from datetime import date, timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.crypto import constant_time_compare
from django.views.decorators.http import require_POST

from .forms import CzynnoscForm, KalkulatorForm, TerminForm
from .ics import kalendarz_ics
from .models import Czynnosc, Osoba, Sprawa, Termin, Uczestnik, format_czas
from .terminy import PRESETY_PO_KODZIE, doreczenie_awizo, doreczenie_portal, fmt, oblicz_termin


@login_required
def pulpit(request):
    dzis = date.today()
    otwarte = Termin.objects.filter(status=Termin.Status.OTWARTY).select_related("sprawa")
    pocz_mies = dzis.replace(day=1)
    czas_mies = Czynnosc.objects.filter(data__gte=pocz_mies).aggregate(s=Sum("czas_min"))["s"] or 0
    return render(request, "sprawy/pulpit.html", {
        "dzis": dzis,
        "zalegle": otwarte.filter(data__lt=dzis),
        "na_dzis": otwarte.filter(data=dzis),
        "tydzien": otwarte.filter(data__gt=dzis, data__lte=dzis + timedelta(days=7)),
        "miesiac": otwarte.filter(data__gt=dzis + timedelta(days=7), data__lte=dzis + timedelta(days=30)),
        "aktywne": Sprawa.objects.filter(status=Sprawa.Status.AKTYWNA).count(),
        "czas_mies": format_czas(czas_mies),
        "do_potwierdzenia": Czynnosc.objects.filter(potwierdzona=False).count(),
        "ostatnie": Czynnosc.objects.select_related("sprawa", "wykonal")[:10],
        "bez_ruchu": Sprawa.objects.filter(status=Sprawa.Status.AKTYWNA)
            .exclude(czynnosci__data__gte=dzis - timedelta(days=30))
            .exclude(terminy__status=Termin.Status.OTWARTY)[:10],
    })


@login_required
def lista_spraw(request):
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "aktywna")
    sprawy = Sprawa.objects.select_related("klient").prefetch_related("postepowania")
    if status:
        sprawy = sprawy.filter(status=status)
    if q:
        sprawy = sprawy.filter(
            Q(tytul__icontains=q) | Q(numer__icontains=q) | Q(klient__nazwa__icontains=q)
            | Q(postepowania__sygnatura__icontains=q) | Q(uczestnicy__osoba__nazwa__icontains=q)
        ).distinct()
    return render(request, "sprawy/lista.html", {
        "sprawy": sprawy, "q": q, "status": status, "statusy": Sprawa.Status.choices,
    })


@login_required
def sprawa(request, pk):
    s = get_object_or_404(Sprawa.objects.select_related("klient"), pk=pk)
    czynnosc_form = CzynnoscForm(prefix="c")
    termin_form = TerminForm(prefix="t", initial={"przypisany": request.user})
    if request.method == "POST":
        if "dodaj_czynnosc" in request.POST:
            czynnosc_form = CzynnoscForm(request.POST, prefix="c")
            if czynnosc_form.is_valid():
                c = czynnosc_form.save(commit=False)
                c.sprawa, c.wykonal = s, request.user
                c.save()
                messages.success(request, "Dodano czynność.")
                return redirect(s)
        elif "dodaj_termin" in request.POST:
            termin_form = TerminForm(request.POST, prefix="t")
            if termin_form.is_valid():
                t = termin_form.save(commit=False)
                t.sprawa = s
                t.save()
                messages.success(request, f"Dodano termin {t.data:%d.%m.%Y}.")
                return redirect(s)
    czynnosci = s.czynnosci.select_related("wykonal")
    return render(request, "sprawy/sprawa.html", {
        "s": s,
        "postepowania": s.postepowania.all(),
        "uczestnicy": s.uczestnicy.select_related("osoba"),
        "terminy_otwarte": s.terminy.filter(status=Termin.Status.OTWARTY),
        "terminy_zamkniete": s.terminy.exclude(status=Termin.Status.OTWARTY).order_by("-data")[:20],
        "czynnosci": czynnosci,
        "czas": format_czas(s.czas_minuty()),
        "czas_rozliczalny": format_czas(czynnosci.filter(rozliczalna=True).aggregate(x=Sum("czas_min"))["x"] or 0),
        "dokumenty": s.dokumenty.all(),
        "czynnosc_form": czynnosc_form,
        "termin_form": termin_form,
    })


@login_required
@require_POST
def termin_status(request, pk):
    t = get_object_or_404(Termin, pk=pk)
    nowy = request.POST.get("status")
    if nowy in Termin.Status.values:
        t.status = nowy
        t.wykonano = date.today() if nowy == Termin.Status.WYKONANY else None
        t.save()
    return redirect(request.POST.get("next") or t.sprawa.get_absolute_url())


@login_required
@require_POST
def czynnosc_potwierdz(request, pk):
    c = get_object_or_404(Czynnosc, pk=pk)
    c.potwierdzona = True
    c.save(update_fields=["potwierdzona"])
    return redirect(request.POST.get("next") or c.sprawa.get_absolute_url())


@login_required
def terminy(request):
    widok = request.GET.get("widok", "otwarte")
    qs = Termin.objects.select_related("sprawa", "przypisany")
    if widok == "otwarte":
        qs = qs.filter(status=Termin.Status.OTWARTY)
    elif widok == "wykonane":
        qs = qs.exclude(status=Termin.Status.OTWARTY).order_by("-data")
    if request.GET.get("moje"):
        qs = qs.filter(przypisany=request.user)
    return render(request, "sprawy/terminy.html", {"terminy": qs[:300], "widok": widok})


@login_required
def kalkulator(request):
    sprawa_obj = None
    if request.GET.get("sprawa"):
        sprawa_obj = get_object_or_404(Sprawa, pk=request.GET["sprawa"])
    form = KalkulatorForm(request.GET or None)
    wynik, doreczenie, preset, termin_form = None, None, None, None
    if request.GET.get("data") and form.is_valid():
        c = form.cleaned_data
        preset = PRESETY_PO_KODZIE.get(c["preset"])
        ilosc = preset["ilosc"] if preset else c["ilosc"]
        jednostka = preset["jednostka"] if preset else c["jednostka"]
        start = c["data"]
        if c["zdarzenie"] == "portal":
            start, opis = doreczenie_portal(c["data"], c.get("otwarcie"))
            doreczenie = opis
        elif c["zdarzenie"] == "awizo":
            start, opis = doreczenie_awizo(c["data"])
            doreczenie = opis
        wynik = oblicz_termin(start, ilosc, jednostka)
        if sprawa_obj:
            wyliczenie = ([doreczenie] if doreczenie else []) + wynik.wyjasnienie
            termin_form = TerminForm(prefix="t", initial={
                "data": wynik.koniec,
                "rodzaj": Termin.Rodzaj.PROCESOWY,
                "opis": preset["nazwa"] if preset else "",
                "podstawa": preset["podstawa"] if preset else "",
                "wyliczenie": "\n".join(wyliczenie),
                "przypisany": request.user,
            })
    return render(request, "sprawy/kalkulator.html", {
        "form": form, "wynik": wynik, "doreczenie": doreczenie, "preset": preset,
        "sprawa": sprawa_obj, "termin_form": termin_form,
        "koniec_txt": fmt(wynik.koniec) if wynik else "",
    })


@login_required
def konflikt(request):
    q = request.GET.get("q", "").strip()
    wyniki = []
    if len(q) >= 3:
        osoby = Osoba.objects.filter(
            Q(nazwa__icontains=q) | Q(nazwisko_rodowe__icontains=q) | Q(pesel=q) | Q(nip=q)
        )
        for o in osoby:
            udzialy = [(s, f"klient ({s.rola_klienta})" if s.rola_klienta else "klient", False)
                       for s in o.sprawy_klienta.all()]
            udzialy += [(u.sprawa, u.rola, u.strona_przeciwna)
                        for u in Uczestnik.objects.filter(osoba=o).select_related("sprawa")]
            wyniki.append((o, udzialy))
    return render(request, "sprawy/konflikt.html", {"q": q, "wyniki": wyniki})


@login_required
def raport_czasu(request):
    od = request.GET.get("od") or date.today().replace(day=1).isoformat()
    do = request.GET.get("do") or date.today().isoformat()
    qs = Czynnosc.objects.filter(data__gte=od, data__lte=do).select_related("sprawa", "wykonal")
    if request.GET.get("sprawa"):
        qs = qs.filter(sprawa_id=request.GET["sprawa"])
    if request.GET.get("format") == "csv":
        resp = HttpResponse(content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = f'attachment; filename="czas_{od}_{do}.csv"'
        resp.write("﻿")  # BOM — żeby Excel poprawnie odczytał polskie znaki
        w = csv.writer(resp, delimiter=";")
        w.writerow(["data", "sprawa", "typ", "opis", "minuty", "godziny", "rozliczalna", "wykonał"])
        for c in qs.order_by("data"):
            w.writerow([c.data, str(c.sprawa), c.get_typ_display(), c.opis, c.czas_min,
                        str(round(c.czas_min / 60, 2)).replace(".", ","), "tak" if c.rozliczalna else "nie",
                        (c.wykonal.get_full_name() or c.wykonal.username) if c.wykonal else ""])
        return resp
    per_sprawa = (qs.values("sprawa__id", "sprawa__numer", "sprawa__tytul")
                  .annotate(suma=Sum("czas_min")).order_by("-suma"))
    for r in per_sprawa:
        r["czas"] = format_czas(r["suma"])
    return render(request, "sprawy/raport_czasu.html", {
        "od": od, "do": do, "per_sprawa": per_sprawa,
        "suma": format_czas(qs.aggregate(s=Sum("czas_min"))["s"] or 0),
        "sprawy": Sprawa.objects.filter(status=Sprawa.Status.AKTYWNA),
        "wybrana": request.GET.get("sprawa", ""),
    })


def kalendarz(request, token):
    """Publiczny (chroniony tokenem) kanał .ics do subskrypcji w Kalendarzu Google."""
    if not settings.KALENDARZ_TOKEN or not constant_time_compare(token, settings.KALENDARZ_TOKEN):
        raise Http404
    od = date.today() - timedelta(days=60)
    qs = (Termin.objects.filter(data__gte=od).exclude(status=Termin.Status.WYKONANY)
          .select_related("sprawa").prefetch_related("sprawa__postepowania"))
    return HttpResponse(kalendarz_ics(qs, anonimowy=settings.KALENDARZ_ANONIMOWY), content_type="text/calendar; charset=utf-8")
