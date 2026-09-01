import pytest

from sahin.ir import IRInstruction, IRProgram
from sahin.native_backend import NativeBackendError, build_native_plan, build_native_plan_from_source


def test_native_plan_is_deterministic_and_has_no_implicit_capabilities():
    source = 'ad = "Şahin"\nsayı = 2 + 3\nyaz ad\nyaz sayı\n'

    first = build_native_plan_from_source(source)
    second = build_native_plan_from_source(source)

    assert first == second
    assert first.canonical() == second.canonical()
    assert first.capabilities == ()
    assert '"target":"native-sahin-safe"' in first.canonical()
    assert '"adapter_version":1' in first.canonical()


def test_native_plan_rejects_unknown_ir_version_fail_closed():
    with pytest.raises(NativeBackendError, match="Desteklenmeyen Şahin IR sürümü"):
        build_native_plan(IRProgram(version=2, instructions=()))


def test_native_plan_rejects_unknown_target_fail_closed():
    with pytest.raises(NativeBackendError, match="Desteklenmeyen native hedefi"):
        build_native_plan(IRProgram(version=1, instructions=()), target="x86_64-host")


def test_native_plan_rejects_unknown_opcode_fail_closed():
    program = IRProgram(version=1, instructions=(IRInstruction("host_call", ("network",)),))

    with pytest.raises(NativeBackendError, match="desteklenmeyen opcode"):
        build_native_plan(program)


def test_native_plan_rejects_use_before_definition():
    program = IRProgram(version=1, instructions=(IRInstruction("write", ("%9",)),))

    with pytest.raises(NativeBackendError, match="tanımsız geçici değer"):
        build_native_plan(program)


def test_native_plan_rejects_duplicate_temp_definition():
    program = IRProgram(
        version=1,
        instructions=(
            IRInstruction("const", ("tam:1",), "%0"),
            IRInstruction("const", ("tam:2",), "%0"),
        ),
    )

    with pytest.raises(NativeBackendError, match="yeniden tanımlanan"):
        build_native_plan(program)


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
def test_native_plan_rejects_invalid_operand_counts_or_result_shape(instruction):
    program = IRProgram(version=1, instructions=(instruction,))

    with pytest.raises(NativeBackendError, match="instruction şemasını reddetti"):
        build_native_plan(program)


def test_native_plan_rejects_temp_in_name_role():
    program = IRProgram(
        version=1,
        instructions=(
            IRInstruction("const", ("tam:1",), "%0"),
            IRInstruction("store", ("%0", "%0")),
        ),
    )

    with pytest.raises(NativeBackendError, match="isim operandı"):
        build_native_plan(program)
