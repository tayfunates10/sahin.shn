import pytest

from sahin.lexer import tokenize
from sahin.parser import parse
from sahin.runtime import Runtime, RuntimeErrorSHN
from sahin.try_backend_equivalence import compare_try_source


def test_reference_runtime_wraps_unary_type_error_with_source_location():
    source = 'yaz -"metin"\n'

    with pytest.raises(RuntimeErrorSHN) as caught:
        Runtime(lambda _: None).execute(parse(tokenize(source)))

    message = str(caught.value)
    assert "Şahin çalışma hatası (satır 1, sütun 5)" in message
    assert "'-' işlemi uygulanamadı" in message
    assert "bad operand type for unary -" in message


def test_top_level_try_unary_error_payload_matches_wasm_and_native():
    report = compare_try_source(
        '''dene
    yaz -"metin"
olmazsa hata
    yaz hata
'''
    )

    assert report.equivalent
    assert len(report.reference_output) == 1
    assert "Şahin çalışma hatası (satır 2, sütun 9)" in report.reference_output[0]
    assert "'-' işlemi uygulanamadı" in report.reference_output[0]


def test_flow_try_unary_error_payload_matches_wasm_and_native():
    report = compare_try_source(
        '''akış boz
    dene
        yaz +"metin"
    olmazsa hata
        yaz hata
    ver 0

yaz boz()
'''
    )

    assert report.equivalent
    assert "Şahin çalışma hatası (satır 3, sütun 13)" in report.reference_output[0]
    assert "'+' işlemi uygulanamadı" in report.reference_output[0]
    assert report.reference_output[-1] == "0"
