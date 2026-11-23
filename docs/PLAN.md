# Plan rozwoju

## ✅ Etap 1 — fundament
Kartoteka spraw, chronologia z czasem pracy, terminy i kalkulator (KPC/KPK), konflikt interesów,
raport czasu (CSV), kalendarz .ics dla Google, wersja lokalna i chmurowa.

## Etap 2 — poczta, portal, Google i poranny raport
- **Poczta home.pl (IMAP)**: program co kilka/kilkanaście minut czyta skrzynkę (w tym folder z powiadomieniami
  z Portalu Informacyjnego), rozpoznaje sygnaturę i przypisuje wiadomość do sprawy (wpis „wpływ” w chronologii
  do potwierdzenia).
- **Portal Informacyjny Sądów Powszechnych**: źródłem są e-maile z powiadomieniami portalu (bez otwierania
  dokumentów!). Program zakłada termin „doręczenie fikcyjne za 14 dni” i przypomina, że otwarcie
  dokumentu = doręczenie. Ewentualny odczyt bezpośrednio z portalu — do oceny po sprawdzeniu regulaminu.
- **Kalendarz Google przez API**: natychmiastowa synchronizacja terminów (zamiast subskrypcji .ics).
- **Poranny raport** (codziennie ok. 7:00, e-mailem): nowe wpływy, terminy na dziś/tydzień, terminy po czasie,
  wpisy czekające na potwierdzenie.

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
