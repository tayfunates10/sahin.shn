from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .data_mutation_execution import DataMutationWrite
from .server_data import BackendQuery, QueryOp, ServerDataError


class SQLiteDataError(ServerDataError):
    """Fail-closed persistent adapter error."""


@dataclass(frozen=True, slots=True)
class SQLiteModelBinding:
    """Explicit mapping between a Şahin model and an existing SQLite table.

    The adapter never infers table, key, or column names from runtime values. All
    identifiers must be declared up front so persistence cannot broaden the data
    surface implicitly.
    """

    model: str
    table: str
    key_field: str
    fields: tuple[str, ...]

    def __post_init__(self) -> None:
        _safe_identifier(self.model)
        _safe_identifier(self.table)
        _safe_identifier(self.key_field)
        for field in self.fields:
            _safe_identifier(field)
        if self.key_field not in self.fields:
            raise SQLiteDataError("SHN-SQL003", "Anahtar alanı model alanları içinde olmalıdır.")
        if len(self.fields) != len(set(self.fields)):
            raise SQLiteDataError("SHN-SQL004", "SQLite model alanları yinelenemez.")


class SQLiteDataAdapter:
    """Persistent Stage 7/10 data adapter backed by Python's SQLite driver."""

    def __init__(self, path: str | Path, bindings: Sequence[SQLiteModelBinding]) -> None:
        self._path = str(path)
        self._bindings = _index_bindings(bindings)

    def execute(self, query: BackendQuery) -> Sequence[Mapping[str, Any]]:
        binding = self._binding(query.model)
        sql, parameters = _compile_select(binding, query)
        connection = self._connect()
        try:
            cursor = connection.execute(sql, parameters)
            columns = tuple(item[0] for item in cursor.description or ())
            return tuple(dict(zip(columns, row, strict=True)) for row in cursor.fetchall())
        finally:
            connection.close()

    def begin(self) -> "SQLiteTransaction":
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
        except BaseException:
            connection.close()
            raise
        return SQLiteTransaction(connection, self._bindings)

    def _binding(self, model: str) -> SQLiteModelBinding:
        try:
            return self._bindings[model]
        except KeyError as exc:
            raise SQLiteDataError("SHN-SQL001", f"SQLite model eşlemesi bulunamadı: {model}") from exc

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection


class SQLiteTransaction:
    def __init__(self, connection: sqlite3.Connection, bindings: Mapping[str, SQLiteModelBinding]) -> None:
        self._connection = connection
        self._bindings = bindings
        self._closed = False

    def execute(self, query: BackendQuery) -> Sequence[Mapping[str, Any]]:
        self._ensure_open()
        binding = self._binding(query.model)
        sql, parameters = _compile_select(binding, query)
        cursor = self._connection.execute(sql, parameters)
        columns = tuple(item[0] for item in cursor.description or ())
        return tuple(dict(zip(columns, row, strict=True)) for row in cursor.fetchall())

    def write(self, mutation: DataMutationWrite) -> None:
        self._ensure_open()
        binding = self._binding(mutation.model)
        if not isinstance(mutation.value, Mapping):
            raise SQLiteDataError("SHN-SQL005", "sakla değeri alan eşlemesi taşımalıdır.")

        supplied = set(mutation.value)
        allowed = set(binding.fields)
        unknown = supplied - allowed
        if unknown:
            names = ", ".join(sorted(str(item) for item in unknown))
            raise SQLiteDataError("SHN-SQL006", f"Bilinmeyen model alanı: {names}")
        if binding.key_field not in mutation.value:
            raise SQLiteDataError("SHN-SQL007", f"Anahtar alanı eksik: {binding.key_field}")

        ordered_fields = tuple(field for field in binding.fields if field in mutation.value)
        sql = _compile_upsert(binding, ordered_fields)
        parameters = tuple(mutation.value[field] for field in ordered_fields)
        self._connection.execute(sql, parameters)

    def commit(self) -> None:
        self._ensure_open()
        try:
            self._connection.commit()
        finally:
            self._closed = True
            self._connection.close()

    def rollback(self) -> None:
        if self._closed:
            return
        try:
            self._connection.rollback()
        finally:
            self._closed = True
            self._connection.close()

    def _binding(self, model: str) -> SQLiteModelBinding:
        try:
            return self._bindings[model]
        except KeyError as exc:
            raise SQLiteDataError("SHN-SQL001", f"SQLite model eşlemesi bulunamadı: {model}") from exc

    def _ensure_open(self) -> None:
        if self._closed:
            raise SQLiteDataError("SHN-SQL008", "SQLite transaction zaten kapalı.")


def _index_bindings(bindings: Sequence[SQLiteModelBinding]) -> dict[str, SQLiteModelBinding]:
    indexed: dict[str, SQLiteModelBinding] = {}
    for binding in bindings:
        if binding.model in indexed:
            raise SQLiteDataError("SHN-SQL002", f"Yinelenen SQLite model eşlemesi: {binding.model}")
        indexed[binding.model] = binding
    return indexed


def _compile_select(binding: SQLiteModelBinding, query: BackendQuery) -> tuple[str, tuple[Any, ...]]:
    selected = query.fields or binding.fields
    _require_fields(binding, selected)

    clauses: list[str] = []
    parameters: list[Any] = []
    operators = {
        QueryOp.EQ: "=",
        QueryOp.NE: "!=",
        QueryOp.LT: "<",
        QueryOp.LTE: "<=",
        QueryOp.GT: ">",
        QueryOp.GTE: ">=",
    }
    for item in query.filters:
        _require_fields(binding, (item.field,))
        if item.parameter_index < 0 or item.parameter_index >= len(query.parameters):
            raise SQLiteDataError("SHN-SQL009", "Sorgu parametre indeksi geçersiz.")
        clauses.append(f'"{item.field}" {operators[item.op]} ?')
        parameters.append(query.parameters[item.parameter_index])

    columns = ", ".join(f'"{field}"' for field in selected)
    sql = f'SELECT {columns} FROM "{binding.table}"'
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " LIMIT ?"
    parameters.append(query.limit)
    return sql, tuple(parameters)


def _compile_upsert(binding: SQLiteModelBinding, fields: tuple[str, ...]) -> str:
    _require_fields(binding, fields)
    columns = ", ".join(f'"{field}"' for field in fields)
    placeholders = ", ".join("?" for _ in fields)
    mutable = tuple(field for field in fields if field != binding.key_field)
    if mutable:
        updates = ", ".join(f'"{field}" = excluded."{field}"' for field in mutable)
        conflict = f'DO UPDATE SET {updates}'
    else:
        conflict = "DO NOTHING"
    return (
        f'INSERT INTO "{binding.table}" ({columns}) VALUES ({placeholders}) '
        f'ON CONFLICT("{binding.key_field}") {conflict}'
    )


def _require_fields(binding: SQLiteModelBinding, fields: Sequence[str]) -> None:
    allowed = set(binding.fields)
    for field in fields:
        if field not in allowed:
            raise SQLiteDataError("SHN-SQL006", f"Bilinmeyen model alanı: {field}")


def _safe_identifier(value: str) -> None:
    if not value or not value.replace("_", "").isalnum() or not value[0].isalpha():
        raise SQLiteDataError("SHN-SQL010", f"Geçersiz SQLite tanımlayıcısı: {value!r}")
