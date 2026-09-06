from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from sahin.ast_nodes import Command
from sahin.backend_equivalence import compare_source
from sahin.capabilities import Capability, CapabilitySet
from sahin.data_mutation_execution import DataMutationWrite
from sahin.data_mutation_runtime import execute_resolved_sakla_command
from sahin.data_mutation_semantics import ResolvedDataBinding
from sahin.lexer import tokenize
from sahin.parser import parse
from sahin.server_data import BackendQuery, DataEngine


@dataclass
class PersistentTransaction:
    persisted: list[DataMutationWrite]

    def execute(self, query: BackendQuery) -> Sequence[Mapping[str, Any]]:
        return ()

    def write(self, mutation: DataMutationWrite) -> None:
        self.persisted.append(mutation)

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        self.persisted.clear()


@dataclass
class PersistentAdapter:
    persisted: list[DataMutationWrite] = field(default_factory=list)

    def execute(self, query: BackendQuery) -> Sequence[Mapping[str, Any]]:
        return ()

    def begin(self) -> PersistentTransaction:
        return PersistentTransaction(self.persisted)


def _source_observation(source: str):
    program = parse(tokenize(source))
    assert isinstance(program.statements[-1], Command)
    command = program.statements[-1]
    assert command.name == "sakla"
    assert command.location is not None

    lines = source.splitlines(keepends=True)
    prefix = "".join(lines[: command.location.line - 1])
    report = compare_source(prefix)
    assert report.equivalent
    return command, report


def _value(observation, slot: str):
    return dict(observation.state)[slot]


def test_real_shn_sakla_source_matches_reference_native_and_wasm_persistent_value() -> None:
    source = "urun = 2 + 3 * 4\nsakla urun\n"
    binding = ResolvedDataBinding(value_slot="urun", model="Urun")
    command, report = _source_observation(source)

    reference_value = _value(report.reference, binding.value_slot)
    assert reference_value == 14

    persisted = {}
    for backend_name, observation in (("native", report.native), ("wasm", report.wasm)):
        adapter = PersistentAdapter()
        engine = DataEngine(adapter, CapabilitySet().grant(Capability.VERI_YAZ))
        backend_value = _value(observation, binding.value_slot)

        execute_resolved_sakla_command(
            command,
            binding=binding,
            resolve_value=lambda slot, value=backend_value: value,
            engine=engine,
            backend_name=backend_name,
        )
        persisted[backend_name] = tuple(adapter.persisted)

    expected = (DataMutationWrite("Urun", reference_value),)
    assert persisted == {"native": expected, "wasm": expected}


def test_real_shn_sakla_source_uses_backend_observation_not_reference_slot_alias() -> None:
    source = "urun = 7\ndiger = 99\nsakla urun\n"
    binding = ResolvedDataBinding(value_slot="urun", model="Urun")
    command, report = _source_observation(source)

    for backend_name, observation in (("native", report.native), ("wasm", report.wasm)):
        adapter = PersistentAdapter()
        engine = DataEngine(adapter, CapabilitySet().grant(Capability.VERI_YAZ))
        slots = dict(observation.state)

        execute_resolved_sakla_command(
            command,
            binding=binding,
            resolve_value=slots.__getitem__,
            engine=engine,
            backend_name=backend_name,
        )

        assert adapter.persisted == [DataMutationWrite("Urun", 7)]
