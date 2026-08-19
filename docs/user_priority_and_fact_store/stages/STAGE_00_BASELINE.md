# STAGE 00 — baseline i zabezpieczenie obecnego działania

## GOAL

Przed zmianami potwierdzić rzeczywisty stan repo i zablokować regresję podstawowego stair-step flow.

Ten stage ma być mały. Nie dodaje nowych funkcjonalności.

## READ FIRST

Przeczytaj:
- `AGENTS.md`
- `docs/CURRENT_STATE.md`
- `docs/ADCM_CONTEXT.md`
- `docs/ARCHITECTURE.md`
- `docs/DECISIONS.md`

Następnie przejrzyj rzeczywisty kod:
- `src/adcm/orchestrator.py`
- `src/adcm/models.py`
- `src/adcm/heuristics.py`
- `src/adcm/semantic.py`
- `src/contract_forge/engine.py`
- `src/contract_forge/models.py`
- `src/contract_forge/schema.py`
- istniejące testy.

Jeśli nazwy/pliki różnią się od dokumentacji, dostosuj zadanie do repo i zapisz różnicę w `CURRENT_STATE.md`.

## BOUNDARY

Ten stage tylko:
- uruchamia testy;
- dokumentuje baseline;
- dodaje brakujące testy regresyjne obecnego poprawnego flow, jeśli ich nie ma.

## NON-GOALS

Nie implementuj jeszcze:
- precedence;
- override enrichmentu;
- UserFact store;
- zmian LLM;
- nowych parserów;
- nowych schema capabilities;
- refactoru klas.

## TODO

1. Uruchom pełny obecny test suite.
2. Zapisz wynik.
3. Upewnij się, że istnieje test potwierdzający:
   - pierwsze requirement to source system;
   - po jego rozwiązaniu Forge odkrywa następne pole;
   - orchestrator potrafi wykonać co najmniej 2 automatyczne kroki bez pytania usera, jeśli dane są już w historii;
   - canonical contract jest własnością Forge, nie ADCM;
   - transcript/history jest własnością ADCM, nie Forge.
4. Jeśli testu brakuje, dodaj minimalny test regresyjny bez zmiany produkcyjnej logiki.
5. Nie zmieniaj architektury tylko po to, aby test był łatwiejszy.
6. Zaktualizuj `docs/CURRENT_STATE.md`:
   - baseline tests;
   - znane problemy;
   - pliki faktycznie odpowiedzialne za flow.

## ACCEPTANCE TESTS

Minimum:
- istniejący test suite przechodzi;
- nowy/istniejący stair-step regression test przechodzi;
- brak zmian behavior poza testami/dokumentacją.

## DONE WHEN

Stage kończy się, gdy znamy rzeczywisty baseline i mamy test chroniący obecny poprawny loop.

## STOP

Nie implementuj Stage 01 ani dalszych.
