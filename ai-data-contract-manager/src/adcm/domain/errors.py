"""Błędy domenowe ADCM.

Warstwa domenowa nazywa tu sytuacje, które warstwy zewnętrzne muszą rozróżnić — nie
znając przy tym transportu. Adapter HTTP mapuje je na statusy, adapter CLI mógłby na
kody wyjścia; żadne z tych mapowań nie należy do tego modułu.

Moduł celowo nie ma zależności, dzięki czemu jest importowalny z każdej warstwy.
"""


class AdcmError(Exception):
    """Wspólna baza dla błędów, które ADCM nazywa świadomie."""


class SessionNotFoundError(AdcmError):
    """Żądana sesja nie istnieje.

    Odróżnia brak zasobu od pustej sesji: `SessionRepositoryPort.get_or_create`
    milcząco tworzy sesję, więc odczyt musi mieć własną, jawną sygnalizację braku.
    """


class ForgeUnavailableError(AdcmError):
    """Contract Forge jest chwilowo nieosiągalny.

    Dotyczy niedostępności usługi — transportu, błędu narzędzia MCP lub braku
    odpowiedzi — a nie niezgodności protokołu, która jest defektem i propaguje dalej.
    """
