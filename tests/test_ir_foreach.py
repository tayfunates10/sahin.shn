import pytest

from sahin.backend_validation import validate_backend_program
from sahin.ir import IRInstruction, IRProgram, lower_source
from sahin.ir_control_flow import IRControlFlowError, validate_control_flow


def test_foreach_lowers_iterable_once_with_lexical_loop_scope():
    program = lower_source(
        "toplam = 0\n"
        "her sayı içinden 1..3\n"
        "    toplam = toplam + sayı\n"
    )

    opcodes = [instruction.opcode for instruction in program.instructions]
    assert opcodes.count("range") == 1
    assert opcodes.count("iter_begin") == 1
    assert opcodes.count("iter_has_next") == 1
    assert opcodes.count("iter_value") == 1
    assert opcodes.count("iter_advance") == 1
    assert opcodes.index("range") < opcodes.index("iter_begin") < opcodes.index("iter_has_next")

    loop_stores = [
        instruction
        for instruction in program.instructions
        if instruction.opcode == "store" and instruction.operands[0].endswith("_sayı")
    ]
    assert len(loop_stores) == 1
    assert loop_stores[0].operands[0].startswith("__shn_scope_")

    validate_control_flow(program)


def test_foreach_bitir_jumps_to_innermost_loop_end():
    program = lower_source(
        "her sayı içinden 1..3\n"
        "    bitir\n"
    )

    end_labels = [
        instruction.operands[0]
        for instruction in program.instructions
        if instruction.opcode == "label" and instruction.operands[0].endswith("_end")
    ]
    assert len(end_labels) == 1
    end_label = end_labels[0]
    jumps = [instruction.operands[0] for instruction in program.instructions if instruction.opcode == "jump"]
    assert end_label in jumps
    validate_control_flow(program)


def test_iterator_opcode_schema_is_fail_closed():
    malformed = IRProgram(
        version=1,
        instructions=(IRInstruction("iter_begin", ("not-a-temp",), "%0"),),
    )
    with pytest.raises(IRControlFlowError):
        validate_control_flow(malformed)


def test_foreach_backend_remains_closed_until_adapter_equivalence_slice():
    program = lower_source(
        "her sayı içinden 1..2\n"
        "    yaz sayı\n"
    )

    with pytest.raises(ValueError, match="desteklenmeyen opcode"):
        validate_backend_program(
            program,
            error_type=ValueError,
            backend_name="test",
        )
