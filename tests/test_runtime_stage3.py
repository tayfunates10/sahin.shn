from __future__ import annotations

import pytest

from sahin.ast_nodes import (
    Assignment,
    Binding,
    Literal,
    Name,
    Pipeline,
    PipelineStage,
    Program,
    SourceLocation,
    Write,
)
from sahin.lexer import tokenize
from sahin.parser import parse
from sahin.runtime import Runtime, RuntimeErrorSHN


def run(source: str):
    output: list[str] = []
    values = Runtime(output.append).execute(parse(tokenize(source)))
    return values, output


def test_flow_call_return_binary_and_lexical_scope_end_to_end():
    source = """taban = 10
akış topla a, b
    ver a + b + taban
sonuç = topla(2, 3)
yaz sonuç
"""
    values, output = run(source)

    assert values["sonuç"] == 15
    assert output == ["15"]


def test_postfix_if_else_and_inclusive_range_loop():
    source = """toplam = 0
her sayı içinden 1..3
    toplam = toplam + sayı
toplam == 6 ise
    yaz "doğru"
yoksa
    yaz "yanlış"
"""
    values, output = run(source)

    assert values["toplam"] == 6
    assert output == ["doğru"]


def test_binding_cannot_be_reassigned_with_assignment():
    source = """sabit <- 7
sabit = 8
"""
    with pytest.raises(RuntimeErrorSHN, match="bağlandığı"):
        run(source)


def test_try_olmazsa_catches_sahin_runtime_error():
    source = """dene
    yaz bilinmeyen
olmazsa hata
    yaz "yakalandı"
"""
    _, output = run(source)
    assert output == ["yakalandı"]


def test_runtime_error_contains_sahin_source_location_and_flow_chain():
    source = """akış iç
    yaz bulunmayan
akış dış
    iç()
dış()
"""
    with pytest.raises(RuntimeErrorSHN) as captured:
        run(source)

    text = str(captured.value)
    assert "satır" in text
    assert "Akış zinciri" in text
    assert "iç" in text
    assert "dış" in text


def test_pipeline_first_is_deterministic_on_ast_contract():
    pipeline = Pipeline(
        source=Name("veriler"),
        stages=(PipelineStage("ilk", (Literal(2),)),),
    )
    program = Program((
        Assignment("veriler", Literal((3, 1, 2))),
        Assignment("sonuç", pipeline),
    ))

    values = Runtime(lambda _: None).execute(program)
    assert values["sonuç"] == (3, 1)


def test_pipeline_sort_and_field_selection_on_ast_contract():
    loc = SourceLocation(1, 1)
    # Literal tipi kullanıcı sözdizimi için sınırlıdır; runtime koleksiyon sözleşmesini
    # doğrudan frame'e vererek pipeline motorunu izole biçimde doğruluyoruz.
    runtime = Runtime(lambda _: None)
    runtime.global_frame.define("kişiler", (
        {"ad": "C", "aktif": True},
        {"ad": "A", "aktif": False},
        {"ad": "B", "aktif": True},
    ))
    pipeline = Pipeline(
        Name("kişiler", loc),
        (
            PipelineStage("seç", (Literal("aktif", loc),), loc),
            PipelineStage("sırala", (Literal("ad", loc),), loc),
        ),
        loc,
    )
    values = runtime.execute(Program((Assignment("sonuç", pipeline, location=loc),)))

    assert [item["ad"] for item in values["sonuç"]] == ["B", "C"]


def test_nearest_name_regression_still_works_in_nested_scope():
    source = """ürün = "Kalem"
akış göster
    yaz ürn
göster()
"""
    with pytest.raises(RuntimeErrorSHN, match="ürün"):
        run(source)
