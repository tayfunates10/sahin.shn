from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Mapping, Protocol, Sequence
from urllib.parse import unquote

from .capabilities import Capability, CapabilitySet


class ServerDataError(ValueError):
    """Şahin sunucu/veri katmanı için yapılandırılmış hata."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


@dataclass(frozen=True, slots=True)
class HttpRequest:
    method: HttpMethod
    path: str
    query: Mapping[str, str] = field(default_factory=dict)
    body: Any = None


@dataclass(frozen=True, slots=True)
class HttpResponse:
    status: int
    body: Any
    headers: Mapping[str, str] = field(default_factory=lambda: {"content-type": "application/json; charset=utf-8"})


Validator = Callable[[Any], Any]


@dataclass(frozen=True, slots=True)
class Endpoint:
    method: HttpMethod
    path: str
    handler: Callable[[Mapping[str, str], Mapping[str, str], Any], HttpResponse]
    path_validators: Mapping[str, Validator] = field(default_factory=dict)
    query_validators: Mapping[str, Validator] = field(default_factory=dict)
    body_validator: Validator | None = None


class Router:
    def __init__(self, endpoints: Sequence[Endpoint]) -> None:
        self._endpoints = tuple(endpoints)

    def dispatch(self, request: HttpRequest) -> HttpResponse:
        for endpoint in self._endpoints:
            if endpoint.method is not request.method:
                continue
            params = _match_path(endpoint.path, request.path)
            if params is None:
                continue
            params = _validate_fields(endpoint.path_validators, params, "SHN-H006", "yol parametresi")
            query = _validate_fields(endpoint.query_validators, request.query, "SHN-H004", "sorgu alanı")
            body = request.body
            if endpoint.body_validator is not None:
                try:
                    body = endpoint.body_validator(request.body)
                except (TypeError, ValueError) as exc:
                    raise ServerDataError("SHN-H005", "Geçersiz istek gövdesi.") from exc
            return endpoint.handler(params, query, body)
        return HttpResponse(404, {"hata": {"kod": "SHN-H404", "mesaj": "Uç bulunamadı."}})


def _match_path(pattern: str, path: str) -> dict[str, str] | None:
    if not pattern.startswith("/") or not path.startswith("/"):
        raise ServerDataError("SHN-H001", "Yol '/' ile başlamalıdır.")
    expected = [piece for piece in pattern.split("/") if piece]
    actual = [piece for piece in path.split("/") if piece]
    if len(expected) != len(actual):
        return None
    params: dict[str, str] = {}
    for wanted, received in zip(expected, actual, strict=True):
        value = unquote(received)
        if wanted.startswith("{") and wanted.endswith("}"):
            name = wanted[1:-1].strip()
            if not name or value in {".", ".."} or "/" in value or "\\" in value:
                raise ServerDataError("SHN-H002", "Geçersiz yol parametresi.")
            params[name] = value
        elif wanted != value:
            return None
    return params


def _validate_fields(
    validators: Mapping[str, Validator],
    values: Mapping[str, Any],
    invalid_code: str,
    label: str,
) -> dict[str, Any]:
    validated: dict[str, Any] = dict(values)
    for name, validator in validators.items():
        if name not in values:
            raise ServerDataError("SHN-H003", f"Zorunlu {label} eksik: {name}")
        try:
            validated[name] = validator(values[name])
        except (TypeError, ValueError) as exc:
            raise ServerDataError(invalid_code, f"Geçersiz {label}: {name}") from exc
    return validated


class QueryOp(str, Enum):
    EQ = "eşit"
    NE = "eşit_değil"
    LT = "küçük"
    LTE = "küçük_eşit"
    GT = "büyük"
    GTE = "büyük_eşit"


@dataclass(frozen=True, slots=True)
class Filter:
    field: str
    op: QueryOp
    value: Any

    def __post_init__(self) -> None:
        _safe_identifier(self.field)


@dataclass(frozen=True, slots=True)
class QueryIR:
    model: str
    fields: tuple[str, ...] = ()
    filters: tuple[Filter, ...] = ()
    limit: int = 100

    def __post_init__(self) -> None:
        _safe_identifier(self.model)
        for field_name in self.fields:
            _safe_identifier(field_name)
        if self.limit < 1 or self.limit > 1000:
            raise ServerDataError("SHN-D003", "Sorgu limiti 1..1000 aralığında olmalıdır.")


@dataclass(frozen=True, slots=True)
class BackendFilter:
    field: str
    op: QueryOp
    parameter_index: int


@dataclass(frozen=True, slots=True)
class BackendQuery:
    """Host adapterına taşınan, SQL metni içermeyen parametreli sorgu sözleşmesi."""

    model: str
    fields: tuple[str, ...]
    filters: tuple[BackendFilter, ...]
    parameters: tuple[Any, ...]
    limit: int


def compile_backend_query(query: QueryIR) -> BackendQuery:
    parameters = tuple(item.value for item in query.filters)
    filters = tuple(
        BackendFilter(item.field, item.op, index)
        for index, item in enumerate(query.filters)
    )
    return BackendQuery(query.model, query.fields, filters, parameters, query.limit)


@dataclass(frozen=True, slots=True)
class ModelField:
    name: str
    type_name: str
    nullable: bool = False

    def __post_init__(self) -> None:
        _safe_identifier(self.name)
        _safe_identifier(self.type_name)


@dataclass(frozen=True, slots=True)
class ModelMeta:
    name: str
    fields: tuple[ModelField, ...]

    def __post_init__(self) -> None:
        _safe_identifier(self.name)
        names = [item.name for item in self.fields]
        if len(names) != len(set(names)):
            raise ServerDataError("SHN-M001", "Model alan adları yinelenemez.")


class MigrationKind(str, Enum):
    CREATE_MODEL = "model_oluştur"
    ADD_FIELD = "alan_ekle"
    REMOVE_FIELD = "alan_kaldır"


@dataclass(frozen=True, slots=True)
class MigrationStep:
    version: int
    kind: MigrationKind
    model: str
    field: ModelField | None = None

    def __post_init__(self) -> None:
        if self.version < 1:
            raise ServerDataError("SHN-M002", "Migration sürümü pozitif olmalıdır.")
        _safe_identifier(self.model)
        if self.kind is not MigrationKind.CREATE_MODEL and self.field is None:
            raise ServerDataError("SHN-M003", "Alan migration adımında alan metadata zorunludur.")


@dataclass(frozen=True, slots=True)
class MigrationPlan:
    steps: tuple[MigrationStep, ...]

    def __post_init__(self) -> None:
        versions = [step.version for step in self.steps]
        if versions != sorted(versions) or len(versions) != len(set(versions)):
            raise ServerDataError("SHN-M004", "Migration sürümleri benzersiz ve artan olmalıdır.")


def _safe_identifier(value: str) -> None:
    if not value or not value.replace("_", "").isalnum() or not value[0].isalpha():
        raise ServerDataError("SHN-D001", f"Geçersiz veri tanımlayıcısı: {value!r}")


class DataAdapter(Protocol):
    def execute(self, query: BackendQuery) -> Sequence[Mapping[str, Any]]: ...

    def begin(self) -> "TransactionAdapter": ...


class TransactionAdapter(Protocol):
    def execute(self, query: BackendQuery) -> Sequence[Mapping[str, Any]]: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


@dataclass(slots=True)
class DataEngine:
    adapter: DataAdapter
    capabilities: CapabilitySet

    def read(self, query: QueryIR) -> Sequence[Mapping[str, Any]]:
        self.capabilities.require(Capability.VERI_OKU)
        return self.adapter.execute(compile_backend_query(query))

    def transaction(self, action: Callable[[TransactionAdapter], Any]) -> Any:
        self.capabilities.require(Capability.VERI_YAZ)
        tx = self.adapter.begin()
        try:
            result = action(tx)
        except BaseException:
            tx.rollback()
            raise
        try:
            tx.commit()
        except BaseException:
            tx.rollback()
            raise
        return result
