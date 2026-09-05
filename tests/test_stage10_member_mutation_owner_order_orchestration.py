from sahin.member_mutation_abi import MemberMutationTarget
from sahin.member_mutation_lowering import lower_member_mutation_owner_order


def test_owner_order_orchestrator_re_evaluates_write_owner_after_amount() -> None:
    events: list[str] = []
    temps = iter(["%3", "%4"])

    def read_owner() -> str:
        events.append("read-owner")
        return "%0"

    def amount() -> str:
        events.append("amount")
        return "%1"

    def write_owner() -> str:
        events.append("write-owner")
        return "%2"

    plan = lower_member_mutation_owner_order(
        MemberMutationTarget("ürün", ("stok",), "+"),
        evaluate_read_owner=read_owner,
        evaluate_amount=amount,
        evaluate_write_owner=write_owner,
        next_temp=lambda: next(temps),
    )

    assert events == ["read-owner", "amount", "write-owner"]
    assert [instruction.opcode for instruction in plan.instructions] == [
        "member",
        "binary",
        "member_store",
    ]
    assert plan.instructions[0].operands == ("stok", "%0")
    assert plan.instructions[1].operands == ("+", "%3", "%1")
    assert plan.instructions[2].operands == ("stok", "%2", "%4")


def test_owner_order_orchestrator_keeps_default_amount_inside_kernel() -> None:
    events: list[str] = []
    temps = iter(["%2", "%3", "%4"])

    plan = lower_member_mutation_owner_order(
        MemberMutationTarget("ürün", ("stok",), "-"),
        evaluate_read_owner=lambda: events.append("read-owner") or "%0",
        evaluate_amount=None,
        evaluate_write_owner=lambda: events.append("write-owner") or "%1",
        next_temp=lambda: next(temps),
    )

    assert events == ["read-owner", "write-owner"]
    assert [instruction.opcode for instruction in plan.instructions] == [
        "member",
        "const",
        "binary",
        "member_store",
    ]
    assert plan.instructions[1].operands == ("tam:1",)
