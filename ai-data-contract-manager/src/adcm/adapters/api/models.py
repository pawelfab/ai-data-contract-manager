"""Publiczne modele REST API ADCM.

Kontrakt publiczny jest projektowany dla klienta, nie jako odbicie modeli domenowych.
Odpowiedź tury niesie dokładnie to, co interfejs musi pokazać: co odpowiedzieć
użytkownikowi, jaki jest dokument, jaki ma status, czego brakuje, czego ADCM nie
zrozumiał i co zmieniło się w tej turze.

Świadomie nie są tu wystawione: `writable`, `foreign`, `proposals`, przebieg
stabilizacji, external checks, `provenance`, `mutation_log` oraz identyfikatory i
rewizje mutacji. Pełna historia pozostaje w Session Audit, a pełny stan wewnętrzny
w opcjonalnym debug endpoincie.
"""

from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

MESSAGE_MAX_LENGTH = 10_000


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str
    service: str


class ErrorBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    message: str
    correlation_id: str | None = None


class ErrorResponse(BaseModel):
    """Jeden kształt dla każdego błędu API, niezależnie od statusu."""

    model_config = ConfigDict(extra="forbid")
    error: ErrorBody


class ContractStatusView(BaseModel):
    model_config = ConfigDict(extra="forbid")
    valid: bool
    complete: bool
    clean: bool


class MissingItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str
    code: str
    message: str | None = None


class DiagnosticItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    path: str | None = None
    severity: str
    message: str


class UnresolvedItem(BaseModel):
    """Fragment wypowiedzi, którego ADCM nie odwzorował na kontrakt."""

    model_config = ConfigDict(extra="forbid")
    intent: str | None = None
    reason: str | None = None


class ChangeItem(BaseModel):
    """Kompaktowy widok mutacji z bieżącej tury.

    Bez `mutation_id`, `producer_id`, `source` i rewizji — te należą do audytu.
    """

    model_config = ConfigDict(extra="forbid")
    operation: str
    path: str
    old_value: Any = None
    new_value: Any = None


class CreateSessionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str
    turn_no: int
    status: str


class SessionStateResponse(BaseModel):
    """Stan sesji po ostatniej zakończonej turze.

    `contract_status` jest `null` dla sesji, w której nie odbyła się jeszcze żadna
    tura — nie ma wtedy dokumentu, który Forge mógłby ocenić.
    """

    model_config = ConfigDict(extra="forbid")
    session_id: str
    turn_no: int
    document: dict
    contract_status: ContractStatusView | None = None
    missing: list[MissingItem] = Field(default_factory=list)
    diagnostics: list[DiagnosticItem] = Field(default_factory=list)


class TurnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=MESSAGE_MAX_LENGTH),
    ]


class TurnResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str
    turn_no: int
    message: str
    document: dict
    contract_status: ContractStatusView
    missing: list[MissingItem] = Field(default_factory=list)
    diagnostics: list[DiagnosticItem] = Field(default_factory=list)
    unresolved: list[UnresolvedItem] = Field(default_factory=list)
    changes: list[ChangeItem] = Field(default_factory=list)
    correlation_id: str | None = None
