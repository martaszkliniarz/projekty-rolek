# Plan rozwoju

## ✅ Etap 1 — fundament
Kartoteka spraw, chronologia z czasem pracy, terminy i kalkulator (KPC/KPK),
raport czasu (CSV), kalendarz .ics dla Google, wersja lokalna i chmurowa.

## ✅ Mediacje
Osobny rejestr mediacji (rola mediatora lub pełnomocnika): strony, skierowanie, termin na przeprowadzenie,
posiedzenia z czasem i poufną notatką, chronologia, wynik/ugoda, przypomnienie o złożeniu protokołu,
rozliczenie wynagrodzenia mediatora. Posiedzenia na pulpicie, w porannym raporcie i w kalendarzu (anonimowo).
Do rozważenia: dopasowanie wpływów z poczty do mediacji po sygnaturze, szablony dokumentów mediatora
(zaproszenie na spotkanie, protokół, ugoda, rachunek).

## Etap 2 — poczta, portal, Google i poranny raport
- ✅ **Skrzynka „Wpływy”** z dopasowaniem do sprawy po sygnaturze → chronologia / kalkulator terminu.
- ✅ **Poczta home.pl (IMAP, tylko odczyt)**: kancelaria@adwokat-sosnowiec.eu — powiadomienia z portalu
  i maile z sygnaturami spraw.
- ✅ **Poranny raport** e-mailem w dni robocze + asystent w tle (docker compose).
- ⏳ **Robot Portalu Informacyjnego** — codziennie przegląda sprawy w portalu:
  - zakładka **„Czynności”** → nowe czynności trafiają do wpływów, a po akceptacji do chronologii,
  - zakładka **„Dokumenty”** → nowe pisma (tu otwieranie nie powoduje doręczenia) — opis, a docelowo
    treść/streszczenie i zapis pliku w dokumentach sprawy,
  - zakładka **„Doręczenia”** → wyłącznie odczyt LISTY (data umieszczenia, nazwa pisma); robot nigdy nie
    otwiera ani nie pobiera dokumentu z tej zakładki; program liczy datę fikcji doręczenia i alarmuje.
  - Miejsce zapisu jest gotowe (`sprawy/portal.py`). Do napisania robota potrzebna jest rzeczywista
    struktura stron portalu (zapisane strony lub wspólna sesja na komputerze Pani Mecenas) oraz
    informacja o sposobie logowania (hasło / kod SMS / aplikacja).
- ⏳ **Kalendarz Google przez API**: natychmiastowa synchronizacja terminów (zamiast subskrypcji .ics).

## Etap 3 — asystenci AI
- **Asystent wpływów**: streszcza nowe pismo/powiadomienie, proponuje wpis do chronologii i termin
  (z wyliczeniem) — do akceptacji jednym kliknięciem.
- **Asystent korespondencji**: szkic maila do klienta z aktualizacją sprawy na podstawie chronologii;
  zapisywany jako **wersja robocza w skrzynce home.pl** (widoczna w Outlooku) — nic nie wychodzi samo.
- **Asystent czasu**: na podstawie wysłanych maili, rozpraw i pism proponuje wpisy czasu do potwierdzenia.
- **Asystent „co w sprawie”**: pytanie w języku naturalnym o dowolną sprawę („kiedy ostatnio był kontakt
  z klientką?”, „jakie wnioski dowodowe złożyliśmy?”).
- Wymogi: dostawca AI z umową powierzenia (DPA), brak trenowania na danych, przetwarzanie w UE;
  pseudonimizacja tam, gdzie to możliwe.

## Etap 4 — rozliczenia i dodatki
- Rozliczenia: godzinowe / ryczałt / success fee, zestawienie dla klienta, faktury (KSeF).
- Obrony z urzędu: wnioski o koszty wg stawek z rozporządzenia.
- Szablony pism wypełniane danymi sprawy (pozew rozwodowy, wniosek o zabezpieczenie, apelacja, zażalenie…).
- Kalkulator alimentów / koszty utrzymania dziecka.
- Sprawy karne: przedawnienie karalności, kontrola terminów tymczasowego aresztowania.
- Notatki głosowe po rozprawie → transkrypcja → chronologia.
- LEX / Legalis: linki do aktów i orzeczeń w sprawie (API tylko po uzgodnieniu z wydawcą);
  darmowe źródła: ISAP/ELI, Portal Orzeczeń.
- RODO: rejestr czynności, okresy przechowywania i archiwizacja zakończonych spraw.
