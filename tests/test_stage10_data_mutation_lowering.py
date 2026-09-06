import pytest

from sahin.ast_nodes import Command
from sahin.data_mutation_lowering import DataMutationLoweringError, lower_sakla_command
from sahin.lexer import tokenize
from sahin.parser import parse


def _command(source: str) -> Command:
    program = parse(tokenize(source))
    statement = program.statements[0]
    assert isinstance(statement, Command)
    return statement


def test_sakla_parser_shape_binds_losslessly_to_data_mutation_abi() -> None:
    abi = lower_sakla_command(_command("sakla ürün\n"), model="Ürün")

    assert abi.command == "sakla"
    assert abi.model == "Ürün"
    assert abi.value_slot == "ürün"


def test_sakla_lowering_rejects_non_name_or_extra_arguments() -> None:
    with pytest.raises(DataMutationLoweringError, match="direct name"):
        lower_sakla_command(_command("sakla ürün.stok\n"), model="Ürün")

    with pytest.raises(DataMutationLoweringError, match="exactly one"):
        lower_sakla_command(_command("sakla ürün başka\n"), model="Ürün")


def test_sakla_lowering_rejects_arrow_shape() -> None:
    with pytest.raises(DataMutationLoweringError, match="arrow"):
        lower_sakla_command(_command("sakla ürün -> sonuç\n"), model="Ürün")


def test_data_mutation_lowering_does_not_guess_model_from_slot_name() -> None:
    abi = lower_sakla_command(_command("sakla ürün\n"), model="SiparişKalemi")

    assert abi.model == "SiparişKalemi"
    assert abi.value_slot == "ürün"
