import pytest

from sahin.ir import IRLoweringError, lower_source
from sahin.ir_control_flow import validate_control_flow


def test_try_statement_lowers_to_guard_catch_and_scoped_error_binding():
    program = lower_source(
        '''dene
    yaz "korunan"
olmazsa hata
    yaz hata
'''
    )

    instructions = program.instructions
    assert instructions[0].opcode == "try_guard"
    handler, protected_end = instructions[0].operands
    assert handler == "__shn_try_0_handler"
    assert protected_end == "__shn_try_0_protected_end"

    catch_index = next(index for index, item in enumerate(instructions) if item.opcode == "catch")
    catch = instructions[catch_index]
    assert catch.result is not None
    assert instructions[catch_index + 1].opcode == "store"
    assert instructions[catch_index + 1].operands == ("__shn_scope_1_hata", catch.result)

    summary = validate_control_flow(program)
    assert handler in summary.labels
    assert protected_end in summary.labels


def test_try_normal_path_jumps_over_handler_instead_of_falling_through():
    program = lower_source(
        '''dene
    yaz "tamam"
olmazsa hata
    yaz hata
'''
    )
    instructions = program.instructions
    protected_end_index = next(
        index
        for index, item in enumerate(instructions)
        if item.opcode == "label" and item.operands == ("__shn_try_0_protected_end",)
    )

    assert instructions[protected_end_index + 1].opcode == "jump"
    assert instructions[protected_end_index + 1].operands == ("__shn_try_0_end",)
    validate_control_flow(program)


def test_try_error_binding_does_not_escape_handler_scope():
    with pytest.raises(IRLoweringError, match="Semantik doğrulama başarısız"):
        lower_source(
            '''dene
    yaz "tamam"
olmazsa hata
    yaz hata
yaz hata
'''
        )


def test_try_without_error_name_still_consumes_exception_with_catch():
    program = lower_source(
        '''dene
    yaz "tamam"
olmazsa
    yaz "kurtarıldı"
'''
    )

    catches = [item for item in program.instructions if item.opcode == "catch"]
    assert len(catches) == 1
    assert catches[0].result is not None
    validate_control_flow(program)
