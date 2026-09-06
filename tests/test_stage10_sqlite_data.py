import sqlite3

import pytest

from sahin.capabilities import Capability, CapabilitySet
from sahin.data_mutation_abi import DataMutationABI
from sahin.data_mutation_execution import execute_data_mutation
from sahin.server_data import Filter, QueryIR, QueryOp, DataEngine
from sahin.sqlite_data import SQLiteDataAdapter, SQLiteDataError, SQLiteModelBinding


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


def _engine(path) -> DataEngine:
    return DataEngine(
        SQLiteDataAdapter(path, (_binding(),)),
        CapabilitySet().grant(Capability.VERI_OKU).grant(Capability.VERI_YAZ),
    )


def _abi() -> DataMutationABI:
    return DataMutationABI(command="sakla", model="Urun", value_slot="urun")


def test_sakla_persists_across_adapter_instances(tmp_path) -> None:
    path = tmp_path / "sahin.db"
    _prepare(path)

    execute_data_mutation(
        _abi(),
        value={"id": 1, "ad": "Kalem", "stok": 3},
        engine=_engine(path),
        backend_name="native",
    )

    fresh_engine = _engine(path)
    rows = fresh_engine.read(QueryIR(model="Urun", fields=("id", "ad", "stok")))
    assert rows == ({"id": 1, "ad": "Kalem", "stok": 3},)


def test_sakla_updates_existing_key_without_duplicate_row(tmp_path) -> None:
    path = tmp_path / "sahin.db"
    _prepare(path)
    engine = _engine(path)

    execute_data_mutation(
        _abi(),
        value={"id": 1, "ad": "Kalem", "stok": 3},
        engine=engine,
        backend_name="wasm",
    )
    execute_data_mutation(
        _abi(),
        value={"id": 1, "ad": "Kalem", "stok": 2},
        engine=engine,
        backend_name="wasm",
    )

    rows = engine.read(QueryIR(model="Urun", fields=("id", "stok")))
    assert rows == ({"id": 1, "stok": 2},)


def test_sqlite_read_uses_structured_filters_and_parameter_binding(tmp_path) -> None:
    path = tmp_path / "sahin.db"
    _prepare(path)
    engine = _engine(path)
    for item in (
        {"id": 1, "ad": "Kalem", "stok": 3},
        {"id": 2, "ad": "Defter", "stok": 0},
    ):
        execute_data_mutation(_abi(), value=item, engine=engine, backend_name="native")

    rows = engine.read(
        QueryIR(
            model="Urun",
            fields=("id", "ad"),
            filters=(Filter("stok", QueryOp.GT, 0),),
        )
    )
    assert rows == ({"id": 1, "ad": "Kalem"},)


def test_sqlite_adapter_rejects_undeclared_runtime_fields_and_rolls_back(tmp_path) -> None:
    path = tmp_path / "sahin.db"
    _prepare(path)
    engine = _engine(path)

    with pytest.raises(SQLiteDataError, match="Bilinmeyen model alanı"):
        execute_data_mutation(
            _abi(),
            value={"id": 1, "ad": "Kalem", "stok": 3, "gizli": "x"},
            engine=engine,
            backend_name="native",
        )

    assert engine.read(QueryIR(model="Urun")) == ()


def test_sqlite_adapter_requires_explicit_key_field(tmp_path) -> None:
    path = tmp_path / "sahin.db"
    _prepare(path)

    with pytest.raises(SQLiteDataError, match="Anahtar alanı eksik"):
        execute_data_mutation(
            _abi(),
            value={"ad": "Kalem", "stok": 3},
            engine=_engine(path),
            backend_name="native",
        )


def test_sqlite_binding_rejects_identifier_injection() -> None:
    with pytest.raises(SQLiteDataError, match="Geçersiz SQLite tanımlayıcısı"):
        SQLiteModelBinding(
            model="Urun",
            table='urunler; DROP TABLE urunler',
            key_field="id",
            fields=("id",),
        )
