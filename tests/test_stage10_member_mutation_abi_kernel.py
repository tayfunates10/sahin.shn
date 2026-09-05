import pytest

from sahin.ast_nodes import Command, Literal, Member, Name
from sahin.member_mutation_abi import MemberMutationABIError, analyze_member_mutation
from sahin.parser import parse
from sahin.lexer import tokenize


def _command(source: str) -> Command:
    program = parse(tokenize(source))
    statement = program.statements[0]
    assert isinstance(statement, Command)
    return statement


def test_parser_member_increment_produces_deterministic_lvalue_contract():
    target = analyze_member_mutation(_command("ürün.stok artır 2\n"))
    assert target.canonical() == ("ürün", ("stok",), "+")


def test_nested_member_decrement_preserves_source_path_order():
    target = analyze_member_mutation(_command("sipariş.ürün.stok azalt 1\n"))
    assert target.canonical() == ("sipariş", ("ürün", "stok"), "-")


def test_member_mutation_rejects_multiple_amount_arguments_fail_closed():
    command = Command(
        name="artır",
        subject=Member(Name("ürün"), "stok"),
        arguments=(Literal(1), Literal(2)),
    )
    with pytest.raises(MemberMutationABIError, match="en fazla bir"):
        analyze_member_mutation(command)


def test_member_mutation_rejects_non_member_target():
    command = Command(name="artır", subject=Name("stok"), arguments=(Literal(1),))
    with pytest.raises(MemberMutationABIError, match="Member AST"):
        analyze_member_mutation(command)
