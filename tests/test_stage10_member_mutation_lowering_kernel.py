import pytest

from sahin.ir import IRInstruction
from sahin.member_mutation_abi import MemberMutationTarget
from sahin.member_mutation_lowering import (
    MemberMutationLoweringError,
    lower_member_mutation_kernel,
)


def _temps():
    counter = 0

    def next_temp():
        nonlocal counter
        value = f"%k{counter}"
        counter += 1
        return value

    return next_temp


def test_member_increment_lowering_is_deterministic_and_uses_member_store():
    mutation = MemberMutationTarget("ürün", ("stok",), "+")
    plan = lower_member_mutation_kernel(
        mutation,
        target_temp="%target",
        amount_temp="%amount",
        next_temp=_temps(),
    )

    assert plan.instructions == (
        IRInstruction("member", ("stok", "%target"), "%k0"),
        IRInstruction("binary", ("+", "%k0", "%amount"), "%k1"),
        IRInstruction("member_store", ("stok", "%target", "%k1")),
    )
    assert plan.result_temp == "%k1"


def test_member_decrement_default_amount_matches_runtime_default_one():
    mutation = MemberMutationTarget("ürün", ("stok",), "-")
    plan = lower_member_mutation_kernel(
        mutation,
        target_temp="%target",
        amount_temp=None,
        next_temp=_temps(),
    )

    assert plan.instructions == (
        IRInstruction("member", ("stok", "%target"), "%k0"),
        IRInstruction("const", ("tam:1",), "%k1"),
        IRInstruction("binary", ("-", "%k0", "%k1"), "%k2"),
        IRInstruction("member_store", ("stok", "%target", "%k2")),
    )


def test_nested_member_kernel_only_mutates_final_owner_and_does_not_re_evaluate_root():
    mutation = MemberMutationTarget("sipariş", ("ürün", "stok"), "+")
    plan = lower_member_mutation_kernel(
        mutation,
        target_temp="%owner",
        amount_temp="%amount",
        next_temp=_temps(),
    )

    assert plan.instructions[0] == IRInstruction("member", ("stok", "%owner"), "%k0")
    assert plan.instructions[-1] == IRInstruction("member_store", ("stok", "%owner", "%k1"))
    assert all("sipariş" not in operand for item in plan.instructions for operand in item.operands)


@pytest.mark.parametrize(
    "mutation,target,amount",
    [
        (MemberMutationTarget("ürün", (), "+"), "%target", "%amount"),
        (MemberMutationTarget("ürün", ("stok",), "*"), "%target", "%amount"),
        (MemberMutationTarget("", ("stok",), "+"), "%target", "%amount"),
        (MemberMutationTarget("ürün", ("stok",), "+"), "ürün", "%amount"),
        (MemberMutationTarget("ürün", ("stok",), "+"), "%target", "amount"),
    ],
)
def test_member_mutation_lowering_fails_closed_on_malformed_contract(mutation, target, amount):
    with pytest.raises(MemberMutationLoweringError):
        lower_member_mutation_kernel(
            mutation,
            target_temp=target,
            amount_temp=amount,
            next_temp=_temps(),
        )
