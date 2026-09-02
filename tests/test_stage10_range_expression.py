import pytest

from sahin.ir import IRInstruction, IRProgram, lower_source
from sahin.native_backend import NativeBackendError, build_native_plan
from sahin.wasm_backend import WasmBackendError, build_wasm_plan


def test_range_expression_lowers_to_explicit_ir_opcode():
    program = lower_source("sayılar = 1 .. 3\n")
    assert program.instructions == (
        IRInstruction("const", ("tam:1",), "%0"),
        IRInstruction("const", ("tam:3",), "%1"),
        IRInstruction("range", ("%0", "%1"), "%2"),
        IRInstruction("store", ("sayılar", "%2")),
    )


def test_descending_range_keeps_endpoint_order_in_ir():
    program = lower_source("sayılar = 3 .. 1\n")
    range_instruction = next(item for item in program.instructions if item.opcode == "range")
    assert range_instruction.operands == ("%0", "%1")


def test_range_backend_support_remains_fail_closed_until_adapter_contract_is_added():
    program = IRProgram(
        version=1,
        instructions=(
            IRInstruction("const", ("tam:1",), "%0"),
            IRInstruction("const", ("tam:3",), "%1"),
            IRInstruction("range", ("%0", "%1"), "%2"),
        ),
    )
    with pytest.raises(WasmBackendError, match="desteklenmeyen opcode"):
        build_wasm_plan(program)
    with pytest.raises(NativeBackendError, match="desteklenmeyen opcode"):
        build_native_plan(program)
