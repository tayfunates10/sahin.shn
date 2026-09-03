import pytest

from sahin.backend_equivalence import compare_source
from sahin.ir import IRInstruction, IRProgram, lower_source
from sahin.native_backend import NativeBackendError, build_native_plan
from sahin.wasm_backend import WasmBackendError, build_wasm_plan


@pytest.mark.parametrize("builder", [build_wasm_plan, build_native_plan])
def test_foreach_iterator_opcodes_are_preserved_in_adapter_plan(builder):
    program = lower_source(
        "her sayı içinden 1..3\n"
        "    yaz sayı\n"
    )
    plan = builder(program)
    opcodes = [item.opcode for item in plan.instructions]

    assert "iter_begin" in opcodes
    assert "iter_has_next" in opcodes
    assert "iter_value" in opcodes
    assert "iter_advance" in opcodes


def test_foreach_reference_wasm_native_equivalence_updates_outer_state():
    report = compare_source(
        "toplam = 0\n"
        "her sayı içinden 1..3\n"
        "    toplam = toplam + sayı\n"
        "yaz toplam\n"
    )

    assert report.equivalent
    assert report.reference.state == (("toplam", 6),)
    assert report.reference.output == ("6",)


def test_foreach_reverse_range_equivalence_preserves_iteration_order():
    report = compare_source(
        "her sayı içinden 3..1\n"
        "    yaz sayı\n"
    )

    assert report.equivalent
    assert report.reference.output == ("3", "2", "1")
    assert report.reference.state == ()


def test_foreach_bitir_equivalence_stops_before_iterator_advance():
    report = compare_source(
        "her sayı içinden 1..3\n"
        "    yaz sayı\n"
        "    bitir\n"
    )

    assert report.equivalent
    assert report.reference.output == ("1",)


@pytest.mark.parametrize(
    ("builder", "error_type"),
    ((build_wasm_plan, WasmBackendError), (build_native_plan, NativeBackendError)),
)
def test_foreach_backend_rejects_iterator_use_before_definition(builder, error_type):
    program = IRProgram(
        version=1,
        instructions=(
            IRInstruction("iter_begin", ("%missing",), "%0"),
            IRInstruction("iter_has_next", ("%0",), "%1"),
        ),
    )

    with pytest.raises(error_type, match="tanımsız geçici"):
        builder(program)


@pytest.mark.parametrize(
    ("builder", "error_type"),
    ((build_wasm_plan, WasmBackendError), (build_native_plan, NativeBackendError)),
)
def test_foreach_backend_rejects_non_iterator_consumer(builder, error_type):
    program = IRProgram(
        version=1,
        instructions=(
            IRInstruction("const", ("tam:1",), "%0"),
            IRInstruction("iter_value", ("%0",), "%1"),
        ),
    )

    with pytest.raises(error_type, match="iter_begin"):
        builder(program)
