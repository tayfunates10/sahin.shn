from __future__ import annotations

from dataclasses import dataclass

from .capabilities import Capability, CapabilitySet


class DataMutationABIError(ValueError):
    """Fail-closed validation error for host-backed data mutation ABI."""


@dataclass(frozen=True, slots=True)
class DataMutationABI:
    """Backend-neutral contract for the first host-backed `sakla` slice.

    This object intentionally does not execute a mutation. It only carries the
    minimum validated shape required before a backend/host adapter may be
    considered. Runtime lowering and backend equivalence stay separate gates.
    """

    command: str
    model: str
    value_slot: str

    def __post_init__(self) -> None:
        if self.command != "sakla":
            raise DataMutationABIError("only the 'sakla' data mutation command is accepted")
        _safe_identifier(self.model, "model")
        _safe_identifier(self.value_slot, "value slot")

    @property
    def required_capability(self) -> Capability:
        return Capability.VERI_YAZ


def require_data_mutation_capability(abi: DataMutationABI, capabilities: CapabilitySet) -> DataMutationABI:
    """Require the explicit write capability before a host mutation boundary."""

    capabilities.require(abi.required_capability)
    return abi


def _safe_identifier(value: str, label: str) -> None:
    if not value or not value.replace("_", "").isalnum() or not value[0].isalpha():
        raise DataMutationABIError(f"invalid {label}: {value!r}")
