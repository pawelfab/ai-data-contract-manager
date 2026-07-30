# Scenariusz użycia MVP

Przykładowa pierwsza wiadomość:

> Źródłem jest CSV w
> `gs://raw-zone/accounts/accounts_2026-07-27.csv`. Ma kolumny `account_id`
> STRING wymagane i `balance` NUMERIC. Ładujemy tylko do Bronze, a kolumny
> mają zostać takie same. Projekt `acme-data-prod`, dataset `bronze_finance`,
> tabela `customer_accounts`. Pipeline `customer_accounts_daily`, właściciel
> `data-platform`, wersja `1.0.0`, uruchomienie codziennie o 06:00.

Oczekiwany przebieg:

1. Agent rozpoznaje `csv` i `bronze` bez dodatkowego potwierdzania.
2. Pobiera z MCP aktywny katalog dla CSV i Bronze.
3. Dopasowuje informacje z całej rozmowy i zapisuje jawne fakty do draftu.
4. Pokazuje brakujące wymagane wartości oraz nierozstrzygnięte opcje wraz
   z opisami i przykładami.
5. Użytkownik może odpowiedzieć:

   > Separator średnik, plik nie ma nagłówka. Kodowanie UTF-8, bez kompresji.
   > Pozostałych opcji nie uzupełniaj.

6. Agent zapisuje patch i `evidence_text`.
7. Po uzupełnieniu wymaganych wartości draft trafia do walidacji MCP.
8. Po sukcesie MCP generuje YAML preview.
9. Agent pokazuje cały YAML i kończy turę pytaniem o zatwierdzenie.
10. Dopiero odpowiedź użytkownika w kolejnej turze, np. „tak, zatwierdzam”,
    uruchamia `approve_final_yaml`.

Nie jest używane drugie, techniczne zatwierdzenie `requires_approval`.

Przykładowa późniejsza poprawka:

> Zmień nazwę tabeli Bronze na `customer_accounts_v2`.

Agent aktualizuje `targets.bronze.table.table`, ponownie waliduje kontrakt
i przygotowuje nowy YAML. Poprzedni zatwierdzony YAML pozostaje dostępny do
chwili zatwierdzenia nowej wersji.
