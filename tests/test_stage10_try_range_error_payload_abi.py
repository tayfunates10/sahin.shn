from sahin.native_backend import build_native_plan_from_source
from sahin.try_backend_equivalence import compare_try_source
from sahin.wasm_backend import build_wasm_plan_from_source


def test_top_level_range_instruction_has_source_provenance_without_widening_capabilities():
    source = "yaz 1 .. 3\n"
    wasm = build_wasm_plan_from_source(source)
    native = build_native_plan_from_source(source)

    wasm_ranges = [item for item in wasm.source_provenance if item.kind == "range"]
    native_ranges = [item for item in native.source_provenance if item.kind == "range"]

    assert len(wasm_ranges) == 1
    assert len(native_ranges) == 1
    assert wasm_ranges[0] == native_ranges[0]
    assert wasm_ranges[0].flow_name is None
    assert wasm.imports == ()
    assert native.capabilities == ()


def test_flow_try_range_error_payload_matches_reference_wasm_and_native():
    report = compare_try_source(
        '''akış aralık başlangıç, bitiş
    dene
        yaz başlangıç .. bitiş
    olmazsa hata
        yaz hata
    ver 0

yaz aralık("bir", 3)
'''
    )

    assert report.equivalent
    assert "Şahin çalışma hatası" in report.reference_output[0]
    assert "'..' aralığının iki ucu tam sayı olmalı." in report.reference_output[0]
    assert report.reference_output[-1] == "0"


def test_valid_range_inside_try_stays_equivalent():
    report = compare_try_source(
        '''dene
    yaz 3 .. 1
olmazsa hata
    yaz hata
'''
    )

    assert report.equivalent
    assert report.reference_output == ("(3, 2, 1)",)
