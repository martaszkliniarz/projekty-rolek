from django import forms

from .models import Czynnosc, Termin
from .terminy import JEDNOSTKI, PRESETY

DATA = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")


class CzynnoscForm(forms.ModelForm):
    godziny = forms.IntegerField(min_value=0, required=False, initial=0, label="h")
    minuty = forms.IntegerField(min_value=0, max_value=59, required=False, initial=0, label="min")

    class Meta:
        model = Czynnosc
        fields = ["data", "typ", "opis", "rozliczalna"]
        widgets = {"data": DATA, "opis": forms.Textarea(attrs={"rows": 2})}

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.czas_min = (self.cleaned_data.get("godziny") or 0) * 60 + (self.cleaned_data.get("minuty") or 0)
        if commit:
            obj.save()
        return obj


class TerminForm(forms.ModelForm):
    class Meta:
        model = Termin
        fields = ["data", "godzina", "rodzaj", "opis", "miejsce", "podstawa", "wyliczenie", "przypisany"]
        widgets = {
            "data": DATA,
            "godzina": forms.TimeInput(attrs={"type": "time"}),
            "wyliczenie": forms.HiddenInput(),
        }


class KalkulatorForm(forms.Form):
    ZDARZENIE = [
        ("bezposrednio", "znam datę zdarzenia (doręczenie, ogłoszenie)"),
        ("portal", "doręczenie przez portal informacyjny"),
        ("awizo", "doręczenie pocztowe — awizo (fikcja)"),
    ]
    preset = forms.ChoiceField(
        label="rodzaj terminu", required=False,
        choices=[("", "— własny termin —")] + [
            (p["kod"], f'{p["tryb"]}: {p["nazwa"]} ({p["ilosc"]} {JEDNOSTKI[p["jednostka"]]})') for p in PRESETY
        ],
    )
    ilosc = forms.IntegerField(label="długość", min_value=1, required=False)
    jednostka = forms.ChoiceField(label="jednostka", choices=list(JEDNOSTKI.items()), required=False)
    zdarzenie = forms.ChoiceField(label="od czego liczymy", choices=ZDARZENIE, initial="bezposrednio")
    data = forms.DateField(label="data zdarzenia / umieszczenia w portalu / pierwszego awizo", widget=DATA)
    otwarcie = forms.DateField(label="data otwarcia w portalu (jeśli otwarto)", required=False, widget=DATA)

    def clean(self):
        c = super().clean()
        if not c.get("preset") and not (c.get("ilosc") and c.get("jednostka")):
            raise forms.ValidationError("Wybierz rodzaj terminu albo podaj długość i jednostkę.")
        return c
