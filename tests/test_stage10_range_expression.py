import pytest

from sahin.backend_equivalence import BackendEquivalenceError, compare_source
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


def test_range_is_preserved_by_both_backend_adapter_plans():
    program = lower_source("sayılar = 1 .. 3\n")
    wasm = build_wasm_plan(program)
    native = build_native_plan(program)
    assert next(item for item in wasm.instructions if item.opcode == "range").operands == ("%0", "%1")
    assert next(item for item in native.instructions if item.opcode == "range").operands == ("%0", "%1")


@pytest.mark.parametrize(
    "source, expected",
    [
        ("sayılar = 1 .. 3\n", (1, 2, 3)),
        ("sayılar = 3 .. 1\n", (3, 2, 1)),
        ("sayılar = 4 .. 4\n", (4,)),
    ],
)
def test_range_reference_wasm_native_equivalence(source, expected):
    report = compare_source(source)
    assert report.equivalent
    assert report.reference.state == (("sayılar", expected),)


@pytest.mark.parametrize("builder,error_type", [(build_wasm_plan, WasmBackendError), (build_native_plan, NativeBackendError)])
def test_range_adapter_rejects_malformed_schema(builder, error_type):
    program = IRProgram(version=1, instructions=(IRInstruction("range", ("%0",), "%1"),))
    with pytest.raises(error_type, match="geçersiz range instruction şemasını reddetti"):
        builder(program)


@pytest.mark.parametrize("builder,error_type", [(build_wasm_plan, WasmBackendError), (build_native_plan, NativeBackendError)])
def test_range_adapter_rejects_use_before_definition(builder, error_type):
    program = IRProgram(
        version=1,
        instructions=(
            IRInstruction("const", ("tam:3",), "%1"),
            IRInstruction("range", ("%0", "%1"), "%2"),
        ),
    )
    with pytest.raises(error_type):
        builder(program)


def test_range_equivalence_rejects_non_integer_endpoints():
    with pytest.raises((BackendEquivalenceError, ValueError)):
        compare_source('sayılar = "1" .. 3\n')
