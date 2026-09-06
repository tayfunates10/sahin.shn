import sqlite3

import pytest

from sahin.capabilities import Capability, CapabilityError, CapabilitySet
from sahin.data_mutation_abi import DataMutationABI
from sahin.data_mutation_execution import execute_data_mutation
from sahin.server_data import DataEngine, QueryIR
from sahin.sqlite_data import SQLiteDataAdapter, SQLiteModelBinding


def _binding() -> SQLiteModelBinding:
    return SQLiteModelBinding(
        model="Urun",
        table="urunler",
        key_field="id",
        fields=("id", "ad", "stok"),
    )


def _prepare(path) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "CREATE TABLE urunler (id INTEGER PRIMARY KEY, ad TEXT NOT NULL, stok INTEGER NOT NULL)"
        )
        connection.commit()
    finally:
        connection.close()


def _engine(path, *, write: bool = True) -> DataEngine:
    capabilities = CapabilitySet().grant(Capability.VERI_OKU)
    if write:
        capabilities = capabilities.grant(Capability.VERI_YAZ)
    return DataEngine(SQLiteDataAdapter(path, (_binding(),)), capabilities)


def _abi() -> DataMutationABI:
    return DataMutationABI(command="sakla", model="Urun", value_slot="urun")


def _persist_and_read(path, *, backend_name: str, value: dict[str, object]):
    _prepare(path)
    execute_data_mutation(_abi(), value=value, engine=_engine(path), backend_name=backend_name)
    return _engine(path).read(QueryIR(model="Urun", fields=("id", "ad", "stok")))


def test_sakla_native_and_wasm_persist_identical_state(tmp_path) -> None:
    value = {"id": 7, "ad": "Kalem", "stok": 3}

    native_rows = _persist_and_read(tmp_path / "native.db", backend_name="native", value=value)
    wasm_rows = _persist_and_read(tmp_path / "wasm.db", backend_name="wasm", value=value)

    expected = ({"id": 7, "ad": "Kalem", "stok": 3},)
    assert native_rows == expected
    assert wasm_rows == expected
    assert native_rows == wasm_rows


@pytest.mark.parametrize("backend_name", ["native", "wasm"])
def test_sakla_equivalence_keeps_write_capability_fail_closed(tmp_path, backend_name: str) -> None:
    path = tmp_path / f"{backend_name}-denied.db"
    _prepare(path)
    engine = _engine(path, write=False)

    with pytest.raises(CapabilityError, match="veri:yaz"):
        execute_data_mutation(_abi(), value={"id": 1, "ad": "Kalem", "stok": 1}, engine=engine, backend_name=backend_name)

    assert _engine(path).read(QueryIR(model="Urun")) == ()


def test_sakla_native_and_wasm_match_on_upsert_semantics(tmp_path) -> None:
    observations = []
    for backend_name in ("native", "wasm"):
        path = tmp_path / f"{backend_name}-upsert.db"
        _prepare(path)
        engine = _engine(path)
        execute_data_mutation(
            _abi(),
            value={"id": 1, "ad": "Kalem", "stok": 3},
            engine=engine,
            backend_name=backend_name,
        )
        execute_data_mutation(
            _abi(),
            value={"id": 1, "ad": "Kalem", "stok": 2},
            engine=engine,
            backend_name=backend_name,
        )
        observations.append(_engine(path).read(QueryIR(model="Urun", fields=("id", "stok"))))

    assert observations == [({"id": 1, "stok": 2},), ({"id": 1, "stok": 2},)]
