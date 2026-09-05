import pytest

from sahin.ir import IRInstruction
from sahin.member_store_abi import (
    MemberStoreABIError,
    MemberStoreOperation,
    apply_member_store,
    validate_member_store_instruction,
)


def test_member_store_instruction_is_deterministic_and_result_free():
    instruction = MemberStoreOperation("stok", "%parent", "%next").instruction()
    assert instruction == IRInstruction("member_store", ("stok", "%parent", "%next"))
    assert validate_member_store_instruction(instruction) == MemberStoreOperation(
        "stok", "%parent", "%next"
    )


def test_member_store_matches_runtime_dict_member_write_semantics():
    target = {"stok": 4}
    apply_member_store(target, "stok", 7)
    assert target == {"stok": 7}


def test_member_store_allows_runtime_compatible_new_dict_member():
    target = {}
    apply_member_store(target, "stok", 1)
    assert target == {"stok": 1}


@pytest.mark.parametrize(
    "instruction, message",
    [
        (IRInstruction("member_store", ("stok", "%parent")), "hedef temp"),
        (IRInstruction("member_store", ("", "%parent", "%next")), "üye adı"),
        (IRInstruction("member_store", ("stok", "parent", "%next")), "hedefi"),
        (IRInstruction("member_store", ("stok", "%parent", "next")), "yeni değeri"),
        (IRInstruction("member_store", ("stok", "%parent", "%next"), "%result"), "sonuç"),
    ],
)
def test_member_store_schema_rejects_malformed_instructions_fail_closed(instruction, message):
    with pytest.raises(MemberStoreABIError, match=message):
        validate_member_store_instruction(instruction)


def test_member_store_rejects_non_mutable_target_fail_closed():
    with pytest.raises(MemberStoreABIError, match="değiştirilebilir değil"):
        apply_member_store((1, 2), "stok", 3)
