import pytest

from sahin.ir import IRInstruction, IRProgram
from sahin.ir_control_flow import IRControlFlowError, validate_control_flow


def test_control_flow_contract_accepts_forward_labels_and_branch() -> None:
    program = IRProgram(
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

    summary = validate_control_flow(program)

    assert summary.labels == ("then", "else", "end")
    assert summary.jump_targets == ("then", "else", "end", "end")


def test_control_flow_contract_rejects_missing_target() -> None:
    program = IRProgram(version=1, instructions=(IRInstruction("jump", ("missing",)),))

    with pytest.raises(IRControlFlowError, match="Tanımsız control-flow hedefi"):
        validate_control_flow(program)


def test_control_flow_contract_rejects_duplicate_label() -> None:
    program = IRProgram(
        version=1,
        instructions=(IRInstruction("label", ("same",)), IRInstruction("label", ("same",))),
    )

    with pytest.raises(IRControlFlowError, match="Yinelenen control-flow etiketi"):
        validate_control_flow(program)


def test_control_flow_contract_rejects_branch_with_undefined_temp() -> None:
    program = IRProgram(
        version=1,
        instructions=(
            IRInstruction("branch", ("%0", "yes", "no")),
            IRInstruction("label", ("yes",)),
            IRInstruction("label", ("no",)),
        ),
    )

    with pytest.raises(IRControlFlowError, match="tüm ulaşılabilir giriş yollarında tanımlı"):
        validate_control_flow(program)


def test_control_flow_contract_rejects_non_dominating_branch_temp() -> None:
    program = IRProgram(
        version=1,
        instructions=(
            IRInstruction("const", ("evet_hayır:evet",), "%0"),
            IRInstruction("branch", ("%0", "then", "else")),
            IRInstruction("label", ("then",)),
            IRInstruction("const", ("evet_hayır:evet",), "%1"),
            IRInstruction("jump", ("join",)),
            IRInstruction("label", ("else",)),
            IRInstruction("jump", ("join",)),
            IRInstruction("label", ("join",)),
            IRInstruction("branch", ("%1", "yes", "no")),
            IRInstruction("label", ("yes",)),
            IRInstruction("label", ("no",)),
        ),
    )

    with pytest.raises(IRControlFlowError, match="tüm ulaşılabilir giriş yollarında tanımlı"):
        validate_control_flow(program)


def test_control_flow_contract_accepts_dominating_branch_temp() -> None:
    program = IRProgram(
        version=1,
        instructions=(
            IRInstruction("const", ("evet_hayır:evet",), "%0"),
            IRInstruction("branch", ("%0", "then", "else")),
            IRInstruction("label", ("then",)),
            IRInstruction("jump", ("join",)),
            IRInstruction("label", ("else",)),
            IRInstruction("jump", ("join",)),
            IRInstruction("label", ("join",)),
            IRInstruction("branch", ("%0", "yes", "no")),
            IRInstruction("label", ("yes",)),
            IRInstruction("label", ("no",)),
        ),
    )

    validate_control_flow(program)


def test_control_flow_contract_rejects_unknown_opcode() -> None:
    program = IRProgram(
        version=1,
        instructions=(
            IRInstruction("branche", ("evet_hayır:evet",), "%0"),
        ),
    )

    with pytest.raises(IRControlFlowError, match="Bilinmeyen IR opcode"):
        validate_control_flow(program)


@pytest.mark.parametrize(
    "instruction",
    [
        IRInstruction("label", ()),
        IRInstruction("jump", ("a",), "%0"),
        IRInstruction("branch", ("%0", "a")),
        IRInstruction("label", ("%0",)),
    ],
)
def test_control_flow_contract_rejects_malformed_instructions(instruction: IRInstruction) -> None:
    prefix = ()
    if instruction.opcode == "branch":
        prefix = (IRInstruction("const", ("evet_hayır:evet",), "%0"),)
    program = IRProgram(version=1, instructions=prefix + (instruction,))

    with pytest.raises(IRControlFlowError):
        validate_control_flow(program)
