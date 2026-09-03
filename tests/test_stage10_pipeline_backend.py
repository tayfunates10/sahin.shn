import pytest

from sahin.backend_equivalence import compare_source
from sahin.ir import IRInstruction, IRProgram, lower_source
from sahin.native_backend import NativeBackendError, build_native_plan
from sahin.wasm_backend import WasmBackendError, build_wasm_plan


def test_pipeline_is_preserved_by_both_backend_adapter_plans():
    program = lower_source("sonuç = 1..5\n    | ilk 2\n    | seç evet\n")
    wasm = build_wasm_plan(program)
    native = build_native_plan(program)

    assert [item.opcode for item in wasm.instructions if item.opcode == "pipeline"] == ["pipeline", "pipeline"]
    assert [item.operands[0] for item in native.instructions if item.opcode == "pipeline"] == ["ilk", "seç"]


@pytest.mark.parametrize(
    "source, expected",
    [
        ("sonuç = 1..5\n    | ilk 2\n", (1, 2)),
        ("sonuç = 3..1\n    | sırala\n", (1, 2, 3)),
        ("sonuç = 1..3\n    | seç evet\n", (1, 2, 3)),
        ("sonuç = 1..3\n    | seç hayır\n", ()),
        ("sonuç = 1..3\n    | ilk\n", (1,)),
    ],
)
def test_pipeline_reference_wasm_native_equivalence(source, expected):
    report = compare_source(source)
    assert report.equivalent
    assert report.reference.state == (("sonuç", expected),)


@pytest.mark.parametrize("builder,error_type", [(build_wasm_plan, WasmBackendError), (build_native_plan, NativeBackendError)])
def test_pipeline_adapter_rejects_malformed_schema(builder, error_type):
    program = IRProgram(version=1, instructions=(IRInstruction("pipeline", ("ilk",), "%1"),))
    with pytest.raises(error_type, match="geçersiz pipeline instruction şemasını reddetti"):
        builder(program)


@pytest.mark.parametrize("builder,error_type", [(build_wasm_plan, WasmBackendError), (build_native_plan, NativeBackendError)])
def test_pipeline_adapter_rejects_unknown_stage(builder, error_type):
    program = IRProgram(
        version=1,
        instructions=(
            IRInstruction("const", ("tam:1",), "%0"),
            IRInstruction("pipeline", ("bilinmeyen", "%0"), "%1"),
        ),
    )
    with pytest.raises(error_type, match="bilinmeyen pipeline aşamasını reddetti"):
        builder(program)


@pytest.mark.parametrize("builder,error_type", [(build_wasm_plan, WasmBackendError), (build_native_plan, NativeBackendError)])
def test_pipeline_adapter_rejects_use_before_definition(builder, error_type):
    program = IRProgram(
        version=1,
        instructions=(IRInstruction("pipeline", ("ilk", "%0"), "%1"),),
    )
    with pytest.raises(error_type):
        builder(program)


def test_pipeline_chained_data_flow_matches_reference():
    report = compare_source("sonuç = 5..1\n    | sırala\n    | ilk 3\n    | seç evet\n")
    assert report.equivalent
    assert report.reference.state == (("sonuç", (1, 2, 3)),)
