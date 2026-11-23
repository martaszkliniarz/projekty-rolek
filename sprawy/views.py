import csv
from datetime import date, timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.crypto import constant_time_compare
from django.views.decorators.http import require_POST

from .forms import (CzynnoscForm, KalkulatorForm, OdbyteForm, PosiedzenieForm, TerminForm, WpisMediacjiForm,
                    ZakonczenieForm)
from .ics import kalendarz_ics
from .models import Czynnosc, Mediacja, Posiedzenie, Sprawa, Termin, Wplyw, format_czas
from .terminy import PRESETY_PO_KODZIE, doreczenie_awizo, doreczenie_portal, fmt, oblicz_termin


def mediacje_alarmy(dzis):
    """Mediacje wymagające uwagi: kończący się termin i niezłożone protokoły."""
    alarmy = []
    for m in Mediacja.objects.filter(status__in=[Mediacja.Status.SKIEROWANA, Mediacja.Status.W_TOKU],
                                     termin_do__isnull=False, termin_do__lte=dzis + timedelta(days=14)):
        d = m.dni_do_konca
        alarmy.append((m, f"termin na mediację {'minął' if d < 0 else 'upływa'} {m.termin_do:%d.%m.%Y}"
                          + (f" (za {d} dni)" if d > 0 else " (dziś)" if d == 0 else "")))
    for m in Mediacja.objects.exclude(wynik="").filter(data_protokolu__isnull=True, rola=Mediacja.Rola.MEDIATOR) \
            .exclude(podstawa=Mediacja.Podstawa.UMOWA):
        alarmy.append((m, "protokół do złożenia w sądzie / u prokuratora"))
    return alarmy


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
        "nowe_wplywy": Wplyw.objects.filter(status=Wplyw.Status.NOWY).count(),
        "doreczenia": Wplyw.objects.filter(status=Wplyw.Status.NOWY, rodzaj=Wplyw.Rodzaj.DORECZENIE).count(),
        "ostatnie": Czynnosc.objects.select_related("sprawa", "wykonal")[:10],
        "posiedzenia": Posiedzenie.objects.filter(odbyte=False, data__gte=dzis, data__lte=dzis + timedelta(days=7))
            .select_related("mediacja"),
        "mediacje_alarmy": mediacje_alarmy(dzis),
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
    if "oblicz" in request.GET:
        form = KalkulatorForm(request.GET)
    else:
        form = KalkulatorForm(initial=request.GET.dict())
    wynik, doreczenie, preset, termin_form = None, None, None, None
    if form.is_bound and form.is_valid():
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
def wplywy(request):
    widok = request.GET.get("widok", "nowe")
    qs = Wplyw.objects.select_related("sprawa")
    qs = qs.filter(status=Wplyw.Status.NOWY) if widok == "nowe" else qs.exclude(status=Wplyw.Status.NOWY)
    return render(request, "sprawy/wplywy.html", {
        "wplywy": qs[:200], "widok": widok,
        "sprawy": Sprawa.objects.exclude(status=Sprawa.Status.ARCHIWUM),
    })


@login_required
@require_POST
def wplyw_akcja(request, pk):
    w = get_object_or_404(Wplyw, pk=pk)
    akcja = request.POST.get("akcja")
    if akcja == "pomin":
        w.status = Wplyw.Status.POMINIETY
        w.save()
        return redirect("wplywy")
    if request.POST.get("sprawa"):
        w.sprawa = get_object_or_404(Sprawa, pk=request.POST["sprawa"])
    if not w.sprawa:
        messages.error(request, "Wybierz sprawę, do której należy ten wpływ.")
        return redirect("wplywy")
    opis = f"[{w.get_rodzaj_display()}] {w.tytul}"
    if request.POST.get("notatka"):
        opis += f"\n{request.POST['notatka']}"
    w.czynnosc = Czynnosc.objects.create(
        sprawa=w.sprawa, data=w.data, typ=Czynnosc.Typ.WPLYW, opis=opis, czas_min=0, rozliczalna=False,
        wykonal=request.user,
        zrodlo=Czynnosc.Zrodlo.PORTAL if w.zrodlo == Wplyw.Zrodlo.PORTAL else Czynnosc.Zrodlo.POCZTA,
    )
    w.status = Wplyw.Status.PRZYJETY
    w.save()
    messages.success(request, f"Dodano do chronologii sprawy {w.sprawa.numer}.")
    if akcja == "termin":
        zdarzenie = "portal" if w.rodzaj == Wplyw.Rodzaj.DORECZENIE else "bezposrednio"
        return redirect(f"{reverse('kalkulator')}?sprawa={w.sprawa.pk}&zdarzenie={zdarzenie}&data={w.data:%Y-%m-%d}")
    return redirect("wplywy")


@login_required
def lista_mediacji(request):
    q = request.GET.get("q", "").strip()
    widok = request.GET.get("widok", "aktywne")
    rola = request.GET.get("rola", "")
    qs = Mediacja.objects.prefetch_related("strony__osoba")
    if widok == "aktywne":
        qs = qs.filter(status__in=[Mediacja.Status.SKIEROWANA, Mediacja.Status.W_TOKU])
    elif widok == "zakonczone":
        qs = qs.filter(status__in=[Mediacja.Status.ZAKONCZONA, Mediacja.Status.ROZLICZONA])
    if rola:
        qs = qs.filter(rola=rola)
    if q:
        qs = qs.filter(Q(tytul__icontains=q) | Q(numer__icontains=q) | Q(sygnatura__icontains=q)
                       | Q(strony__osoba__nazwa__icontains=q)).distinct()
    dzis = date.today()
    return render(request, "sprawy/mediacje.html", {
        "mediacje": qs, "q": q, "widok": widok, "rola": rola, "role": Mediacja.Rola.choices,
        "nierozliczone": Mediacja.objects.filter(rola=Mediacja.Rola.MEDIATOR, status=Mediacja.Status.ZAKONCZONA,
                                                 data_zaplaty__isnull=True),
        "alarmy": mediacje_alarmy(dzis),
    })


@login_required
def mediacja(request, pk):
    m = get_object_or_404(Mediacja.objects.select_related("sprawa"), pk=pk)
    posiedzenie_form = PosiedzenieForm(prefix="p")
    wpis_form = WpisMediacjiForm(prefix="w")
    zakonczenie_form = ZakonczenieForm(prefix="z", instance=m)
    if request.method == "POST":
        if "dodaj_posiedzenie" in request.POST:
            posiedzenie_form = PosiedzenieForm(request.POST, prefix="p")
            if posiedzenie_form.is_valid():
                p = posiedzenie_form.save(commit=False)
                p.mediacja = m
                p.save()
                messages.success(request, f"Zaplanowano posiedzenie {p.data:%d.%m.%Y}.")
                return redirect(m)
        elif "dodaj_wpis" in request.POST:
            wpis_form = WpisMediacjiForm(request.POST, prefix="w")
            if wpis_form.is_valid():
                w = wpis_form.save(commit=False)
                w.mediacja, w.wykonal, w.czas_min = m, request.user, wpis_form.minuty_lacznie()
                w.save()
                messages.success(request, "Dodano wpis.")
                return redirect(m)
        elif "odbyte" in request.POST:
            p = get_object_or_404(Posiedzenie, pk=request.POST["odbyte"], mediacja=m)
            f = OdbyteForm(request.POST, prefix=f"o{p.pk}")
            if f.is_valid():
                p.odbyte, p.czas_min = True, f.minuty_lacznie()
                if f.cleaned_data["notatka"]:
                    p.notatka = f.cleaned_data["notatka"]
                p.save()
                if m.status == Mediacja.Status.SKIEROWANA:
                    m.status = Mediacja.Status.W_TOKU
                    m.save(update_fields=["status"])
                messages.success(request, "Posiedzenie oznaczone jako odbyte.")
                return redirect(m)
        elif "zakoncz" in request.POST:
            zakonczenie_form = ZakonczenieForm(request.POST, prefix="z", instance=m)
            if zakonczenie_form.is_valid():
                m = zakonczenie_form.save(commit=False)
                if m.wynik and m.aktywna:
                    m.status = Mediacja.Status.ZAKONCZONA
                    m.data_zakonczenia = m.data_zakonczenia or date.today()
                m.save()
                messages.success(request, "Zapisano wynik mediacji.")
                return redirect(m)
    posiedzenia = m.posiedzenia.all()
    return render(request, "sprawy/mediacja.html", {
        "m": m, "strony": m.strony.select_related("osoba"),
        "planowane": [(p, OdbyteForm(prefix=f"o{p.pk}")) for p in posiedzenia if not p.odbyte],
        "odbyte": [p for p in posiedzenia if p.odbyte],
        "wpisy": m.wpisy.select_related("wykonal"),
        "czas": format_czas(m.czas_minuty()),
        "posiedzenie_form": posiedzenie_form, "wpis_form": wpis_form, "zakonczenie_form": zakonczenie_form,
    })


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
    med = {}
    if not request.GET.get("sprawa"):
        for p in Posiedzenie.objects.filter(odbyte=True, data__gte=od, data__lte=do).select_related("mediacja"):
            med[p.mediacja] = med.get(p.mediacja, 0) + p.czas_min
        from .models import WpisMediacji
        for w in WpisMediacji.objects.filter(data__gte=od, data__lte=do).select_related("mediacja"):
            med[w.mediacja] = med.get(w.mediacja, 0) + w.czas_min
    return render(request, "sprawy/raport_czasu.html", {
        "per_mediacja": [(m, format_czas(v)) for m, v in sorted(med.items(), key=lambda x: -x[1]) if v],
        "suma_mediacje": format_czas(sum(med.values())),
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
    posiedzenia = Posiedzenie.objects.filter(data__gte=od, odbyte=False).select_related("mediacja")
    return HttpResponse(kalendarz_ics(qs, anonimowy=settings.KALENDARZ_ANONIMOWY, posiedzenia=posiedzenia),
                        content_type="text/calendar; charset=utf-8")
