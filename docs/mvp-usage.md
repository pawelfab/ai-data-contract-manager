# Scenariusz użycia MVP

Przykładowa pierwsza wiadomość:

> Źródłem jest CSV w
> `gs://raw-zone/accounts/accounts_2026-07-27.csv`. Ma kolumny `account_id`
> STRING wymagane i `balance` NUMERIC. Ładujemy tylko do Bronze, a kolumny
> mają zostać takie same. Projekt `acme-data-prod`, dataset `bronze_finance`,
> tabela `customer_accounts`. Pipeline `customer_accounts_daily`.

Oczekiwany przebieg:

1. Agent rozpoznaje `csv` i `bronze`.
2. Pobiera aktywny katalog MCP.
3. Zapisuje jawne fakty do draftu.
4. Pokazuje nierozstrzygnięte opcje CSV i Bronze wraz z przykładami.
5. Użytkownik może odpowiedzieć np.:

   > Separator średnik, plik ma nagłówek. Pozostałych opcji nie uzupełniaj.

6. Agent aktualizuje draft i wysyła go do walidacji MCP.
7. Po sukcesie MCP generuje YAML preview.
8. Web UI pokazuje wbudowane zatwierdzenie narzędzia końcowego.
9. Zatwierdzenie utrwala wersję jako `last_valid_rendered_yaml`.

Przykładowa późniejsza poprawka:

> Zmień nazwę tabeli Bronze na `customer_accounts_v2`.

Agent aktualizuje tylko `targets.bronze.table.table`, ponownie waliduje
i przygotowuje nowy YAML. Poprzedni YAML pozostaje ostatnią zatwierdzoną wersją
do czasu zaakceptowania nowej.
