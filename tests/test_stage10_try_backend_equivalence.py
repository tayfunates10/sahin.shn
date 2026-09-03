from sahin.try_backend_equivalence import compare_try_source


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
