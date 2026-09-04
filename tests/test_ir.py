from decimal import Decimal

import pytest

from sahin.ast_nodes import (
    Assignment,
    Binding,
    ExpressionStatement,
    IfStatement,
    Literal,
    Name,
    Program,
    Write,
)
from sahin.ir import IRLoweringError, lower_program, lower_source
from sahin.ir_control_flow import validate_control_flow


def test_ir_is_deterministic_for_same_source():
    source = 'ad = "Şahin"\nsayı = 2 + 3\nyaz ad\nyaz sayı\n'

    first = lower_source(source)
    second = lower_source(source)

    assert first == second
    assert first.canonical() == second.canonical()
    assert first.canonical().startswith('{"instructions":[')
    assert '"version":1' in first.canonical()


def test_ir_uses_explicit_stable_literal_encoding():
    program = lower_source('fiyat = 10,50₺\naktif = evet\nyaz fiyat\nyaz aktif\n')
    canonical = program.canonical()

    assert 'ondalık:10.50' in canonical
    assert 'evet_hayır:evet' in canonical
    assert '"op":"store"' in canonical
    assert '"op":"write"' in canonical


def test_ir_rejects_semantically_invalid_source_before_lowering():
    with pytest.raises(IRLoweringError, match="Semantik doğrulama başarısız"):
        lower_source("yaz bilinmeyen\n")


def test_ir_v1_lowers_if_statement_with_deterministic_control_flow():
    program = Program(
        statements=(
            IfStatement(
                condition=Literal(True),
                body=(Write(Literal(Decimal("1"))),),
                else_body=(Write(Literal(Decimal("2"))),),
            ),
        )
    )

    lowered = lower_program(program)
    opcodes = tuple(instruction.opcode for instruction in lowered.instructions)

    assert opcodes == (
        "const",
        "branch",
        "label",
        "const",
        "write",
        "jump",
        "label",
        "const",
        "write",
        "jump",
        "label",
    )
    assert lowered.instructions[1].operands == (
        "%0",
        "__shn_if_0_true",
        "__shn_if_0_false",
    )
    assert validate_control_flow(lowered).labels == (
        "__shn_if_0_true",
        "__shn_if_0_false",
        "__shn_if_0_end",
    )


def test_ir_v1_preserves_if_branch_lexical_shadowing():
    program = Program(
        statements=(
            Assignment("x", Literal(Decimal("1"))),
            IfStatement(
                condition=Literal(True),
                body=(
                    Binding("x", Literal(Decimal("2"))),
                    Write(Name("x")),
                ),
                else_body=(),
            ),
            Write(Name("x")),
        )
    )

    lowered = lower_program(program)
    binds = [item for item in lowered.instructions if item.opcode == "bind"]
    loads = [item for item in lowered.instructions if item.opcode == "load"]

    assert len(binds) == 1
    assert binds[0].operands[0] == "__shn_scope_0_x"
    assert loads[0].operands == ("__shn_scope_0_x",)
    assert loads[-1].operands == ("x",)
    validate_control_flow(lowered)


def test_ir_v1_branch_assignment_to_outer_name_keeps_outer_identity():
    program = Program(
        statements=(
            Assignment("x", Literal(Decimal("1"))),
            IfStatement(
                condition=Literal(True),
                body=(Assignment("x", Literal(Decimal("2"))),),
                else_body=(),
            ),
            Write(Name("x")),
        )
    )

    lowered = lower_program(program)
    stores = [item for item in lowered.instructions if item.opcode == "store"]
    loads = [item for item in lowered.instructions if item.opcode == "load"]

    assert [item.operands[0] for item in stores] == ["x", "x"]
    assert loads[-1].operands == ("x",)
    validate_control_flow(lowered)


def test_ir_v1_nested_if_labels_are_unique_and_deterministic():
    nested = IfStatement(
        condition=Literal(False),
        body=(Write(Literal(Decimal("3"))),),
    )
    program = Program(
        statements=(
            IfStatement(condition=Literal(True), body=(nested,), else_body=()),
        )
    )

    first = lower_program(program)
    second = lower_program(program)
    labels = [item.operands[0] for item in first.instructions if item.opcode == "label"]

    assert first == second
    assert len(labels) == len(set(labels))
    assert "__shn_if_0_true" in labels
    assert "__shn_if_1_true" in labels
    validate_control_flow(first)


def test_ir_v1_lowers_or_with_lazy_rhs_control_flow():
    lowered = lower_source("sonuç = evet veya (1 / 0 == 1)\nyaz sonuç\n")
    opcodes = tuple(item.opcode for item in lowered.instructions)

    assert opcodes[:2] == ("const", "branch")
    branch = lowered.instructions[1]
    assert branch.operands[1:] == ("__shn_logic_0_short", "__shn_logic_0_rhs")
    rhs_label_index = next(
        index for index, item in enumerate(lowered.instructions)
        if item.opcode == "label" and item.operands == ("__shn_logic_0_rhs",)
    )
    binary_indices = [index for index, item in enumerate(lowered.instructions) if item.opcode == "binary"]
    assert binary_indices and min(binary_indices) > rhs_label_index
    validate_control_flow(lowered)


def test_ir_v1_lowers_and_with_false_short_circuit_value():
    lowered = lower_source("sonuç = hayır ve (1 / 0 == 1)\nyaz sonuç\n")
    branch = next(item for item in lowered.instructions if item.opcode == "branch")

    assert branch.operands[1:] == ("__shn_logic_0_rhs", "__shn_logic_0_short")
    assert any(
        item.opcode == "const" and item.operands == ("evet_hayır:hayır",)
        for item in lowered.instructions
    )
    validate_control_flow(lowered)


def test_ir_v1_lowers_semantically_valid_expression_statement_and_discards_result():
    program = Program(statements=(ExpressionStatement(Literal(Decimal("3"))),))

    lowered = lower_program(program)

    assert tuple(item.opcode for item in lowered.instructions) == ("const",)
    assert lowered.instructions[0].result == "%0"


def test_ir_v1_rejects_semantically_invalid_expression_statement_before_lowering():
    with pytest.raises(IRLoweringError, match="Semantik doğrulama başarısız"):
        lower_source("bilinmeyen()\n")
