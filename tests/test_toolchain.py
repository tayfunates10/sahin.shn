from __future__ import annotations

import unicodedata

import pytest

from sahin.lexer import LexerError
from sahin.toolchain import format_source


def test_formatter_is_idempotent_and_has_final_newline() -> None:
    source = "yaz 1   \r\n\r\n\r\nyaz 2  "
    once = format_source(source)
    twice = format_source(once)

    assert once == "yaz 1\n\nyaz 2\n"
    assert twice == once


def test_formatter_normalizes_unicode_to_nfc() -> None:
    source = "yaz \"go\u0308ru\u0308nu\u0308m\"\n"
    formatted = format_source(source)

    assert formatted == unicodedata.normalize("NFC", formatted)


def test_formatter_preserves_semantic_indentation() -> None:
    source = "eger ise\n    yaz 1\n"

    # Formatter girintiyi yeniden yorumlamaz; lexer/parser dışındaki anlamsal
    # kararları bu çekirdek dilimde üstlenmez.
    assert format_source(source).splitlines()[1].startswith("    ")


def test_formatter_rejects_tab_indentation() -> None:
    with pytest.raises(LexerError):
        format_source("eger ise\n\tyaz 1\n")


def test_formatter_rejects_noncanonical_indentation_width() -> None:
    with pytest.raises(LexerError):
        format_source("eger ise\n  yaz 1\n")
