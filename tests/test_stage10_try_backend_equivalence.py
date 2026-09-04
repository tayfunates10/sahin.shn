from sahin.try_backend_equivalence import compare_try_source

# Bu dosya top-level ve flow-local gözlemlenebilir try/error payload ABI regresyonlarını kilitler.


def test_try_success_path_matches_reference_runtime_on_wasm_and_native():
    report = compare_try_source(
        '''dene
    yaz "başarılı"
olmazsa hata
    yaz "yakalandı"
'''
    )

    assert report.reference_output == ("başarılı",)
    assert report.equivalent


def test_try_error_path_matches_reference_runtime_on_wasm_and_native():
    report = compare_try_source(
        '''dene
    yaz 1 / 0
olmazsa hata
    yaz "yakalandı"
'''
    )

    assert report.reference_output == ("yakalandı",)
    assert report.equivalent


def test_nested_try_uses_innermost_handler_first():
    report = compare_try_source(
        '''dene
    dene
        yaz 1 / 0
    olmazsa iç_hata
        yaz "iç"
olmazsa dış_hata
    yaz "dış"
'''
    )

    assert report.reference_output == ("iç",)
    assert report.equivalent


def test_observable_binary_error_payload_preserves_source_location_across_backends():
    report = compare_try_source(
        '''dene
    yaz 1 / 0
olmazsa hata
    yaz hata
'''
    )

    assert report.equivalent
    assert len(report.reference_output) == 1
    rendered = report.reference_output[0]
    assert "Şahin çalışma hatası" in rendered
    assert "satır 2" in rendered
    assert report.reference_output == report.wasm_output == report.native_output


def test_flow_local_try_observable_error_payload_preserves_flow_provenance_across_backends():
    report = compare_try_source(
        '''akış güvenli_böl
    dene
        yaz 1 / 0
    olmazsa hata
        yaz hata
    ver yok
sonuç = güvenli_böl()
'''
    )

    assert report.equivalent
    assert len(report.reference_output) == 1
    rendered = report.reference_output[0]
    assert "Şahin çalışma hatası" in rendered
    assert "satır 3" in rendered
    assert report.reference_output == report.wasm_output == report.native_output


def test_uncaught_flow_error_gains_callsite_frame_before_outer_try_catches_it():
    report = compare_try_source(
        '''akış riskli
    yaz 1 / 0
    ver yok
dene
    sonuç = riskli()
olmazsa hata
    yaz hata
'''
    )

    assert report.equivalent
    assert len(report.reference_output) == 1
    rendered = report.reference_output[0]
    assert "Şahin çalışma hatası" in rendered
    assert "satır 2" in rendered
    assert "Akış zinciri:" in rendered
    assert "riskli" in rendered
    assert "satır 5" in rendered
    assert report.reference_output == report.wasm_output == report.native_output


def test_nested_flow_error_preserves_each_callsite_frame_in_reference_order():
    report = compare_try_source(
        '''akış iç
    yaz 1 / 0
    ver yok
akış dış
    sonuç = iç()
    ver sonuç
dene
    sonuç = dış()
olmazsa hata
    yaz hata
'''
    )

    assert report.equivalent
    assert len(report.reference_output) == 1
    rendered = report.reference_output[0]
    assert "Akış zinciri:" in rendered
    assert "iç" in rendered
    assert "dış" in rendered
    assert "satır 5" in rendered
    assert "satır 8" in rendered
    assert report.reference_output == report.wasm_output == report.native_output
