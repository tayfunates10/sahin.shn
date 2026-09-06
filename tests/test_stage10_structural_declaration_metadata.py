import pytest

from sahin.ast_nodes import Declaration, Literal, Parameter, Write
from sahin.structural_declaration_abi import (
    StructuralDeclarationABIError,
    analyze_structural_declaration,
)


def test_named_structural_declaration_shape_is_deterministic():
    declaration = Declaration(
        kind="uygulama",
        name="Panel",
        body=(Write(Literal("çalışmamalı")),),
    )

    metadata = analyze_structural_declaration(declaration)

    assert metadata.kind == "uygulama"
    assert metadata.name == "Panel"
    assert metadata.header_arity == 0
    assert metadata.body_arity == 1


def test_loose_header_shape_is_counted_without_executing_or_serializing_expressions():
    declaration = Declaration(
        kind="uç",
        name="listele",
        header=(Literal("GET"), Literal("/ürünler")),
        body=(Write(Literal("çalışmamalı")),),
    )

    metadata = analyze_structural_declaration(declaration)

    assert metadata.kind == "uç"
    assert metadata.name == "listele"
    assert metadata.header_arity == 2
    assert metadata.body_arity == 1


def test_event_requires_header_identity():
    with pytest.raises(StructuralDeclarationABIError, match="header"):
        analyze_structural_declaration(Declaration(kind="olay", name=None))


@pytest.mark.parametrize("kind", ["uygulama", "ekran", "görünüm"])
def test_named_no_header_declarations_reject_header(kind):
    declaration = Declaration(kind=kind, name="örnek", header=(Literal("beklenmeyen"),))

    with pytest.raises(StructuralDeclarationABIError, match="header"):
        analyze_structural_declaration(declaration)


def test_structural_declaration_rejects_flow_only_shape_fields():
    declaration = Declaration(
        kind="iş",
        name="yenile",
        parameters=(Parameter("x"),),
    )

    with pytest.raises(StructuralDeclarationABIError, match="parametre"):
        analyze_structural_declaration(declaration)


def test_non_structural_declaration_is_fail_closed():
    with pytest.raises(StructuralDeclarationABIError, match="Desteklenmeyen"):
        analyze_structural_declaration(Declaration(kind="akış", name="hesapla"))
