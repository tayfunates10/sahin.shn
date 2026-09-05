import pytest

from sahin.ast_nodes import Assignment, Command, Literal, Member, Name, Program
from sahin.ir import IRLoweringError, lower_program, lower_source


def _mutation_program(command_name: str, *, subject=None) -> Program:
    return Program(
        (
            Assignment("stok", Literal(3)),
            Command(
                name=command_name,
                arguments=(Literal(1),),
                subject=subject or Name("stok"),
            ),
        )
    )


def test_name_increment_command_is_now_lowered_by_mutation_abi():
    ir = lower_program(_mutation_program("artır"))
    assert [item.opcode for item in ir.instructions] == ["const", "store", "load", "const", "binary", "store"]


def test_name_decrement_command_is_now_lowered_by_mutation_abi():
    ir = lower_program(_mutation_program("azalt"))
    assert [item.opcode for item in ir.instructions] == ["const", "store", "load", "const", "binary", "store"]


def test_member_mutation_is_now_lowered_by_member_lvalue_abi():
    member_subject = Member(Name("stok"), "adet")
    ir = lower_program(_mutation_program("artır", subject=member_subject))

    opcodes = [item.opcode for item in ir.instructions]
    assert opcodes == [
        "const",
        "store",
        "load",
        "member",
        "const",
        "binary",
        "load",
        "member_store",
    ]
    assert ir.instructions[-1].operands[0] == "adet"


def test_host_effect_command_stays_fail_closed():
    with pytest.raises(IRLoweringError, match=r"'sakla' Command düğümünü"):
        lower_source("sakla ürün\n")


def test_return_command_is_rejected_outside_flow():
    with pytest.raises(IRLoweringError, match=r"'ver' Command düğümünü"):
        lower_source("ver 1\n")


def test_break_command_is_rejected_outside_loop():
    with pytest.raises(IRLoweringError, match=r"'bitir' Command düğümünü"):
        lower_source("bitir\n")
