from __future__ import annotations

from dataclasses import dataclass

from .ast_nodes import Command, Name
from .data_mutation_abi import DataMutationABI
from .data_mutation_lowering import DataMutationLoweringError, lower_sakla_command


class DataMutationSemanticError(ValueError):
    """Fail-closed error while binding authoritative semantic metadata."""


@dataclass(frozen=True, slots=True)
class ResolvedDataBinding:
    """Authoritative semantic/type resolution for one data value slot.

    The resolver that constructs this value is responsible for proving the
    model identity. This boundary deliberately carries the source slot as well
    so lowering can reject stale or mismatched metadata instead of guessing.
    """

    value_slot: str
    model: str


def lower_resolved_sakla_command(command: Command, *, binding: ResolvedDataBinding) -> DataMutationABI:
    """Lower ``sakla`` only when semantic metadata matches the parsed slot."""

    if command.name != "sakla":
        raise DataMutationSemanticError("only the 'sakla' command accepts data semantic binding")
    if len(command.arguments) != 1 or not isinstance(command.arguments[0], Name):
        raise DataMutationSemanticError("'sakla' semantic binding requires one direct-name value slot")

    parsed_slot = command.arguments[0].value
    if binding.value_slot != parsed_slot:
        raise DataMutationSemanticError(
            f"semantic binding slot mismatch: parsed {parsed_slot!r}, resolved {binding.value_slot!r}"
        )

    try:
        return lower_sakla_command(command, model=binding.model)
    except DataMutationLoweringError as exc:
        raise DataMutationSemanticError(str(exc)) from exc
