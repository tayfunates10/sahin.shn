from __future__ import annotations

from dataclasses import dataclass

from .capabilities import CapabilitySet
from .data_mutation_abi import DataMutationABI, require_data_mutation_capability


class DataMutationBackendError(ValueError):
    """Fail-closed validation error for backend data-mutation planning."""


@dataclass(frozen=True, slots=True)
class DataMutationBackendPlan:
    """Validated, non-executing host-mutation plan for a backend adapter.

    This plan deliberately does not perform a write and does not introduce an
    IR opcode/import. It proves only that a known backend received a validated
    ``sakla`` ABI and an explicit ``veri:yaz`` capability before crossing the
    host-mutation boundary.
    """

    backend: str
    command: str
    model: str
    value_slot: str


_SUPPORTED_BACKENDS = frozenset({"native", "wasm"})


def validate_data_mutation_backend(
    abi: DataMutationABI,
    *,
    capabilities: CapabilitySet,
    backend_name: str,
) -> DataMutationBackendPlan:
    """Validate ``sakla`` at the backend/host boundary without executing it."""

    if backend_name not in _SUPPORTED_BACKENDS:
        raise DataMutationBackendError(f"unsupported data-mutation backend: {backend_name!r}")

    require_data_mutation_capability(abi, capabilities)
    return DataMutationBackendPlan(
        backend=backend_name,
        command=abi.command,
        model=abi.model,
        value_slot=abi.value_slot,
    )
