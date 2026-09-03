import pytest

from sahin.backend_equivalence import compare_source
from sahin.ir import IRLoweringError, lower_source
from sahin.ir_control_flow import validate_control_flow
from sahin.native_backend import build_native_plan
from sahin.wasm_backend import build_wasm_plan


def test_match_subject_is_lowered_once_and_cases_keep_source_order():
    program = lower_source(
        "akış konu => 2\n"
        "duruma göre konu()\n"
        "    1 -> yaz \"bir\"\n"
        "    2 -> yaz \"iki\"\n"
        "    3 -> yaz \"üç\"\n"
    )

    assert sum(item.opcode == "call" for item in program.instructions) == 1
    comparisons = [
        item
        for item in program.instructions
        if item.opcode == "binary" and item.operands[0] == "=="
    ]
    assert len(comparisons) == 3
    validate_control_flow(program)


def test_match_reference_wasm_native_equivalence_executes_only_first_match():
    report = compare_source(
        "değer = 2\n"
        "duruma göre değer\n"
        "    2 -> yaz \"ilk\"\n"
        "    2 -> yaz \"ikinci\"\n"
        "    3 -> yaz \"üç\"\n"
    )

    assert report.equivalent
    assert report.reference.state == (("değer", 2),)
    assert report.reference.output == ("ilk",)


def test_match_unmatched_subject_has_no_case_side_effect():
    report = compare_source(
        "değer = 9\n"
        "duruma göre değer\n"
        "    1 -> yaz \"bir\"\n"
        "    2 -> yaz \"iki\"\n"
    )

    assert report.equivalent
    assert report.reference.output == ()


def test_match_backend_plans_preserve_existing_control_flow_without_new_capabilities():
    program = lower_source(
        "değer = 1\n"
        "duruma göre değer\n"
        "    1 -> bildir \"eşleşti\"\n"
    )

    wasm = build_wasm_plan(program)
    native = build_native_plan(program)
    assert wasm.instructions == program.instructions
    assert native.instructions == program.instructions
    assert wasm.imports == ()
    assert native.capabilities == ()


def test_match_case_with_unsupported_command_remains_fail_closed():
    with pytest.raises(IRLoweringError, match="sakla"):
        lower_source(
            "değer = 1\n"
            "duruma göre değer\n"
            "    1 -> sakla değer\n"
        )
