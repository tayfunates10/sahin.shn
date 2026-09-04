from sahin.native_backend import build_native_plan_from_source
from sahin.try_backend_equivalence import compare_try_source
from sahin.wasm_backend import build_wasm_plan_from_source


def test_top_level_pipeline_stage_has_source_provenance_without_widening_capabilities():
    source = "sonuç = 1..5 | ilk 2\n"
    wasm = build_wasm_plan_from_source(source)
    native = build_native_plan_from_source(source)

    wasm_pipeline = [item for item in wasm.source_provenance if item.kind == "pipeline"]
    native_pipeline = [item for item in native.source_provenance if item.kind == "pipeline"]

    assert len(wasm_pipeline) == 1
    assert len(native_pipeline) == 1
    assert wasm_pipeline[0] == native_pipeline[0]
    assert wasm_pipeline[0].flow_name is None
    assert wasm.imports == ()
    assert native.capabilities == ()


def test_flow_try_pipeline_ilk_error_payload_matches_reference_wasm_and_native():
    report = compare_try_source(
        '''akış kırp değer, miktar
    dene
        yaz değer | ilk miktar
    olmazsa hata
        yaz hata
    ver 0

yaz kırp(1..3, "bir")
'''
    )

    assert report.equivalent
    assert "Şahin çalışma hatası" in report.reference_output[0]
    assert "'ilk' aşamasının miktarı sıfır veya pozitif tam sayı olmalı." in report.reference_output[0]
    assert report.reference_output[-1] == "0"


def test_flow_try_pipeline_selector_errors_match_reference_wasm_and_native():
    for stage in ("sırala", "seç"):
        report = compare_try_source(
            f'''akış uygula değer, seçim
    dene
        yaz değer | {stage} seçim
    olmazsa hata
        yaz hata
    ver 0

yaz uygula(1..3, 9)
'''
        )
        assert report.equivalent
        assert "Şahin çalışma hatası" in report.reference_output[0]
        assert report.reference_output[-1] == "0"


def test_valid_pipeline_inside_try_stays_equivalent():
    report = compare_try_source(
        '''dene
    yaz 1..3 | ilk 2
olmazsa hata
    yaz hata
'''
    )

    assert report.equivalent
    assert report.reference_output == ("(1, 2)",)
