from __future__ import annotations

import pytest

from sahin.backend_equivalence import compare_source
from sahin.ir import IRInstruction, IRProgram, lower_source
from sahin.native_backend import NativeBackendError, build_native_plan
from sahin.wasm_backend import WasmBackendError, build_wasm_plan


def test_member_expression_lowers_to_explicit_ir_opcode():
    program = lower_source('uzunluk = "Şahin".uzunluk\nyaz uzunluk\n')

    members = [instruction for instruction in program.instructions if instruction.opcode == "member"]
    assert len(members) == 1
    assert members[0].operands[0] == "uzunluk"
    assert members[0].operands[1].startswith("%")
    assert members[0].result is not None and members[0].result.startswith("%")


def test_member_equivalence_matches_reference_runtime():
    report = compare_source('uzunluk = "Şahin".uzunluk\nyaz uzunluk\n')

    assert report.equivalent
    assert report.reference.state == (("uzunluk", 5),)
    assert report.reference.output == ("5",)
    assert report.wasm == report.reference
    assert report.native == report.reference


@pytest.mark.parametrize(
    ("builder", "error_type"),
    (
        (build_wasm_plan, WasmBackendError),
        (build_native_plan, NativeBackendError),
    ),
)
def test_member_schema_rejects_missing_target_temp(builder, error_type):
    program = IRProgram(1, (IRInstruction("member", ("uzunluk",), "%0"),))

    with pytest.raises(error_type):
        builder(program)


@pytest.mark.parametrize(
    ("builder", "error_type"),
    (
        (build_wasm_plan, WasmBackendError),
        (build_native_plan, NativeBackendError),
    ),
)
def test_member_rejects_non_dominating_target_temp(builder, error_type):
    program = IRProgram(
        1,
        (
            IRInstruction("const", ("evet_hayır:evet",), "%0"),
            IRInstruction("branch", ("%0", "true", "false")),
            IRInstruction("label", ("true",)),
            IRInstruction("const", ("metin:\"Şahin\"",), "%1"),
            IRInstruction("jump", ("join",)),
            IRInstruction("label", ("false",)),
            IRInstruction("jump", ("join",)),
            IRInstruction("label", ("join",)),
            IRInstruction("member", ("uzunluk", "%1"), "%2"),
        ),
    )

    with pytest.raises(error_type, match="tanımsız geçici değer"):
        builder(program)


def test_member_unknown_runtime_member_is_not_silently_accepted():
    with pytest.raises(Exception):
        compare_source('sonuç = "Şahin".bilinmeyen\n')
