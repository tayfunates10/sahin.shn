from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

import pytest

from sahin.capabilities import Capability, CapabilityError, CapabilitySet
from sahin.data_mutation_execution import DataMutationWrite
from sahin.data_mutation_runtime import execute_resolved_sakla_command
from sahin.data_mutation_semantics import DataMutationSemanticError, ResolvedDataBinding
from sahin.lexer import tokenize
from sahin.parser import parse
from sahin.server_data import BackendQuery, DataEngine


@dataclass
class MutationTransaction:
    events: list[str]
    writes: list[DataMutationWrite]

    def execute(self, query: BackendQuery) -> Sequence[Mapping[str, Any]]:
        return []

    def write(self, mutation: DataMutationWrite) -> None:
        self.events.append(f"write:{mutation.model}")
        self.writes.append(mutation)

    def commit(self) -> None:
        self.events.append("commit")

    def rollback(self) -> None:
        self.events.append("rollback")


@dataclass
class MutationAdapter:
    events: list[str] = field(default_factory=list)
    writes: list[DataMutationWrite] = field(default_factory=list)

    def execute(self, query: BackendQuery) -> Sequence[Mapping[str, Any]]:
        return []

    def begin(self) -> MutationTransaction:
        self.events.append("begin")
        return MutationTransaction(self.events, self.writes)


def _command():
    return parse(tokenize("sakla ürün\n")).statements[0]


@pytest.mark.parametrize("backend_name", ["native", "wasm"])
def test_resolved_sakla_reads_exact_runtime_slot_then_executes_transaction(backend_name: str) -> None:
    adapter = MutationAdapter()
    engine = DataEngine(adapter, CapabilitySet().grant(Capability.VERI_YAZ))
    value = {"ad": "Kalem", "stok": 2}
    resolved_slots: list[str] = []

    result = execute_resolved_sakla_command(
        _command(),
        binding=ResolvedDataBinding(value_slot="ürün", model="Ürün"),
        resolve_value=lambda slot: resolved_slots.append(slot) or value,
        engine=engine,
        backend_name=backend_name,
    )

    assert resolved_slots == ["ürün"]
    assert adapter.events == ["begin", "write:Ürün", "commit"]
    assert adapter.writes == [DataMutationWrite("Ürün", value)]
    assert result.backend == backend_name
    assert result.model == "Ürün"
    assert result.value_slot == "ürün"


def test_resolved_sakla_rejects_stale_binding_before_runtime_slot_access() -> None:
    adapter = MutationAdapter()
    engine = DataEngine(adapter, CapabilitySet().grant(Capability.VERI_YAZ))
    resolved_slots: list[str] = []

    with pytest.raises(DataMutationSemanticError, match="slot mismatch"):
        execute_resolved_sakla_command(
            _command(),
            binding=ResolvedDataBinding(value_slot="sipariş", model="Ürün"),
            resolve_value=lambda slot: resolved_slots.append(slot),
            engine=engine,
            backend_name="native",
        )

    assert resolved_slots == []
    assert adapter.events == []
    assert adapter.writes == []


def test_resolved_sakla_capability_denial_happens_before_adapter_access() -> None:
    adapter = MutationAdapter()
    engine = DataEngine(adapter, CapabilitySet())

    with pytest.raises(CapabilityError, match="veri:yaz"):
        execute_resolved_sakla_command(
            _command(),
            binding=ResolvedDataBinding(value_slot="ürün", model="Ürün"),
            resolve_value=lambda slot: {"stok": 2},
            engine=engine,
            backend_name="wasm",
        )

    assert adapter.events == []
    assert adapter.writes == []
