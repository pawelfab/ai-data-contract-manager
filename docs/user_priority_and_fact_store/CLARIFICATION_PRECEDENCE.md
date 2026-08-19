# CLARIFICATION — recency USER vs precedence originów

Ta wersja stage planu rozdziela dwa wcześniej częściowo zmieszane mechanizmy.

## ADCM owns user recency

ADCM posiada transcript i UserFact store.

Dlatego ADCM rozstrzyga:

```text
nowsza informacja USER > starsza informacja USER
```

na podstawie `message_sequence`.

Forge nie analizuje transcriptu.

## Contract Forge owns value-source precedence

Forge posiada canonical contract, enrichmenty i schema defaults.

Dlatego Forge rozstrzyga:

```text
USER
>
SYSTEM_ENRICHMENT
>
GENERIC_ENRICHMENT
>
SCHEMA_DEFAULT
```

## LLM

LLM nie jest osobnym biznesowym originem.

Jeśli LLM wydobył wartość z wypowiedzi usera:

```text
origin = USER
extraction_method = LLM
```

## Consequence for implementation

Do Forge powinien trafić już aktualny USER candidate wybrany przez ADCM.

Jeżeli current contract ma wartość z enrichment/default:
- Forge może ją zastąpić USER candidate.

Jeżeli current contract ma wcześniejszą wartość USER:
- ADCM odpowiada za to, aby wysłany candidate reprezentował aktualną intencję usera;
- Forge może przyjąć nowy poprawny USER submit;
- Forge nie musi porównywać historycznych wiadomości.
