import pytest

from sahin.ast_nodes import Assignment, Command, Literal, Name, Program
from sahin.ir import IRLoweringError, lower_program, lower_source


def _mutation_program(command_name: str) -> Program:
    return Program(
        (
            Assignment("stok", Literal(3)),
            Command(
                name=command_name,
                arguments=(Literal(1),),
                subject=Name("stok"),
            ),
        )
    )


def test_increment_command_stays_fail_closed_until_mutation_abi_exists():
    # Runtime ABI Name/Member subject kabul eder. Parser'ın çıplak
    # `stok artır 1` satırını başka bir Command biçimi olarak yorumlaması bu
    # IR sınır testini yanlış komuta bağlamamalı; gerçek semantic AST'yi sınarız.
    with pytest.raises(IRLoweringError, match=r"'artır' Command düğümünü"):
        lower_program(_mutation_program("artır"))


def test_decrement_command_stays_fail_closed_until_mutation_abi_exists():
    with pytest.raises(IRLoweringError, match=r"'azalt' Command düğümünü"):
        lower_program(_mutation_program("azalt"))


def test_host_effect_command_stays_fail_closed():
    with pytest.raises(IRLoweringError, match=r"'sakla' Command düğümünü"):
        lower_source("sakla ürün\n")


def test_return_command_is_rejected_outside_flow():
    with pytest.raises(IRLoweringError, match=r"'ver' Command düğümünü"):
        lower_source("ver 1\n")


def test_break_command_is_rejected_outside_loop():
    with pytest.raises(IRLoweringError, match=r"'bitir' Command düğümünü"):
        lower_source("bitir\n")
