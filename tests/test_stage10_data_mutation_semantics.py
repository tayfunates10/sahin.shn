import pytest

from sahin.ast_nodes import Command
from sahin.data_mutation_semantics import (
    DataMutationSemanticError,
    ResolvedDataBinding,
    lower_resolved_sakla_command,
)
from sahin.lexer import tokenize
from sahin.parser import parse


def _command(source: str) -> Command:
    program = parse(tokenize(source))
    statement = program.statements[0]
    assert isinstance(statement, Command)
    return statement


def test_sakla_uses_authoritative_semantic_model_metadata() -> None:
    abi = lower_resolved_sakla_command(
        _command("sakla ürün\n"),
        binding=ResolvedDataBinding(value_slot="ürün", model="SiparişKalemi"),
    )

    assert abi.command == "sakla"
    assert abi.value_slot == "ürün"
    assert abi.model == "SiparişKalemi"


def test_sakla_rejects_stale_or_mismatched_semantic_binding() -> None:
    with pytest.raises(DataMutationSemanticError, match="slot mismatch"):
        lower_resolved_sakla_command(
            _command("sakla ürün\n"),
            binding=ResolvedDataBinding(value_slot="sipariş", model="Ürün"),
        )


def test_sakla_semantic_boundary_does_not_accept_noncanonical_value_shape() -> None:
    with pytest.raises(DataMutationSemanticError, match="direct-name"):
        lower_resolved_sakla_command(
            _command("sakla ürün.stok\n"),
            binding=ResolvedDataBinding(value_slot="ürün", model="Ürün"),
        )
