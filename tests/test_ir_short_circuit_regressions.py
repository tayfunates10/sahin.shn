from sahin.ir import lower_source
from sahin.ir_control_flow import validate_control_flow


def test_short_circuit_join_slot_cannot_alias_user_identifier():
    user_name = "__shn_logic_0_end_result"
    lowered = lower_source(
        f"{user_name} = hayır\n"
        "sonuç = evet veya hayır\n"
        f"yaz {user_name}\n"
    )

    stores = [item for item in lowered.instructions if item.opcode == "store"]
    user_stores = [item for item in stores if item.operands[0] == user_name]
    internal_stores = [item for item in stores if item.operands[0].startswith("$internal_")]

    assert len(user_stores) == 1
    assert len(internal_stores) == 2
    assert all(item.operands[0] != user_name for item in internal_stores)
    assert any(
        item.opcode == "load" and item.operands == (user_name,)
        for item in lowered.instructions
    )
    validate_control_flow(lowered)
