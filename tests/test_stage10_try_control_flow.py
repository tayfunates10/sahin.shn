import pytest

from sahin.ir import IRInstruction, IRProgram
from sahin.ir_control_flow import IRControlFlowError, validate_control_flow
from sahin.native_backend import NativeBackendError, build_native_plan
from sahin.wasm_backend import WasmBackendError, build_wasm_plan


def _valid_try_program() -> IRProgram:
    return IRProgram(
        version=1,
        instructions=(
            IRInstruction("try_guard", ("handler", "protected_end")),
            IRInstruction("const", ("tam:1",), "%value"),
            IRInstruction("label", ("protected_end",)),
            IRInstruction("jump", ("join",)),
            IRInstruction("label", ("handler",)),
            IRInstruction("catch", (), "%error"),
            IRInstruction("write", ("%error",)),
            IRInstruction("label", ("join",)),
        ),
    )


def test_try_guard_models_normal_and_exceptional_paths_without_leaking_error_temp():
    program = _valid_try_program()
    summary = validate_control_flow(program)

    assert summary.labels == ("protected_end", "handler", "join")
    assert summary.jump_targets == ("join",)


def test_try_error_temp_is_not_definitely_defined_after_normal_and_handler_join():
    program = IRProgram(
        version=1,
        instructions=(*_valid_try_program().instructions, IRInstruction("write", ("%error",))),
    )

    with pytest.raises(IRControlFlowError, match="tüm ulaşılabilir giriş yollarında"):
        validate_control_flow(program)


def test_try_handler_requires_immediate_catch_instruction():
    program = IRProgram(
        version=1,
        instructions=(
            IRInstruction("try_guard", ("handler", "protected_end")),
            IRInstruction("label", ("protected_end",)),
            IRInstruction("jump", ("join",)),
            IRInstruction("label", ("handler",)),
            IRInstruction("const", ("tam:1",), "%0"),
            IRInstruction("label", ("join",)),
        ),
    )

    with pytest.raises(IRControlFlowError, match="catch"):
        validate_control_flow(program)


def test_try_handler_cannot_be_a_normal_jump_target():
    program = IRProgram(
        version=1,
        instructions=(
            IRInstruction("try_guard", ("handler", "protected_end")),
            IRInstruction("jump", ("handler",)),
            IRInstruction("label", ("protected_end",)),
            IRInstruction("jump", ("join",)),
            IRInstruction("label", ("handler",)),
            IRInstruction("catch", (), "%error"),
            IRInstruction("label", ("join",)),
        ),
    )

    with pytest.raises(IRControlFlowError, match="normal jump/branch"):
        validate_control_flow(program)


def test_try_handler_cannot_be_reached_by_normal_fallthrough():
    program = IRProgram(
        version=1,
        instructions=(
            IRInstruction("try_guard", ("handler", "protected_end")),
            IRInstruction("const", ("tam:1",), "%value"),
            IRInstruction("label", ("protected_end",)),
            IRInstruction("label", ("handler",)),
            IRInstruction("catch", (), "%error"),
        ),
    )

    with pytest.raises(IRControlFlowError, match="yalnız try_guard exceptional kenarından"):
        validate_control_flow(program)


def test_standalone_catch_is_fail_closed():
    program = IRProgram(version=1, instructions=(IRInstruction("catch", (), "%error"),))

    with pytest.raises(IRControlFlowError, match="yalnız doğrulanmış try_guard"):
        validate_control_flow(program)


@pytest.mark.parametrize("builder", (build_wasm_plan, build_native_plan))
def test_try_opcodes_are_accepted_without_widening_adapter_surface(builder):
    plan = builder(_valid_try_program())
    assert plan.instructions == _valid_try_program().instructions
    if hasattr(plan, "imports"):
        assert plan.imports == ()
    if hasattr(plan, "capabilities"):
        assert plan.capabilities == ()


@pytest.mark.parametrize(
    ("builder", "error_type"),
    ((build_wasm_plan, WasmBackendError), (build_native_plan, NativeBackendError)),
)
def test_backend_rejects_malformed_try_handler(builder, error_type):
    malformed = IRProgram(
        version=1,
        instructions=(
            IRInstruction("try_guard", ("handler", "protected_end")),
            IRInstruction("label", ("protected_end",)),
            IRInstruction("jump", ("join",)),
            IRInstruction("label", ("handler",)),
            IRInstruction("const", ("tam:1",), "%not_catch"),
            IRInstruction("label", ("join",)),
        ),
    )
    with pytest.raises(error_type, match="try control-flow"):
        builder(malformed)
