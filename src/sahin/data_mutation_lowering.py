from __future__ import annotations

from .ast_nodes import Command, Name
from .data_mutation_abi import DataMutationABI


class DataMutationLoweringError(ValueError):
    """Fail-closed error while binding command AST to the data-mutation ABI."""


def lower_sakla_command(command: Command, *, model: str) -> DataMutationABI:
    """Bind the canonical ``sakla <name>`` AST shape to ``DataMutationABI``.

    The parser only carries the value slot (for example ``sakla ürün``); it does
    not carry authoritative model metadata. The caller therefore must provide
    the model resolved by the semantic/type layer. This function deliberately
    refuses to infer a model from spelling or to widen the accepted command
    shape.
    """

    if command.name != "sakla":
        raise DataMutationLoweringError("only the 'sakla' command can use data-mutation lowering")
    if command.subject is not None:
        raise DataMutationLoweringError("'sakla' does not accept a subject")
    if command.arrow is not None:
        raise DataMutationLoweringError("'sakla' does not accept an arrow target")
    if command.body:
        raise DataMutationLoweringError("'sakla' does not accept a command body")
    if len(command.arguments) != 1:
        raise DataMutationLoweringError("'sakla' requires exactly one value slot")

    value = command.arguments[0]
    if not isinstance(value, Name):
        raise DataMutationLoweringError("'sakla' value slot must be a direct name")

    return DataMutationABI(command="sakla", model=model, value_slot=value.value)
