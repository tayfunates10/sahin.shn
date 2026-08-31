from __future__ import annotations

import random
import unicodedata
from pathlib import Path

from sahin.ast_dump import dump_ast
from sahin.ast_nodes import Binding
from sahin.lexer import tokenize
from sahin.parser import parse
from sahin.semantics import analyze


GOLDEN = Path(__file__).parent / "golden" / "parser_core.ast"


def test_parser_core_matches_golden_native_ast_contract():
    source = """kayıt Ürün
    ad: yazı gerekli

ekran Ana
    ürünler <- Ürün.tümü | ilk 10
"""
    program = parse(tokenize(source))

    assert isinstance(program.statements[1].body[0], Binding)
    assert dump_ast(program) == GOLDEN.read_text(encoding="utf-8")


def test_turkish_unicode_identifier_property_suite_is_nfc_stable():
    rng = random.Random(20260831)
    alphabet = "abcçdefgğhıijklmnoöprsştuüvyz"

    for index in range(100):
        suffix = "".join(rng.choice(alphabet) for _ in range(rng.randint(3, 14)))
        identifier = f"değer_{index}_{suffix}"
        decomposed = unicodedata.normalize("NFD", identifier)
        canonical = unicodedata.normalize("NFC", identifier)

        source = f"{decomposed} = {index}\nyaz {decomposed}\n"
        program = parse(tokenize(source))
        model = analyze(program)

        assert model.ok, [diagnostic.format() for diagnostic in model.diagnostics]
        assert canonical in model.global_symbols


def test_unicode_property_suite_preserves_turkish_dotless_i_and_dotted_i_names():
    source = "ışık = 1\nİzmir = 2\nyaz ışık\nyaz İzmir\n"
    model = analyze(parse(tokenize(source)))

    assert model.ok
    assert "ışık" in model.global_symbols
    assert "İzmir" in model.global_symbols
