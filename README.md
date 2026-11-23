# ⚖️ Kancelaria — program do prowadzenia spraw

Autorski program dla jednoosobowej kancelarii adwokackiej (sprawy rodzinne i karne).

**Etap 1 (gotowy):**

| Moduł | Co robi |
|---|---|
| **Pulpit** | terminy po czasie, na dziś, na 7 i 30 dni; czas pracy w miesiącu; sprawy „uśpione” |
| **Kartoteka spraw** | klient, postępowania i sygnatury, uczestnicy, stan sprawy i strategia, dokumenty |
| **Chronologia i czas** | każda czynność z czasem trwania → suma dla sprawy, raport, eksport do Excela |
| **Terminy** | lista z oznaczaniem „wykonane”, przypisanie do osoby (Pani / asystentka) |
| **Kalkulator terminów** | KPC i KPK, soboty i święta, fikcja doręczenia (portal / awizo), gotowe presety (apelacja, zażalenie, kasacja…) — wynik zapisuje się w sprawie razem z wyliczeniem |
| **Konflikt interesów** | wyszukiwanie osoby we wszystkich sprawach (klient / strona przeciwna / uczestnik) |
| **Kalendarz Google** | wszystkie terminy jako subskrybowany kalendarz (tryb anonimowy — bez nazwisk) |
| **Panel edycji** | dodawanie i poprawianie wszystkiego: sprawy, osoby, terminy, czynności, dokumenty |

Plan kolejnych etapów (poczta home.pl, portal sądów, asystenci AI): [docs/PLAN.md](docs/PLAN.md).

---

## Uruchomienie na komputerze

1. Zainstaluj **Python 3.12 lub nowszy** z [python.org](https://www.python.org/downloads/)
   (w Windows zaznacz „Add Python to PATH”).
2. Pobierz ten folder (np. przycisk *Code → Download ZIP* na GitHubie) i rozpakuj.
3. **Windows:** kliknij dwukrotnie `uruchom.bat`. **Mac:** w Terminalu `./uruchom.sh`.
4. Przy pierwszym uruchomieniu program zapyta o login i hasło — to będzie Pani konto.
5. Przeglądarka otworzy się na `http://127.0.0.1:8000`.

Chcesz obejrzeć program z przykładowymi danymi? Przed pierwszym uruchomieniem (albo w dowolnym
momencie) wpisz: `.venv\Scripts\python manage.py dane_przykladowe` (Windows) /
`.venv/bin/python manage.py dane_przykladowe` (Mac).

**Konto dla asystentki:** Panel edycji → Użytkownicy → Dodaj. Zaznacz „W zespole” i nadaj uprawnienia
do modułu *Sprawy* (bez uprawnień do użytkowników).

## Uruchomienie w chmurze

Program jest gotowy do uruchomienia w kontenerze Docker (np. na serwerze VPS w Polsce / UE,
także w home.pl, OVH, Hetzner):

```sh
cp .env.example .env        # uzupełnij: DEBUG=0, SECRET_KEY, ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS
docker build -t kancelaria .
docker run -d --name kancelaria --env-file .env -v /srv/kancelaria-dane:/dane -p 8000:8000 kancelaria
docker exec -it kancelaria python manage.py createsuperuser
```

Przed serwerem musi stać HTTPS (np. Caddy lub panel hostingu). Wersję w chmurze najlepiej
ustawić razem — to jednorazowa praca na ok. godzinę.

## Kopie zapasowe — ważne!

Wszystkie dane są w folderze **`dane/`** (baza `kancelaria.sqlite3` + dokumenty w `pliki/`).
Ten folder trzeba regularnie kopiować (np. zaszyfrowany dysk zewnętrzny). Nie jest wysyłany na GitHuba.

## Kalendarz Google

1. W pliku `.env` ustaw `KALENDARZ_TOKEN=` na długi losowy ciąg (instrukcja w pliku).
2. W Kalendarzu Google: *Inne kalendarze → + → Z adresu URL* i wklej
   `https://ADRES-PROGRAMU/kalendarz/TOKEN.ics`.
3. Google odświeża taki kalendarz co kilka–kilkanaście godzin. Natychmiastowa synchronizacja
   przez API Google jest w planie Etapu 2.

Działa tylko z programem w chmurze (Google musi mieć dostęp do adresu). Przy
`KALENDARZ_ANONIMOWY=1` w Google widać tylko numer sprawy (np. „Apelacja – 2026/014”), bez nazwisk —
proszę też nie wpisywać nazwisk w opisie terminu.

## Kalkulator terminów — zasady

- dnia zdarzenia nie wlicza się (art. 111 § 2 KC, art. 123 § 1 KPK),
- tygodnie: ten sam dzień tygodnia; miesiące: ta sama data albo ostatni dzień miesiąca (art. 112 KC, art. 123 § 2 KPK),
- koniec w sobotę lub dzień ustawowo wolny → najbliższy dzień roboczy (art. 115 KC, art. 123 § 3 KPK);
  uwzględnia święta ruchome i Wigilię (wolna od 2025 r.),
- portal: doręczenie w dniu otwarcia, a najpóźniej po 14 dniach od umieszczenia (art. 131¹ KPC),
- awizo: doręczenie zastępcze z upływem 14 dni od pierwszego awizo.

Kalkulator jest pomocą — przy każdym terminie warto zerknąć na zapisane wyliczenie.
Presety terminów są w pliku `sprawy/terminy.py` (lista `PRESETY`) — łatwo dopisać kolejne.

## Dla informatyka

Django 5.2 + SQLite, bez JavaScriptu. Testy: `DEBUG=1 python manage.py test sprawy`.
