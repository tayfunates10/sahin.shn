import pytest

from sahin.lexer import tokenize
from sahin.parser import parse
from sahin.runtime import Runtime, RuntimeErrorSHN
from sahin.try_backend_equivalence import compare_try_source
from sahin.wasm_backend import build_wasm_plan_from_source


def test_reference_runtime_wraps_unary_type_error_with_source_location():
    source = 'yaz -"metin"\n'

    with pytest.raises(RuntimeErrorSHN) as caught:
        Runtime(lambda _: None).execute(parse(tokenize(source)))

    message = str(caught.value)
    assert "Şahin çalışma hatası (satır 1, sütun 5)" in message
    assert "'-' işlemi uygulanamadı" in message
    assert "bad operand type for unary -" in message


def test_top_level_valid_unary_instruction_has_source_provenance():
    plan = build_wasm_plan_from_source("yaz -1\n")

    unary = [item for item in plan.source_provenance if item.kind == "unary"]
    assert len(unary) == 1
    assert unary[0].flow_name is None
    assert (unary[0].line, unary[0].column) == (1, 5)


def test_flow_try_unary_error_payload_matches_wasm_and_native_for_dynamic_parameter():
    report = compare_try_source(
        '''akış boz değer
    dene
        yaz -değer
    olmazsa hata
        yaz hata
    ver 0

yaz boz("metin")
'''
    )

    assert report.equivalent
    assert "Şahin çalışma hatası (satır 3, sütun 13)" in report.reference_output[0]
    assert "'-' işlemi uygulanamadı" in report.reference_output[0]
    assert report.reference_output[-1] == "0"
