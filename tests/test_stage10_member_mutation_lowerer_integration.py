from sahin.ast_nodes import Command, Member, Name
from sahin.ir import IRInstruction, _Lowerer


def test_member_mutation_is_wired_into_main_lowerer_with_runtime_owner_order():
    lowerer = _Lowerer(initial_names={"ürün": "ürün", "miktar": "miktar"})
    statement = Command(
        name="artır",
        subject=Member(Name("ürün"), "stok"),
        arguments=(Name("miktar"),),
    )

    lowerer._statement(statement)

    assert lowerer.instructions == [
        IRInstruction("load", ("ürün",), "%0"),
        IRInstruction("member", ("stok", "%0"), "%1"),
        IRInstruction("load", ("miktar",), "%2"),
        IRInstruction("binary", ("+", "%1", "%2"), "%3"),
        IRInstruction("load", ("ürün",), "%4"),
        IRInstruction("member_store", ("stok", "%4", "%3")),
    ]


def test_nested_member_mutation_re_evaluates_full_owner_chain_before_store():
    lowerer = _Lowerer(initial_names={"ürün": "ürün"})
    statement = Command(
        name="azalt",
        subject=Member(Member(Name("ürün"), "depo"), "stok"),
        arguments=(),
    )

    lowerer._statement(statement)

    assert lowerer.instructions == [
        IRInstruction("load", ("ürün",), "%0"),
        IRInstruction("member", ("depo", "%0"), "%1"),
        IRInstruction("member", ("stok", "%1"), "%2"),
        IRInstruction("const", ("tam:1",), "%3"),
        IRInstruction("binary", ("-", "%2", "%3"), "%4"),
        IRInstruction("load", ("ürün",), "%5"),
        IRInstruction("member", ("depo", "%5"), "%6"),
        IRInstruction("member_store", ("stok", "%6", "%4")),
    ]
