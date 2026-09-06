from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

import pytest

from sahin.capabilities import Capability, CapabilityError, CapabilitySet
from sahin.data_mutation_abi import DataMutationABI
from sahin.data_mutation_execution import (
    DataMutationExecutionError,
    DataMutationExecutionResult,
    DataMutationWrite,
    execute_data_mutation,
)
from sahin.server_data import BackendQuery, DataEngine


@dataclass
class MutationTransaction:
    events: list[str]
    writes: list[DataMutationWrite]
    fail_write: bool = False

    def execute(self, query: BackendQuery) -> Sequence[Mapping[str, Any]]:
        return []

    def write(self, mutation: DataMutationWrite) -> None:
        self.events.append(f"write:{mutation.model}")
        if self.fail_write:
            raise RuntimeError("write failed")
        self.writes.append(mutation)

    def commit(self) -> None:
        self.events.append("commit")

    def rollback(self) -> None:
        self.events.append("rollback")


@dataclass
class MutationAdapter:
    events: list[str] = field(default_factory=list)
    writes: list[DataMutationWrite] = field(default_factory=list)
    fail_write: bool = False

    def execute(self, query: BackendQuery) -> Sequence[Mapping[str, Any]]:
        return []

    def begin(self) -> MutationTransaction:
        self.events.append("begin")
        return MutationTransaction(self.events, self.writes, self.fail_write)


@dataclass
class ReadOnlyTransaction:
    events: list[str]

    def execute(self, query: BackendQuery) -> Sequence[Mapping[str, Any]]:
        return []

    def commit(self) -> None:
        self.events.append("commit")

    def rollback(self) -> None:
        self.events.append("rollback")


@dataclass
class ReadOnlyAdapter:
    events: list[str] = field(default_factory=list)

    def execute(self, query: BackendQuery) -> Sequence[Mapping[str, Any]]:
        return []

    def begin(self) -> ReadOnlyTransaction:
        self.events.append("begin")
        return ReadOnlyTransaction(self.events)


def _abi() -> DataMutationABI:
    return DataMutationABI(command="sakla", model="Urun", value_slot="urun")


def test_sakla_execution_requires_capability_before_adapter_access() -> None:
    adapter = MutationAdapter()
    engine = DataEngine(adapter, CapabilitySet())

    with pytest.raises(CapabilityError, match="veri:yaz"):
        execute_data_mutation(_abi(), value={"stok": 2}, engine=engine, backend_name="native")

    assert adapter.events == []
    assert adapter.writes == []


@pytest.mark.parametrize("backend_name", ["native", "wasm"])
def test_sakla_execution_writes_inside_transaction_and_commits(backend_name: str) -> None:
    adapter = MutationAdapter()
    engine = DataEngine(adapter, CapabilitySet().grant(Capability.VERI_YAZ))
    value = {"ad": "Kalem", "stok": 2}

    result = execute_data_mutation(_abi(), value=value, engine=engine, backend_name=backend_name)

    assert result == DataMutationExecutionResult(backend_name, "Urun", "urun")
    assert adapter.events == ["begin", "write:Urun", "commit"]
    assert adapter.writes == [DataMutationWrite("Urun", value)]


def test_sakla_execution_rolls_back_when_host_write_fails() -> None:
    adapter = MutationAdapter(fail_write=True)
    engine = DataEngine(adapter, CapabilitySet().grant(Capability.VERI_YAZ))

    with pytest.raises(RuntimeError, match="write failed"):
        execute_data_mutation(_abi(), value={"stok": 2}, engine=engine, backend_name="wasm")

    assert adapter.events == ["begin", "write:Urun", "rollback"]
    assert adapter.writes == []


def test_sakla_execution_fails_closed_when_transaction_has_no_write_contract() -> None:
    adapter = ReadOnlyAdapter()
    engine = DataEngine(adapter, CapabilitySet().grant(Capability.VERI_YAZ))

    with pytest.raises(DataMutationExecutionError, match="write contract"):
        execute_data_mutation(_abi(), value={"stok": 2}, engine=engine, backend_name="native")

    assert adapter.events == ["begin", "rollback"]
