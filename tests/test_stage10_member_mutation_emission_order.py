from sahin.member_mutation_abi import MemberMutationTarget
from sahin.member_mutation_lowering import lower_member_mutation_owner_order


def test_owner_order_orchestrator_emits_runtime_order() -> None:
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

    def emit(instruction) -> None:
        events.append(instruction.opcode)

    plan = lower_member_mutation_owner_order(
        MemberMutationTarget("ürün", ("stok",), "+"),
        evaluate_read_owner=read_owner,
        evaluate_amount=amount,
        evaluate_write_owner=write_owner,
        next_temp=lambda: next(temps),
        emit_instruction=emit,
    )

    assert events == [
        "read-owner",
        "member",
        "amount",
        "binary",
        "write-owner",
        "member_store",
    ]
    assert [instruction.opcode for instruction in plan.instructions] == [
        "member",
        "binary",
        "member_store",
    ]


def test_owner_order_orchestrator_emits_default_before_binary() -> None:
    events: list[str] = []
    temps = iter(["%2", "%3", "%4"])

    lower_member_mutation_owner_order(
        MemberMutationTarget("ürün", ("stok",), "-"),
        evaluate_read_owner=lambda: events.append("read-owner") or "%0",
        evaluate_amount=None,
        evaluate_write_owner=lambda: events.append("write-owner") or "%1",
        next_temp=lambda: next(temps),
        emit_instruction=lambda instruction: events.append(instruction.opcode),
    )

    assert events == [
        "read-owner",
        "member",
        "const",
        "binary",
        "write-owner",
        "member_store",
    ]
