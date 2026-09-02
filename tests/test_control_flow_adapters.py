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

    with pytest.raises(error_type, match="control-flow sözleşmesini reddetti"):
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

    with pytest.raises(error_type, match="control-flow sözleşmesini reddetti"):
        builder(program)
