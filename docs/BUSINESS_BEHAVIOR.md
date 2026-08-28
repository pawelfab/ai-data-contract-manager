# ADCM i Contract Forge - zachowanie biznesowe

## 1. Cel i zakres dokumentu
Ten dokument opisuje trwale zachowanie biznesowe wspolpracy ADCM i Contract Forge.
Dokument odpowiada na pytania co system robi i dlaczego robi to w ten sposob.
Dokument nie opisuje jak system jest zbudowany technicznie.
Dokument nie zawiera nazw klas, funkcji, modulow ani sciezek implementacyjnych.
Czytelnik ma po lekturze ocenic, czy dane zachowanie jest wymagane produktowo.
Zakres obejmuje:
- podzial odpowiedzialnosci miedzy uslugami,
- model biznesowy kontraktu,
- cykl zycia sesji i tury,
- wymagane odpowiedzi Contract Forge,
- scenariusze biznesowe i przypadki brzegowe,
- uzasadnienie funkcji, ktore wygladaja na nadmiarowe,
- decyzje produktowe,
- kryteria akceptacji biznesowej.
Dokument jest trwaly i przekrojowy.
Nie jest instrukcja implementacji.

## 2. Podzial odpowiedzialnosci
Niezmiennik glowny:
"ADCM rozumie uzytkownika. Contract Forge rozumie kontrakt."
ADCM jest wlascicielem:
- rozmowy i jej kontekstu,
- intencji uzytkownika,
- stanu sesji,
- autorytetu wartosci,
- mutacji dokumentu,
- redakcji odpowiedzi,
- kolejnosci prezentowania pytan,
- historii zaakceptowanych decyzji.
Contract Forge jest wlascicielem:
- struktury kontraktu,
- wymagalnosci,
- dopuszczalnosci,
- propozycji z regul,
- diagnostyki,
- statusu dokumentu.
Context MCPs sa wlascicielem:
- dostarczania dowodow,
- dostarczania kontekstu,
- wykonywania ograniczonych dzialan pomocniczych.
Context MCPs nigdy nie mutuja stanu kontraktu.
Zasady jawne bez wyjatku:
- Forge jest bezstanowy.
- Forge nigdy nie widzi rozmowy.
- Forge nigdy nie wywoluje LLM.
- ADCM nigdy nie parsuje samodzielnie schematu kontraktu.
Znaczenie biznesowe:
- role sa czytelne,
- odpowiedzialnosc za blad jest audytowalna,
- klient rozmowy nie musi znac szczegolow kontraktu,
- usluga kontraktowa nie musi znac semantyki rozmowy.

## 3. Model biznesowy kontraktu
Kontrakt opisuje pipeline od danych wejsciowych do warstw analitycznych.
| Warstwa | Rola biznesowa | Wymagana |
|---|---|---|
| metadata | Tozsamosc kontraktu i metryka biznesowa | Tak |
| orchestration | Harmonogram i punkt startu | Tak |
| rawData | Kontext surowego wejscia | Nie |
| preparator | Przygotowanie danych | Nie |
| converter | Normalizacja zrodla | Nie |
| bronzeTable | Pierwszy zapis tabelaryczny | Nie |
| silver | Warstwa robocza i porzadkujaca | Nie |
| gold | Warstwa docelowa analityczna | Nie |
### 3.1 Sekcje opcjonalne
Sekcja jest AKTYWOWANA, gdy jest obecna w dokumencie i ma wartosc rozna od "null".
Jezeli schema tej sekcji definiuje flage `enabled`, to `enabled=false` DEAKTYWUJE sekcje nawet gdy jest obecna.
Pusty obiekt zapisany regula aktywacyjna (np. `/rawData = {}`, `/bronzeTable = {}`) jest intencjonalna aktywacja i nigdy nie jest 'foreign'.
Dla sekcji opcjonalnych aktywacja moze wynikac z jawnej decyzji uzytkownika albo z kontekstu zrodla, ktory uzytkownik zadeklarowal.
Dopoki sekcja opcjonalna nie jest wlaczona:
- nie nalezy do aktywnego dokumentu,
- nie generuje brakow,
- nie obniza kompletnosci kontraktu.
Po wlaczeniu sekcji opcjonalnej:
- sekcja staje sie czescia aktywnego kontraktu,
- pojawiaja sie jej wymagania,
- moga pojawic sie defaulty,
- moga pojawic sie propozcyje konwencyjne.
### 3.2 Alternatywy i warianty zrodla
Wariant zrodla jest wybierany przez typ zrodla.
Dopuszczone typy: csv, txt, json, jdbc, fixed_width.
Po wyborze jednego wariantu pola pozostalych wariantow NIE naleza do kontraktu.
System traktuje je jako obce.
Uzytkownik musi dostac jasna informacje o takim odrzuceniu.
### 3.3 Kolekcje
Kolekcje moga miec wiele elementow i to jest zamierzone.
Dotyczy to miedzy innymi silver.tables, gold.entries oraz columns.
Znaczenie biznesowe:
- wiele elementow jest legalne,
- dodanie elementu musi byc intencjonalne,
- usuniecie element jest pelnoprawna operacja,
- wymagania musza byc przypisane do konkretnego elementu,
- system musi odroznic dopisanie do elementu od utworzenia nowego.

## 4. Cykl zycia sesji i tury
### 4.1 Jedna tura uzytkownika = dokladnie jedna odpowiedz
Jedna wypowiedz uzytkownika konczy sie jedna odpowiedzia.
Uzytkownik nigdy nie czeka na wiele komunikatow dla tej samej tury.
To utrzymuje przewidywalny rytm rozmowy i czytelnosc postepu.
### 4.2 Wewnatr jednej tury ADCM moze wielokrotnie odpytac Forge
ADCM moze wielokrotnie odpytac Forge w jednej turze bez udzialu uzytkownika.
Przyklad: najpierw ustalenie typu zrodla, potem odkrycie pol tego typu.
Petla uzgadniania ma twardy limit rund.
Uzytkownik nadal dostaje jedna odpowiedz.
Wlascicielem petli rund pozostaje stabilizacja kontraktu; nie jest ona przenoszona do warstwy redakcji odpowiedzi.
### 4.3 Pochodzenie kazdej wartosci jest znane i trwale
Kazda wartosc ma stale pochodzenie:
- `user` - podana lub potwierdzona przez uzytkownika,
- `enrichment` - wynik konwencji biznesowej,
- `default` - wynik domyslnosci definicji.
Wartosc uzytkownika jest autorytatywna.
Enrichment nie moze jej cicho nadpisac w kolejnych turach.
Uzytkownik moze zmieniac te sama wartosc wielokrotnie.
Obowiazuje ostatnia decyzja uzytkownika.
### 4.4 Enrichment nie jest pamiecia
Forge jest bezstanowy i przy tym samym wejsciu proponuje to samo.
To ADCM pamieta, co zostalo zaakceptowane.
To ADCM przekazuje ten stan w kolejnym dokumencie.
Dzieki temu reguly pozostaja deterministyczne, a pamiec sesji ma jednego wlasciciela.

## 5. Co Forge musi zwracac
Forge musi zwracac szesc odpowiedzi biznesowych dla przekazanego dokumentu.
### 5.1 `writable`
`writable` oznacza wszystkie miejsca, w ktore wolno pisac przy aktualnym ksztalcie dokumentu.
Obejmuje tez sekcje opcjonalne jeszcze niewlaczone, oznaczone jako mozliwe do wlaczenia.
Sekcje niewlaczone nie trafiaja do dokumentu, ale ADCM musi umiec o nich opowiedziec.
### 5.2 `missing`
`missing` zawiera WSZYSTKIE brakujace wartosci wymagane, bez dawkowania.
Kolejnosc prezentacji brakow jest zadaniem ADCM.
W praktyce rozmowy oznacza to: Forge zwraca pelny zbior brakow, ADCM moze zadac jedno pytanie kotwiczace, ale lista `[brak]` w odpowiedzi nadal odzwierciedla pelny zbior Forge.
### 5.3 `foreign`
`foreign` zawiera wartosci obecne w dokumencie, ktore nie naleza do aktualnego ksztaltu.
Kazda pozycja musi byc jawna i uzasadniona.
Kazda pozycja `foreign` zawiera zawsze:
- `reason`,
- `admissible_fields` dla aktywnego wariantu.
`foreign` jest osobnym kluczem odpowiedzi i nie jest kopiowane do `diagnostics`.
Pozycje `foreign` nie uniewazniaja formalnie kontraktu: nie zmieniaja `status.valid`.
Wplywaja tylko na `status.clean`.
Forge jedynie raportuje lokalizacje obce; decyzja o usunieciu nalezy do ADCM,
a usuniecie musi byc jawnie zakomunikowane uzytkownikowi.
### 5.4 `proposals`
`proposals` to propozcyje z regul biznesowych, po jednej na lokalizacje, z podaniem przyczyny.
### 5.5 `diagnostics`
`diagnostics` obejmuje naruszenia typu, dozwolonych wartosci i regul miedcypolowych.
Diagnostyka musi byc przypisywalna do konkretnego miejsca.
### 5.6 `status`
`status` rozdziela trzy sygnaly:
- `valid` (brak bledow),
- `complete` (brak brakow),
- `clean` (brak lokalizacji obcych).
Kazdy sygnal musi byc obserwowalny osobno.
Zasady graniczne:
- Forge nigdy nie mutuje dokumentu.
- Forge nigdy nie porownuje znaczen dwoch wartosci.
- Forge nigdy nie zadaje pytan.

## 6. Scenariusze biznesowe
### SC-01
Sytuacja: Start rozmowy bez zadnych danych ("robimy zasilanie").
Co robi uzytkownik: Rozpoczyna proces bez szczegolow.
Oczekiwane zachowanie systemu: System prosi o pierwsza rozstrzygajaca informacje, nie o wszystko naraz.
Jednoczesnie odpowiedz moze prezentowac pelna liste `[brak]` wyliczona przez Forge.
Dlaczego to jest wymagane: Zapewnia niski prog wejscia i porzadkuje start rozmowy.
### SC-02
Sytuacja: Podanie systemu zrodlowego ("system sap").
Co robi uzytkownik: Wskazuje system.
Oczekiwane zachowanie systemu: Konwencje systemu uzupelniaja metadane i wlaczaja sekcje typowe dla systemu; nazwy warstw wyprowadzają...
Dlaczego to jest wymagane: Redukuje reczne uzupelnianie i utrzymuje spojnosc nazewnictwa.
### SC-03
Sytuacja: Podanie typu zrodla (np. txt, jdbc).
Co robi uzytkownik: Wybiera wariant zrodla.
Oczekiwane zachowanie systemu: Odkrywaja sie pola wymagane i pola opcjonalne aktywnego wariantu.
Dlaczego to jest wymagane: Uzytkownik musi znac legalny zakres biezacego wariantu.
### SC-04
Sytuacja: Zmiana systemu zrodlowego (sap -> rocket).
Co robi uzytkownik: Koryguje decyzje o systemie.
Oczekiwane zachowanie systemu: Wszystkie wartosci wyprowadzone przeliczaja sie; nic po poprzednim systemie nie zostaje.
Dlaczego to jest wymagane: Chroni kontrakt przed mieszaniem konwencji miedzy systemami.
### SC-05
Sytuacja: Zmiana typu zrodla (csv -> jdbc).
Co robi uzytkownik: Przelacza wariant.
Oczekiwane zachowanie systemu: Pola poprzedniego wariantu przestaja nalezec do kontraktu, sa usuwane i komunikowane jawnie.
Dlaczego to jest wymagane: Zapobiega utrzymywaniu nielegalnych pol pod pozorem poprawnosci.
### SC-06
Sytuacja: Uzytkownik wkleja gotowy kontrakt.
Co robi uzytkownik: Dostarcza wartosci bazowe.
Oczekiwane zachowanie systemu: Wklejone wartosci maja autorytet uzytkownika i wygrywaja z konwencjami.
Dlaczego to jest wymagane: Chroni intencje i umozliwia bezpieczna prace na istniejacym kontrakcie.
### SC-07
Sytuacja: "dodaj kolumne DATA_DANYCH w converter i w silver".
Co robi uzytkownik: Zada dopisania do istniejacych elementow.
Oczekiwane zachowanie systemu: Kolumna trafia do istniejacych elementow; nowa tabela nie powstaje.
Dlaczego to jest wymagane: To modyfikacja zawartosci, nie zmiana liczebnosci kolekcji.
### SC-08
Sytuacja: "dodaj kolejna tabele do silver" lub "kolejna tabele do converter".
Co robi uzytkownik: Zada utworzenia nowego elementu kolekcji.
Oczekiwane zachowanie systemu: Powstaje dokladnie jeden nowy element i tylko jego braki sa zglaszane.
Dlaczego to jest wymagane: Utrzymuje precyzyjna kontrole przyrostu kolekcji.
### SC-09
Sytuacja: "usun druga tabele silver".
Co robi uzytkownik: Usuwa wskazany element kolekcji.
Oczekiwane zachowanie systemu: Element znika, a wszystkie zadania dotyczace tego elementu milkna natychmiast.
Dlaczego to jest wymagane: Usuniety element nie moze dalej blokowac rozmowy.
### SC-10
Sytuacja: Wlaczenie sekcji opcjonalnej ("wlacz gold").
Co robi uzytkownik: Swiadomie rozszerza zakres kontraktu.
Oczekiwane zachowanie systemu: Pojawiaja sie wymagania i opcje tej sekcji, defaulty sa uzupelnione, konwencje dopisuja co potrafia, a nic poza ta sekcja.
Dlaczego to jest wymagane: Rozszerzenie zakresu nie moze psuc wczesniejszych ustalzen.
### SC-11
Sytuacja: Wlaczenie podopcji (unpack w preparatorze).
Co robi uzytkownik: Aktywuje podopcje.
Oczekiwane zachowanie systemu: Pojawia sie jej wlasne wymaganie (format).
Dlaczego to jest wymagane: Aktywna podopcja musi byc kompletna operacyjnie.
### SC-12
Sytuacja: Pytanie "co jeszcze moge uzupelnic?".
Co robi uzytkownik: Prosi o mape mozliwych uzupelnien.
Oczekiwane zachowanie systemu: Odpowiedz obejmuje takze sekcje niewlaczone; dokument nie zmienia sie ani o jote.
Dlaczego to jest wymagane: To pytanie o wiedze, nie polecenie zmiany.
### SC-13
Sytuacja: Pytanie "jakie sa typy zrodla?".
Co robi uzytkownik: Pyta o liste dopuszczalnych wartosci.
Oczekiwane zachowanie systemu: Odpowiedz pochodzi z listy dopuszczalnych wartosci; pytanie nie zmienia dokumentu.
Dlaczego to jest wymagane: Uzytkownik musi znac legalne opcje przed decyzja.
### SC-14
Sytuacja: Prosba o sekcje nieistniejaca w kontrakcie ("dodaj archiwizacje").
Co robi uzytkownik: Zada czegoś spoza modelu kontraktu.
Oczekiwane zachowanie systemu: Jasna informacja, ze kontrakt tego nie przewiduje; nic nie jest dopisywane.
Dlaczego to jest wymagane: Chroni granice produktu i zapobiega fikcyjnym konfiguracjom.
### SC-15
Sytuacja: Zada pola niedopuszczalnego w aktywnym wariancie (separator przy zrodle jdbc).
Co robi uzytkownik: Wpisuje pole nieadekwatne do aktywnego wariantu.
Oczekiwane zachowanie systemu: System nie blokuje wpisu z gory; wpis trafia do walidacji, zostaje odrzucony i usuniety, a uzytkownik dostaje przyczyne.
Dlaczego to jest wymagane: Uzytkownik ma prawo sie pomylic, a system ma obowiazek wydac jawny werdykt.
Uwaga: W obserwacjach live zdarzaly sie przebiegi z wczesniejszym blokowaniem.
### SC-16
Sytuacja: Rozbieznosc nazw o charakterze semantycznym (metadata "ferryt" vs kod zrodla "FERY").
Co robi uzytkownik: Podaje wartosci, ktore moga byc celowo rozne.
Oczekiwane zachowanie systemu: System moze co najwyzej zasygnalizowac podpowiedz; nigdy nie blokuje kontraktu i nigdy nie pyta o to wielokrotnie po potwierdzeniu.
Dlaczego to jest wymagane: Rozne identyfikatory moga byc legalna intencja biznesowa.
### SC-17
Sytuacja: Klucz glowny wskazuje nieistniejaca kolumne.
Co robi uzytkownik: Tworzy niespojnosc referencyjna.
Oczekiwane zachowanie systemu: Konkretny komunikat diagnostyczny wskazuje element i wartosc; system niczego nie podmienia po cichu.
Dlaczego to jest wymagane: Naprawa musi byc jednoznaczna i lokalna.
### SC-18
Sytuacja: Kontrakt kompletny i poprawny.
Co robi uzytkownik: Domyka wszystkie wymagania i usuwa bledy.
Oczekiwane zachowanie systemu: Uzytkownik dostaje gotowy YAML.
Dlaczego to jest wymagane: To finalny artefakt biznesowy.
### SC-19
Sytuacja: Kontrakt poprawny, ale niekompletny.
Co robi uzytkownik: Nie wypelnia wszystkich wymaganych wartosci.
Oczekiwane zachowanie systemu: Jawnie `valid` tak, `complete` nie oraz pelna lista brakow.
Dlaczego to jest wymagane: Poprawnosc formalna i gotowosc biznesowa musza byc rozdzielone.
### SC-20
Sytuacja: Kontrakt kompletny, ale niepoprawny.
Co robi uzytkownik: Wypelnia wszystkie wymagane pola, ale z bledami.
Oczekiwane zachowanie systemu: Jawnie `complete` tak, `valid` nie oraz lista bledow.
Dlaczego to jest wymagane: Kompletnosc bez poprawnosci nie wystarcza do bezpiecznego uzycia.
### SC-21
Sytuacja: Powrot do wartosci z wczesniejszej tury ("przywroc poprzednia wersje").
Co robi uzytkownik: Odwoluje sie do wczesniejszego materialu.
Oczekiwane zachowanie systemu: Material z wczesniejszych tur pozostaje uzyteczny i moze zostac przywrocony.
Dlaczego to jest wymagane: Rozmowa biznesowa jest iteracyjna i korekcyjna.
### SC-22
Sytuacja: Dostawa nowej wersji definicji kontraktu.
Co robi uzytkownik: Pracuje po aktualizacji definicji.
Oczekiwane zachowanie systemu: System dostosowuje sie bez zmian w kodzie.
Dlaczego to jest wymagane: Ewolucja kontraktu ma byc sterowana danymi, nie kodem.

## 7. Przypadki brzegowe
### EC-01
Sytuacja: Typ zrodla nieustalony.
Wymagane zachowanie: Jedyne pytanie o zrodlo dotyczy samego typu.
Skutek gdyby zachowanie pominac: Pojawiaja sie pytania o pola wariantowe bez podstawy.
### EC-02
Sytuacja: Element kolekcji wypelniony czesciowo (podano pozycje startowa, brak koncowej).
Wymagane zachowanie: Dopytujemy tylko o brakujace pola TEGO samego wariantu.
Skutek gdyby zachowanie pominac: System pyta o nie ten wariant i blokuje domkniecie.
### EC-03
Sytuacja: Zapis do kolekcji pod indeks wiekszy niz jej dlugosc.
Wymagane zachowanie: To blad; indeks rowny dlugosci oznacza dopisanie nowego elementu.
Skutek gdyby zachowanie pominac: Powstaja luki i przypadkowe elementy.
### EC-04
Sytuacja: Konwencja biznesowa celuje w miejsce nieosiagalne w aktualnym ksztalcie.
Wymagane zachowanie: Taka konwencja jest pomijana bez sladu w dokumencie.
Skutek gdyby zachowanie pominac: Dokument zawiera wartosci nielegalne dla aktywnego ksztaltu.
### EC-05
Sytuacja: Dwie konwencje celuja w to samo miejsce.
Wymagane zachowanie: Rozstrzygniecie jest deterministyczne i powtarzalne.
Skutek gdyby zachowanie pominac: Uzytkownik obserwuje losowe przeskoki wartosci.
### EC-06
Sytuacja: Konwencja i uzytkownik podaja rozne wartosci dla tego samego miejsca.
Wymagane zachowanie: Uzytkownik wygrywa i pozostaje autorytatywny w kolejnych turach.
Skutek gdyby zachowanie pominac: System nadpisuje decyzje uzytkownika.
### EC-07
Sytuacja: Uzytkownik zmienia wartosc pochodzaca z konwencji i robi to kilkukrotnie.
Wymagane zachowanie: Obowiazuje ostatnia decyzja uzytkownika.
Skutek gdyby zachowanie pominac: System wraca do konwencji mimo jawnej zmiany.
### EC-08
Sytuacja: Regula w definicji kontraktu, ktorej nie da sie sprawdzic z samej definicji.
Wymagane zachowanie: Jest pomijana, bo weryfikuje ja inny etap poza ta aplikacja.
Skutek gdyby zachowanie pominac: Powstaja pozorne bledy bez mozliwosci rozstrzygniecia.
### EC-09
Sytuacja: Definicja kontraktu miesza konwencje nazewnicze sciezek.
Wymagane zachowanie: Musi byc zrozumiana mimo tej niespojnosci.
Skutek gdyby zachowanie pominac: Aktualizacja definicji powoduje regresje bez zmiany sensu.
### EC-10
Sytuacja: Uzgadnianie w jednej turze nie zbiega.
Wymagane zachowanie: Tura i tak konczy sie jedna odpowiedzia i widocznym sygnalem braku zbieznosci.
Skutek gdyby zachowanie pominac: Uzytkownik czeka bez konca albo dostaje niejawnie niepelny wynik.
### EC-11
Sytuacja: Propozycja wartosci o niskiej pewnosci.
Wymagane zachowanie: Nie trafia do dokumentu, a fakt odrzucenia jest odtwarzalny w strumieniu zdarzen AUDIT.
Skutek gdyby zachowanie pominac: Slabe wartosci trafiaja do kontraktu bez sladu.
### EC-12
Sytuacja: Puste sekcje/obiekty.
Wymagane zachowanie: Puste obiekty nie moga trafic do dokumentu jako skutek uboczny;
wyjatkiem jest swiadoma aktywacja sekcji opcjonalnej, gdzie pusty obiekt jest nosnikiem aktywacji i jest oczekiwany.
Skutek gdyby zachowanie pominac: Puste szkielety zaciemniaja stan i maskuja realne dane, albo blokowana jest legalna aktywacja sekcji.
### EC-13
Sytuacja: Uzytkownik podaje szczegoly zrodla, zanim ustalono typ.
Wymagane zachowanie: Najpierw ustalany jest typ, a wlasciwe pola trafiaja na miejsce w tej samej turze.
Skutek gdyby zachowanie pominac: Poprawne dane sa odrzucane tylko przez kolejnosc wypowiedzi.

## 8. Funkcje pozornie nadmiarowe i ich uzasadnienie
### J-01
Wyglada na nadmiarowe: Rozdzielenie `valid` i `complete`.
W rzeczywistosci wymusza to: SC-19, SC-20.
Skutek usuniecia: Brak rozroznienia poprawnosci od gotowosci.
### J-02
Wyglada na nadmiarowe: Pamietanie pochodzenia kazdej wartosci.
W rzeczywistosci wymusza to: SC-04, SC-06, EC-06, EC-07.
Skutek usuniecia: Nie da sie bezpiecznie rozstrignac autorytetu wartosci.
### J-03
Wyglada na nadmiarowe: Wielokrotne odpytywanie Forge w jednej turze.
W rzeczywistosci wymusza to: SC-02+SC-03, EC-13.
Skutek usuniecia: Brak stabilizacji przed odpowiedzia dla uzytkownika.
### J-04
Wyglada na nadmiarowe: Jawne zglaszanie wartosci obcych zamiast cichego ignorowania.
W rzeczywistosci wymusza to: SC-05, SC-15.
Skutek usuniecia: Obce wartosci pozostaja ukryte i wracaja jako pozne defekty.
### J-05
Wyglada na nadmiarowe: Rozroznienie "dopisz do istniejacego" vs "utworz nowy".
W rzeczywistosci wymusza to: SC-07, SC-08, EC-03.
Skutek usuniecia: Kolekcje rosna przypadkiem i generuja sztuczne braki.
### J-06
Wyglada na nadmiarowe: Zwracanie sekcji jeszcze niewlaczonych.
W rzeczywistosci wymusza to: SC-12, SC-14.
Skutek usuniecia: Uzytkownik nie zna pelnej mapy mozliwych dzialan.
### J-07
Wyglada na nadmiarowe: Szczegolowy zapis przebiegu tury.
W rzeczywistosci wymusza to: Historycznie bez tego defekty byly niediagnozowalne; odtwarzalnosc przebiegu jest konieczna.
Skutek usuniecia: Powrot defektow bez mozliwosti ustalenia przyczyny.
### J-08
Wyglada na nadmiarowe: Zakaz oceny semantycznej po stronie Forge.
W rzeczywistosci wymusza to: SC-16.
Skutek usuniecia: Deterministyczna walidacja zaczyna blokowac legalne rozbieznosci.
### J-09
Wyglada na nadmiarowe: Normalizacja definicji kontraktu przy jej wczytaniu.
W rzeczywistosci wymusza to: EC-09, SC-22.
Skutek usuniecia: Niespojnosci nazewnicze destabilizuja zachowanie.
### J-10
Wyglada na nadmiarowe: Traktowanie konwencji biznesowych jako regul, a nie pamieci o wyborach uzytkownika.
W rzeczywistosci wymusza to: 4.4, EC-06.
Skutek usuniecia: Reguly emuluja pamiec sesji i tworza konflikt autorytetu.

## 9. Decyzje produktowe (potwierdzone)
### D-01
Decyzja: Forge zawsze zwraca wszystkie braki naraz; dawkowanie pytan to rola ADCM.
Uzasadnienie: Pelny stan kontraktu i strategia rozmowy musza miec roznych wlascicieli.
Uwaga: W czesci przebiegow live obserwowano etapowe ujawnianie brakow.
Doprecyzowanie: pojedyncze pytanie kotwiczace nie zmienia faktu, ze blok `[brak]` opiera sie o pelny zbior `missing`.
### D-02
Decyzja: Wartosci obce sa usuwane automatycznie, ale uzytkownik ZAWSZE dostaje komunikat
"usunieto X, poniewaz nie wystepuje przy wybranym wariancie Y".
Uzasadnienie: Zapewnia formalna czystosc kontraktu i swiadomosc skutku po stronie uzytkownika.
Doprecyzowanie: kazdy element `foreign` niesie zawsze `reason` i `admissible_fields`,
dzieki czemu komunikat usuniecia zawsze wskazuje aktywny wariant i dozwolone pola.
### D-03
Decyzja: `complete` obejmuje sekcje wymagane i te opcjonalne, ktore sa swiadomie wlaczone; sekcje niewlaczone nie czynia kontraktu niekompletnym.
Za swiadomie wlaczone uznajemy sekcje wlaczone bezposrednio przez uzytkownika ORAZ sekcje wynikajace z zadeklarowanego systemu zrodlowego.
Uzasadnienie: Kompletnosc ma odzwierciedlac wybrany zakres biznesowy.
### D-04
Decyzja: Dopuszczalna jest wielokrotna liczba tabel w silver i wpisow w gold; nie wolno tego ograniczac, trzeba umiec element usunac i dodac.
Uzasadnienie: Realne przypadki biznesowe wymagaja kolekcji wieloelementowych i precyzyjnych operacji.
### D-05
Decyzja: Weryfikacja semantyczna (literowki, rozbiezne nazwy) jest opcjonalnym, wylacznym dodatkiem po stronie ADCM; nigdy nie blokuje kontraktu.
Uzasadnienie: To sygnal doradczy, nie werdykt formalny.
### D-06
Decyzja: Uzytkownik moze wpisac dowolna wartosc, takze bledna; system nie blokuje jej z gory, tylko pokazuje werdykt walidacji.
Uzasadnienie: Jawny werdykt po probie zapisu jest bardziej uzyteczny niz blokada prewencyjna.
Uwaga: W obserwacjach live zdarzaly sie przypadki wczesniejszego blokowania.

## 10. Swiadomosc poza zakresem
Po stronie ADCM:
- brak trwalego magazynu decyzji uzytkownika jako osobnego bytu,
- brak blokujacych pytan potwierdzajacych jako obowiazkowego etapu.
Po stronie Forge:
- brak rozmowy,

- brak LLM,
- brak stanu,
- brak porownan semantycznych,
- brak dawkowania pytan.
Po stronie wspolnej:
- generowanie samego pipeline'u i DAG-ow jest poza zakresem.
Znaczenie biznesowe:
- utrzymanie ostrych granic odpowiedzialnosci,
- ograniczenie dryfu zakresu,
- brak mylenia roli doradczej i roli formalnej.

## 11. Kryteria akceptacji biznesowej
| ID | Obserwowalny skutek |
|---|---|
| SC-01 | Po ogolnym starcie system zadaje jedno pytanie kotwiczace, nie cala liste pytan. |
| SC-02 | Po podaniu systemu pojawiaja sie wartosci wyprowadzone i nazwy warstw zgodne z systemem. |
| SC-03 | Po wyborze typu zrodla wymagania i opcje dotycza tylko aktywnego wariantu. |
| SC-04 | Po zmianie systemu znikaja wszystkie wartosci wyprowadzone dla starego systemu. |
| SC-05 | Po zmianie typu zrodla pola starego wariantu sa usuniete i jawnie zakomunikowane. |
| SC-06 | Po wklejeniu kontraktu wartosci z wklejki pozostaja i nie sa nadpisywane konwencjami. |
| SC-07 | Polecenie dopisania kolumny aktualizuje istniejace elementy bez tworzenia nowej tabeli. |
| SC-08 | Polecenie dodania kolejnej tabeli tworzy dokladnie jeden nowy element i raportuje tylko jego braki. |
| SC-09 | Po usunieciu elementu kolekcji system nie raportuje juz brakow tego elementu. |
| SC-10 | Wlaczenie sekcji opcjonalnej uruchamia jej wymagania i nie modyfikuje innych sekcji. |
| SC-11 | Wlaczenie podpogcji powoduje pojawienie sie jej wlasnego wymagania. |
| SC-12 | Pytanie o dalsze uzupelnienia obejmuje tez sekcje niewlaczone i nie zmienia dokumentu. |
| SC-13 | Pytanie o typy zrodla zwraca liste dozwolonych wartosci bez zapisu do dokumentu. |
| SC-14 | Prosba o sekcje spoza kontraktu daje jasna odmowe i nie dodaje nowych pol. |
| SC-15 | Wpis pola niedopuszczalnego konczy sie odrzuceniem, usunieciem i komunikatem o legalnych polach. |
| SC-16 | Rozbieznosc semantyczna moze byc zasygnalizowana, ale nie blokuje i nie wraca po potwierdzeniu. |
| SC-17 | Bledny klucz glowny daje diagnostyke wskazujaca konkretny element i wartosc. |
| SC-18 | Dla kontraktu kompletnego i poprawnego uzytkownik otrzymuje gotowy YAML. |
| SC-19 | Dla kontraktu poprawnego, ale niekompletnego status pokazuje `valid` tak i `complete` nie oraz pelna liste brakow. |
| SC-20 | Dla kontraktu kompletnego, ale niepoprawnego status pokazuje `complete` tak i `valid` nie oraz liste bledow. |
| SC-21 | Polecenie przywrocenia wczesniejszej wartosci odtwarza wartosc z materialu wczesniejszej tury. |
| SC-22 | Po dostawie nowej definicji kontraktu system dostosowuje sie bez zmian w kodzie. |
| D-01 | Forge zwraca pelna liste brak naraz, a ADCM decyduje o kolejnosci ich prezentacji w rozmowie. |
| D-05 | Doradztwo semantyczne jest opcjonalne i wylaczne; nigdy nie blokuje i nie obniza formalnego statusu kontraktu. |
| D-06 | Uzytkownik moze wpisac wartosc nawet bledna; system pokazuje jawny werdykt walidacji zamiast blokady prewencyjnej. |