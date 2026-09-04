from sahin.try_backend_equivalence import compare_try_source
from sahin.wasm_backend import build_wasm_plan_from_source
from sahin.native_backend import build_native_plan_from_source


def test_top_level_member_instruction_has_source_provenance_without_widening_capabilities():
    source = 'yaz "Şahin".uzunluk\n'
    wasm = build_wasm_plan_from_source(source)
    native = build_native_plan_from_source(source)

    wasm_members = [item for item in wasm.source_provenance if item.kind == "member"]
    native_members = [item for item in native.source_provenance if item.kind == "member"]

    assert len(wasm_members) == 1
    assert len(native_members) == 1
    assert wasm_members[0] == native_members[0]
    assert wasm_members[0].flow_name is None
    assert (wasm_members[0].line, wasm_members[0].column) == (1, 5)
    assert wasm.imports == ()
    assert native.capabilities == ()


def test_flow_try_member_error_payload_matches_reference_wasm_and_native():
    report = compare_try_source(
        '''akış oku değer
    dene
        yaz değer.bilinmeyen
    olmazsa hata
        yaz hata
    ver 0

yaz oku("Şahin")
'''
    )

    assert report.equivalent
    assert "Şahin çalışma hatası (satır 3, sütun 13)" in report.reference_output[0]
    assert "'bilinmeyen' üyesi bulunamadı." in report.reference_output[0]
    assert report.reference_output[-1] == "0"


def test_valid_member_inside_try_stays_equivalent():
    report = compare_try_source(
        '''dene
    yaz "Şahin".uzunluk
olmazsa hata
    yaz hata
'''
    )

    assert report.equivalent
    assert report.reference_output == ("5",)
