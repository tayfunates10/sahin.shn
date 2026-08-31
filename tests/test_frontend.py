from decimal import Decimal

import pytest

from sahin.lexer import LexerError, tokenize
from sahin.parser import parse
from sahin.runtime import Runtime, RuntimeErrorSHN
from sahin.tokens import TokenKind


def test_turkish_unicode_identifiers_and_custom_tokens():
    source = """ürünler <- Ürün\nfiyat = 249,90₺\nyol -> hedef\naralık = 1..10\n"""
    tokens = tokenize(source)
    values = [(token.kind, token.value) for token in tokens]

    assert (TokenKind.IDENTIFIER, "ürünler") in values
    assert (TokenKind.BIND, "<-") in values
    assert (TokenKind.NUMBER, "249.90₺") in values
    assert (TokenKind.ARROW, "->") in values
    assert (TokenKind.RANGE, "..") in values


def test_minimal_program_runs_end_to_end():
    source = """ad = \"Şahin\"\naktif = evet\nfiyat = 10,50₺\nyaz ad\nyaz aktif\nyaz fiyat\n"""
    output: list[str] = []

    program = parse(tokenize(source))
    values = Runtime(output.append).execute(program)

    assert values["ad"] == "Şahin"
    assert values["aktif"] is True
    assert values["fiyat"] == Decimal("10.50")
    assert output == ["Şahin", "evet", "10.50"]


def test_runtime_suggests_close_turkish_name():
    source = """ürün = \"Kalem\"\nyaz ürn\n"""
    program = parse(tokenize(source))

    with pytest.raises(RuntimeErrorSHN, match="ürün"):
        Runtime(lambda _: None).execute(program)


def test_bad_indentation_is_explained_in_turkish():
    with pytest.raises(LexerError, match="girinti"):
        tokenize("ekran Ana\n   yaz \"hata\"\n")
