import pytest

from sahin.ir import IRInstruction, IRProgram
from sahin.native_backend import NativeBackendError, build_native_plan
from sahin.wasm_backend import WasmBackendError, build_wasm_plan


def _valid_control_flow_program() -> IRProgram:
    return IRProgram(
        version=1,
        instructions=(
            IRInstruction("const", ("evet_hayır:evet",), "%0"),
            IRInstruction("branch", ("%0", "then", "else")),
            IRInstruction("label", ("then",)),
            IRInstruction("jump", ("end",)),
            IRInstruction("label", ("else",)),
            IRInstruction("jump", ("end",)),
            IRInstruction("label", ("end",)),
        ),
    )


def test_wasm_and_native_accept_valid_control_flow_without_capabilities() -> None:
    program = _valid_control_flow_program()

    wasm = build_wasm_plan(program)
    native = build_native_plan(program)

    assert wasm.instructions == program.instructions
    assert wasm.imports == ()
    assert native.instructions == program.instructions
    assert native.capabilities == ()


@pytest.mark.parametrize(
    ("builder", "error_type"),
    [
        (build_wasm_plan, WasmBackendError),
        (build_native_plan, NativeBackendError),
    ],
)
def test_adapters_fail_closed_on_non_dominating_temp(builder, error_type) -> None:
    program = IRProgram(
        version=1,
        instructions=(
            IRInstruction("const", ("evet_hayır:evet",), "%0"),
            IRInstruction("branch", ("%0", "then", "else")),
            IRInstruction("label", ("then",)),
            IRInstruction("const", ("tam:1",), "%1"),
            IRInstruction("jump", ("join",)),
            IRInstruction("label", ("else",)),
            IRInstruction("jump", ("join",)),
            IRInstruction("label", ("join",)),
            IRInstruction("write", ("%1",)),
        ),
    )

    with pytest.raises(error_type, match="tanımsız geçici değer"):
        builder(program)


@pytest.mark.parametrize(
    ("builder", "error_type"),
    [
        (build_wasm_plan, WasmBackendError),
        (build_native_plan, NativeBackendError),
    ],
)
def test_adapters_fail_closed_on_unknown_control_flow_opcode(builder, error_type) -> None:
    program = IRProgram(version=1, instructions=(IRInstruction("branche", (), "%0"),))

    with pytest.raises(error_type, match="desteklenmeyen opcode"):
        builder(program)


@pytest.mark.parametrize("builder", [build_wasm_plan, build_native_plan])
def test_adapters_accept_cfg_dominating_temp_even_when_definition_is_later_in_tuple(builder) -> None:
    program = IRProgram(
        version=1,
        instructions=(
            IRInstruction("jump", ("define",)),
            IRInstruction("label", ("use",)),
            IRInstruction("write", ("%0",)),
            IRInstruction("jump", ("end",)),
            IRInstruction("label", ("define",)),
            IRInstruction("const", ("tam:1",), "%0"),
            IRInstruction("jump", ("use",)),
            IRInstruction("label", ("end",)),
        ),
    )

    plan = builder(program)
    assert plan.instructions == program.instructions


@pytest.mark.parametrize("builder", [build_wasm_plan, build_native_plan])
def test_adapters_accept_cfg_dominating_name_even_when_store_is_later_in_tuple(builder) -> None:
    program = IRProgram(
        version=1,
        instructions=(
            IRInstruction("jump", ("define",)),
            IRInstruction("label", ("use",)),
            IRInstruction("load", ("x",), "%1"),
            IRInstruction("write", ("%1",)),
            IRInstruction("jump", ("end",)),
            IRInstruction("label", ("define",)),
            IRInstruction("const", ("tam:1",), "%0"),
            IRInstruction("store", ("x", "%0")),
            IRInstruction("jump", ("use",)),
            IRInstruction("label", ("end",)),
        ),
    )

    plan = builder(program)
    assert plan.instructions == program.instructions
