from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

import pytest

from sahin.capabilities import Capability, CapabilityError, CapabilitySet
from sahin.server_data import (
    BackendQuery,
    DataEngine,
    Endpoint,
    Filter,
    HttpMethod,
    HttpRequest,
    HttpResponse,
    MigrationKind,
    MigrationPlan,
    MigrationStep,
    ModelField,
    ModelMeta,
    QueryIR,
    QueryOp,
    Router,
    ServerDataError,
    compile_backend_query,
)


def test_router_matches_path_and_validates_query() -> None:
    router = Router(
        [
            Endpoint(
                HttpMethod.GET,
                "/kullanicilar/{id}",
                lambda params, query, body: HttpResponse(200, {"id": params["id"], "sayfa": query["sayfa"]}),
                query_validators={"sayfa": lambda value: str(int(value))},
            )
        ]
    )

    response = router.dispatch(HttpRequest(HttpMethod.GET, "/kullanicilar/42", {"sayfa": "2"}))

    assert response.status == 200
    assert response.body == {"id": "42", "sayfa": "2"}


def test_router_validates_path_and_body() -> None:
    router = Router(
        [
            Endpoint(
                HttpMethod.POST,
                "/urunler/{id}",
                lambda params, query, body: HttpResponse(200, {"id": params["id"], "ad": body["ad"]}),
                path_validators={"id": lambda value: int(value)},
                body_validator=lambda body: {"ad": str(body["ad"]).strip()} if body["ad"] else (_ for _ in ()).throw(ValueError()),
            )
        ]
    )

    response = router.dispatch(HttpRequest(HttpMethod.POST, "/urunler/42", body={"ad": " Kalem "}))
    assert response.body == {"id": 42, "ad": "Kalem"}

    with pytest.raises(ServerDataError, match="SHN-H006"):
        router.dispatch(HttpRequest(HttpMethod.POST, "/urunler/x", body={"ad": "Kalem"}))
    with pytest.raises(ServerDataError, match="SHN-H005"):
        router.dispatch(HttpRequest(HttpMethod.POST, "/urunler/42", body={"ad": ""}))


def test_router_rejects_encoded_path_traversal() -> None:
    router = Router([Endpoint(HttpMethod.GET, "/dosya/{ad}", lambda *_: HttpResponse(200, {}))])

    with pytest.raises(ServerDataError, match="SHN-H002"):
        router.dispatch(HttpRequest(HttpMethod.GET, "/dosya/%2E%2E"))


def test_router_returns_structured_not_found() -> None:
    response = Router([]).dispatch(HttpRequest(HttpMethod.GET, "/yok"))

    assert response.status == 404
    assert response.body["hata"]["kod"] == "SHN-H404"


def test_query_ir_rejects_sql_shaped_identifiers_and_unbounded_limits() -> None:
    with pytest.raises(ServerDataError, match="SHN-D001"):
        QueryIR("users; DROP TABLE users")
    with pytest.raises(ServerDataError, match="SHN-D003"):
        QueryIR("kullanici", limit=1001)


def test_query_values_remain_structured_parameters() -> None:
    payload = "' OR 1=1 --"
    query = QueryIR("kullanici", fields=("ad",), filters=(Filter("ad", QueryOp.EQ, payload),))
    backend = compile_backend_query(query)

    assert backend.parameters == (payload,)
    assert backend.filters[0].parameter_index == 0
    assert backend.filters[0].field == "ad"
    assert not isinstance(backend, str)


def test_model_metadata_and_migration_plan_are_structured() -> None:
    model = ModelMeta("urun", (ModelField("ad", "yazi"), ModelField("stok", "sayi")))
    plan = MigrationPlan(
        (
            MigrationStep(1, MigrationKind.CREATE_MODEL, model.name),
            MigrationStep(2, MigrationKind.ADD_FIELD, model.name, ModelField("fiyat", "para")),
        )
    )

    assert plan.steps[1].field is not None
    assert plan.steps[1].field.name == "fiyat"

    with pytest.raises(ServerDataError, match="SHN-M001"):
        ModelMeta("urun", (ModelField("ad", "yazi"), ModelField("ad", "yazi")))
    with pytest.raises(ServerDataError, match="SHN-M004"):
        MigrationPlan((MigrationStep(2, MigrationKind.CREATE_MODEL, "a"), MigrationStep(1, MigrationKind.CREATE_MODEL, "b")))


@dataclass
class FakeTransaction:
    events: list[str]
    fail_commit: bool = False

    def execute(self, query: BackendQuery | QueryIR) -> Sequence[Mapping[str, Any]]:
        self.events.append(f"execute:{query.model}")
        return []

    def commit(self) -> None:
        self.events.append("commit")
        if self.fail_commit:
            raise RuntimeError("commit failed")

    def rollback(self) -> None:
        self.events.append("rollback")


@dataclass
class FakeAdapter:
    events: list[str] = field(default_factory=list)
    fail_commit: bool = False
    last_query: BackendQuery | None = None

    def execute(self, query: BackendQuery) -> Sequence[Mapping[str, Any]]:
        self.last_query = query
        self.events.append(f"read:{query.model}")
        return [{"id": 1}]

    def begin(self) -> FakeTransaction:
        self.events.append("begin")
        return FakeTransaction(self.events, self.fail_commit)


def test_data_engine_is_fail_closed_before_adapter_access() -> None:
    adapter = FakeAdapter()
    engine = DataEngine(adapter, CapabilitySet())

    with pytest.raises(CapabilityError, match="SHN-G001"):
        engine.read(QueryIR("kullanici"))
    with pytest.raises(CapabilityError, match="SHN-G001"):
        engine.transaction(lambda tx: None)

    assert adapter.events == []


def test_data_engine_requires_read_capability_and_compiles_adapter_query() -> None:
    adapter = FakeAdapter()
    engine = DataEngine(adapter, CapabilitySet().grant(Capability.VERI_OKU))
    payload = "' OR 1=1 --"

    assert engine.read(QueryIR("kullanici", filters=(Filter("ad", QueryOp.EQ, payload),))) == [{"id": 1}]
    assert adapter.events == ["read:kullanici"]
    assert adapter.last_query is not None
    assert adapter.last_query.parameters == (payload,)


def test_transaction_rolls_back_when_action_fails() -> None:
    adapter = FakeAdapter()
    engine = DataEngine(adapter, CapabilitySet().grant(Capability.VERI_YAZ))

    with pytest.raises(RuntimeError, match="boom"):
        engine.transaction(lambda tx: (_ for _ in ()).throw(RuntimeError("boom")))

    assert adapter.events == ["begin", "rollback"]


def test_transaction_rolls_back_when_commit_fails() -> None:
    adapter = FakeAdapter(fail_commit=True)
    engine = DataEngine(adapter, CapabilitySet().grant(Capability.VERI_YAZ))

    with pytest.raises(RuntimeError, match="commit failed"):
        engine.transaction(lambda tx: tx.execute(QueryIR("kullanici")))

    assert adapter.events == ["begin", "execute:kullanici", "commit", "rollback"]
