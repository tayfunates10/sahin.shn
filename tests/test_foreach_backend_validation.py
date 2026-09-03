import pytest

from sahin.ir import IRInstruction, IRProgram, lower_source
from sahin.native_backend import NativeBackendError, build_native_plan
from sahin.wasm_backend import WasmBackendError, build_wasm_plan


def test_foreach_is_accepted_by_safe_backend_plans_without_new_capabilities():
    program = lower_source(
        "toplam = 0\n"
        "her sayı içinden 1..3\n"
        "    toplam = toplam + sayı\n"
        "yaz toplam\n"
    )

    wasm = build_wasm_plan(program)
    native = build_native_plan(program)

    assert wasm.instructions == program.instructions
    assert native.instructions == program.instructions
    assert wasm.imports == ()
    assert native.capabilities == ()
    assert any(item.opcode == "iter_begin" for item in wasm.instructions)
    assert any(item.opcode == "iter_advance" for item in native.instructions)


@pytest.mark.parametrize(
    ("builder", "error_type"),
    ((build_wasm_plan, WasmBackendError), (build_native_plan, NativeBackendError)),
)
def test_iterator_consumers_require_an_iter_begin_origin(builder, error_type):
    program = IRProgram(
        version=1,
        instructions=(
            IRInstruction("const", ("tam:1",), "%0"),
            IRInstruction("iter_has_next", ("%0",), "%1"),
        ),
    )

    with pytest.raises(error_type, match="iter_begin"):
        builder(program)


@pytest.mark.parametrize(
    ("builder", "error_type"),
    ((build_wasm_plan, WasmBackendError), (build_native_plan, NativeBackendError)),
)
def test_iter_advance_must_not_produce_a_result(builder, error_type):
    program = IRProgram(
        version=1,
        instructions=(
            IRInstruction("const", ("tam:1",), "%0"),
            IRInstruction("iter_begin", ("%0",), "%1"),
            IRInstruction("iter_advance", ("%1",), "%2"),
        ),
    )

    with pytest.raises(error_type, match="iter_advance"):
        builder(program)
