from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from .data_mutation_abi import DataMutationABI
from .data_mutation_backend import DataMutationBackendPlan, validate_data_mutation_backend
from .server_data import DataEngine, TransactionAdapter


class DataMutationExecutionError(RuntimeError):
    """Fail-closed error raised when a host transaction cannot perform `sakla`."""


@dataclass(frozen=True, slots=True)
class DataMutationWrite:
    """Validated host write payload carried inside the existing data transaction."""

    model: str
    value: Any


@runtime_checkable
class DataMutationTransaction(Protocol):
    """Narrow host capability required by transaction-backed `sakla` execution."""

    def write(self, mutation: DataMutationWrite) -> None: ...


@dataclass(frozen=True, slots=True)
class DataMutationExecutionResult:
    backend: str
    model: str
    value_slot: str


def execute_data_mutation(
    abi: DataMutationABI,
    *,
    value: Any,
    engine: DataEngine,
    backend_name: str,
) -> DataMutationExecutionResult:
    """Execute one validated `sakla` write through the existing transaction boundary.

    Backend and `veri:yaz` capability validation happen before adapter access. The
    mutation itself is issued only inside ``DataEngine.transaction`` so action,
    commit and rollback semantics remain owned by the Stage 7 data engine.
    """

    plan = validate_data_mutation_backend(
        abi,
        capabilities=engine.capabilities,
        backend_name=backend_name,
    )
    mutation = DataMutationWrite(model=plan.model, value=value)

    def action(tx: TransactionAdapter) -> None:
        _write_transaction(tx, mutation)

    engine.transaction(action)
    return _execution_result(plan)


def _write_transaction(tx: TransactionAdapter, mutation: DataMutationWrite) -> None:
    if not isinstance(tx, DataMutationTransaction):
        raise DataMutationExecutionError("data transaction does not implement the sakla write contract")
    tx.write(mutation)


def _execution_result(plan: DataMutationBackendPlan) -> DataMutationExecutionResult:
    return DataMutationExecutionResult(
        backend=plan.backend,
        model=plan.model,
        value_slot=plan.value_slot,
    )
