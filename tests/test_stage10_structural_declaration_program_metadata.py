from __future__ import annotations

import pytest

from sahin.ast_nodes import Assignment, Declaration, Literal, Name, Parameter, Program
from sahin.structural_declaration_abi import (
    StructuralDeclarationABIError,
    extract_structural_declaration_metadata,
)


def test_extract_structural_metadata_preserves_source_order_and_ignores_other_statements() -> None:
    program = Program(
        (
            Assignment("x", Literal(1)),
            Declaration("uygulama", "Ana", body=()),
            Declaration("akış", "hesapla", parameters=(Parameter("x"),), body=()),
            Declaration("uç", "listele", header=(Name("GET"),), body=()),
            Declaration("ekran", "Giris", body=()),
        )
    )

    metadata = extract_structural_declaration_metadata(program)

    assert [(item.kind, item.name, item.header_arity, item.body_arity) for item in metadata] == [
        ("uygulama", "Ana", 0, 0),
        ("uç", "listele", 1, 0),
        ("ekran", "Giris", 0, 0),
    ]


def test_program_level_extractor_reuses_fail_closed_shape_validation() -> None:
    program = Program((Declaration("ekran", "Giris", header=(Literal("yasak"),)),))

    with pytest.raises(StructuralDeclarationABIError, match="header kabul etmiyor"):
        extract_structural_declaration_metadata(program)


def test_program_level_extractor_does_not_invent_motor_semantics() -> None:
    program = Program(
        (
            Declaration("iş", "gece", header=(Name("zaman"), Literal("03:00")), body=()),
            Declaration("olay", "tikla", header=(Name("buton"),), body=()),
        )
    )

    metadata = extract_structural_declaration_metadata(program)

    assert metadata[0].header_arity == 2
    assert metadata[1].header_arity == 1
    assert not hasattr(metadata[0], "capabilities")
    assert not hasattr(metadata[1], "opcode")
