import pytest

from sahin.ir import IRInstruction, IRProgram
from sahin.wasm_backend import WasmBackendError, build_wasm_plan, build_wasm_plan_from_source


def test_wasm_plan_is_deterministic_and_has_no_implicit_capability_imports():
    source = 'ad = "Şahin"\nsayı = 2 + 3\nyaz ad\nyaz sayı\n'

    first = build_wasm_plan_from_source(source)
    second = build_wasm_plan_from_source(source)

    assert first == second
    assert first.canonical() == second.canonical()
    assert first.imports == ()
    assert '"target":"wasm32-sahin-safe"' in first.canonical()
    assert '"adapter_version":1' in first.canonical()


def test_wasm_plan_rejects_unknown_ir_version_fail_closed():
    with pytest.raises(WasmBackendError, match="Desteklenmeyen Şahin IR sürümü"):
        build_wasm_plan(IRProgram(version=2, instructions=()))


def test_wasm_plan_rejects_unknown_opcode_fail_closed():
    program = IRProgram(version=1, instructions=(IRInstruction("host_call", ("network",)),))

    with pytest.raises(WasmBackendError, match="desteklenmeyen opcode"):
        build_wasm_plan(program)


def test_wasm_plan_rejects_use_before_definition():
    program = IRProgram(
        version=1,
        instructions=(IRInstruction("write", ("%9",)),),
    )

    with pytest.raises(WasmBackendError, match="tanımsız geçici değer"):
        build_wasm_plan(program)


def test_wasm_plan_rejects_duplicate_temp_definition():
    program = IRProgram(
        version=1,
        instructions=(
            IRInstruction("const", ("tam:1",), "%0"),
            IRInstruction("const", ("tam:2",), "%0"),
        ),
    )

    with pytest.raises(WasmBackendError, match="yeniden tanımlanan"):
        build_wasm_plan(program)


@pytest.mark.parametrize(
    "instruction",
    (
        IRInstruction("const"),
        IRInstruction("const", ("tam:1",)),
        IRInstruction("load", ("isim",)),
        IRInstruction("unary", ("-",), "%0"),
        IRInstruction("binary", ("+", "%0"), "%1"),
        IRInstruction("store", ("x", "%0"), "%1"),
        IRInstruction("bind", ("x", "%0"), "%1"),
        IRInstruction("write", (), "%0"),
    ),
)
def test_wasm_plan_rejects_invalid_operand_counts_or_result_shape(instruction):
    program = IRProgram(version=1, instructions=(instruction,))

    with pytest.raises(WasmBackendError, match="instruction şemasını reddetti"):
        build_wasm_plan(program)


def test_wasm_plan_rejects_write_result_even_when_operand_is_defined():
    program = IRProgram(
        version=1,
        instructions=(
            IRInstruction("const", ("tam:1",), "%0"),
            IRInstruction("write", ("%0",), "%1"),
        ),
    )

    with pytest.raises(WasmBackendError, match="write.*sonuç üretmemelidir"):
        build_wasm_plan(program)


def test_wasm_plan_rejects_non_temp_value_role_for_store():
    program = IRProgram(version=1, instructions=(IRInstruction("store", ("x", "tam:1")),))

    with pytest.raises(WasmBackendError, match="geçici değer beklenen operandı"):
        build_wasm_plan(program)


def test_wasm_plan_rejects_temp_in_name_role():
    program = IRProgram(
        version=1,
        instructions=(
            IRInstruction("const", ("tam:1",), "%0"),
            IRInstruction("store", ("%0", "%0")),
        ),
    )

    with pytest.raises(WasmBackendError, match="isim operandı"):
        build_wasm_plan(program)
