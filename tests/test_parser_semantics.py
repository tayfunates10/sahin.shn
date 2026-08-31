import unicodedata

import pytest

from sahin.ast_nodes import (
    Binary,
    Call,
    Declaration,
    ForEach,
    IfStatement,
    MatchStatement,
    Pipeline,
)
from sahin.lexer import tokenize
from sahin.parser import ParserError, parse
from sahin.semantics import TypeKind, analyze


def test_readme_shop_example_parses_into_native_sahin_ast():
    source = """kayıt Ürün
    ad: yazı
    fiyat: para
    stok: sayı

ekran Ana
    başlık "Ürünler"
    ürünler <- Ürün.tümü
    her ürün içinden ürünler
        kart
            başlık ürün.ad
            metin ürün.fiyat
            eylem "Satın al" -> satınAl ürün

akış satınAl ürün
    ürün.stok <= 0 ise
        bildir "Ürün tükendi"
        bitir
    ürün.stok azalt 1
    sakla ürün
    bildir "Satın alma başarılı"
"""
    program = parse(tokenize(source))

    assert [node.kind for node in program.statements if isinstance(node, Declaration)] == [
        "kayıt",
        "ekran",
        "akış",
    ]
    screen = program.statements[1]
    assert isinstance(screen, Declaration)
    assert isinstance(screen.body[2], ForEach)

    flow = program.statements[2]
    assert isinstance(flow, Declaration)
    assert isinstance(flow.body[0], IfStatement)

    model = analyze(program)
    assert model.ok, [diagnostic.format() for diagnostic in model.diagnostics]


def test_expression_precedence_keeps_multiplication_tighter_than_addition():
    program = parse(tokenize("sonuç = 1 + 2 * 3\n"))
    expression = program.statements[0].expression

    assert isinstance(expression, Binary)
    assert expression.operator == "+"
    assert isinstance(expression.right, Binary)
    assert expression.right.operator == "*"


def test_multiline_pipeline_is_one_expression():
    program = parse(
        tokenize(
            """aktifler <- kullanıcılar
    | seç aktif
    | sırala ad
    | ilk 20
"""
        )
    )
    expression = program.statements[0].expression

    assert isinstance(expression, Pipeline)
    assert [stage.name for stage in expression.stages] == ["seç", "sırala", "ilk"]


def test_match_try_and_implicit_flow_call_parse():
    source = """duruma göre sipariş.durum
    "hazır" -> bildir "Sipariş hazır"
    diğer -> bildir "İşleniyor"

dene
    profil <- uzak.profil al
olmazsa hata
    bildir "Profil alınamadı"
"""
    program = parse(tokenize(source))

    assert isinstance(program.statements[0], MatchStatement)
    assignment = program.statements[1].body[0]
    assert isinstance(assignment.expression, Call)


def test_semantics_infers_types_and_rejects_bound_value_overwrite():
    source = """ad = "Şahin"
adet = 4
profil <- ad
profil = "başka"
yaz ads
"""
    model = analyze(parse(tokenize(source)))

    assert model.global_symbols["ad"].type_kind is TypeKind.YAZI
    assert model.global_symbols["adet"].type_kind is TypeKind.SAYI
    codes = {diagnostic.code for diagnostic in model.diagnostics}
    assert "SHN-S201" in codes
    assert "SHN-S301" in codes
    assert any("Şunu mu demek istediniz" in d.message for d in model.diagnostics)


def test_missing_required_block_has_turkish_location_diagnostic():
    with pytest.raises(ParserError, match="4 boşluk"):
        parse(tokenize('ekran Ana\nyaz "hata"\n'))


def test_decomposed_turkish_identifier_is_normalized_to_nfc():
    decomposed = "s\u0327ehir"
    assert decomposed != unicodedata.normalize("NFC", decomposed)

    program = parse(tokenize(f'{decomposed} = "Edremit"\nyaz şehir\n'))
    model = analyze(program)

    assert "şehir" in model.global_symbols
    assert model.ok
