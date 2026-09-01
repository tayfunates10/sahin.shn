from __future__ import annotations

import pytest

from sahin.lexer import LexerError
from sahin.lsp import LspAdapter
from sahin.parser import ParserError


def test_lsp_snapshot_reuses_semantic_diagnostics_and_symbols() -> None:
    source = "deger = 1\nyaz eksik\n"
    snapshot = LspAdapter().snapshot(source)

    assert tuple(symbol.name for symbol in snapshot.symbols) == ("deger",)
    assert len(snapshot.diagnostics) == 1
    assert snapshot.diagnostics[0].rule == "SHN-S301"
    assert snapshot.diagnostics[0].line == 2
    assert snapshot.diagnostics[0].column == 5


def test_lsp_completions_are_deterministic_and_prefix_filtered() -> None:
    source = "zeta = 1\nalfa = 2\nalpaca = 3\n"
    adapter = LspAdapter()

    assert adapter.completions(source) == ("alfa", "alpaca", "zeta")
    assert adapter.completions(source, "al") == ("alfa", "alpaca")


def test_lsp_hover_and_definition_use_semantic_symbol_location() -> None:
    source = "deger = 1\nyaz deger\n"
    adapter = LspAdapter()

    hover = adapter.hover(source, 2, 7)
    definition = adapter.definition(source, 2, 7)

    assert hover is not None
    assert hover.name == "deger"
    assert "değer" in hover.detail
    assert definition is not None
    assert definition.name == "deger"
    assert definition.position.line == 1
    assert definition.position.column == 1


def test_lsp_symbol_info_is_sorted_and_source_located() -> None:
    source = "ikinci = 2\nbirinci = 1\n"
    symbols = LspAdapter().symbol_info(source)

    assert tuple(symbol.name for symbol in symbols) == ("birinci", "ikinci")
    assert tuple((symbol.line, symbol.column) for symbol in symbols) == ((2, 1), (1, 1))


def test_lsp_unknown_symbol_has_no_hover_or_definition() -> None:
    source = "deger = 1\nyaz deger\n"
    adapter = LspAdapter()

    assert adapter.hover(source, 2, 1) is None
    assert adapter.definition(source, 2, 1) is None


def test_lsp_fails_closed_on_lexical_errors() -> None:
    with pytest.raises(LexerError):
        LspAdapter().snapshot("eger ise\n\tyaz 1\n")


def test_lsp_fails_closed_on_parser_errors() -> None:
    with pytest.raises(ParserError):
        LspAdapter().snapshot("yaz\n")
