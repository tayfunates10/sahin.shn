from decimal import Decimal

import pytest

from sahin.ast_nodes import ExpressionStatement, IfStatement, Literal, Name, Program, Write
from sahin.ir import IRLoweringError, lower_program, lower_source


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


def test_ir_v1_fails_closed_for_ast_nodes_not_yet_supported():
    program = Program(
        statements=(
            IfStatement(
                condition=Literal(True),
                body=(Write(Literal(Decimal("1"))),),
            ),
        )
    )

    with pytest.raises(IRLoweringError, match="IfStatement"):
        lower_program(program)


def test_ir_v1_fails_closed_for_short_circuit_boolean_lowering():
    with pytest.raises(IRLoweringError, match="kısa devreli 've/veya'"):
        lower_source("sonuç = evet veya (1 / 0 == 1)\n")


def test_ir_v1_rejects_unvalidated_expression_statement():
    program = Program(statements=(ExpressionStatement(Name("bilinmeyen")),))

    with pytest.raises(IRLoweringError, match="ExpressionStatement"):
        lower_program(program)
