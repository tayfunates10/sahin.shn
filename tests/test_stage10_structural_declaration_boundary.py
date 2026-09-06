import pytest

from sahin.ast_nodes import Declaration, Literal, Program, Write
from sahin.ir import IRLoweringError, lower_program
from sahin.runtime import Runtime


STRUCTURAL_KINDS = ("uygulama", "ekran", "görünüm", "uç", "iş", "olay")


@pytest.mark.parametrize("kind", STRUCTURAL_KINDS)
def test_structural_declaration_is_runtime_noop(kind):
    outputs: list[str] = []
    declaration = Declaration(
        kind=kind,
        name=f"{kind}_örnek",
        body=(Write(Literal("çalışmamalı")),),
    )

    values = Runtime(output=outputs.append).execute(Program((declaration,)))

    assert outputs == []
    assert values == {}


@pytest.mark.parametrize("kind", STRUCTURAL_KINDS)
def test_structural_declaration_remains_fail_closed_in_ir(kind):
    declaration = Declaration(
        kind=kind,
        name=f"{kind}_örnek",
        body=(Write(Literal("çalışmamalı")),),
    )

    with pytest.raises(IRLoweringError, match="Declaration ABI"):
        lower_program(Program((declaration,)))
