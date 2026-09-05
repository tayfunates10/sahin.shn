import pytest

from sahin.backend_equivalence import compare_source
from sahin.ir import IRLoweringError, lower_source


def test_name_increment_and_decrement_match_reference_wasm_and_native():
    source = "stok = 3\nstok artır 2\nstok azalt 1\nyaz stok\n"
    report = compare_source(source)

    assert report.equivalent
    assert report.reference.state == (("stok", 4),)
    assert report.reference.output == ("4",)
    assert report.wasm == report.reference
    assert report.native == report.reference


def test_name_mutation_default_amount_matches_reference_runtime():
    source = "stok = 3\nstok artır\nyaz stok\n"
    report = compare_source(source)

    assert report.equivalent
    assert report.reference.state == (("stok", 4),)
    assert report.reference.output == ("4",)


def test_name_mutation_does_not_mutate_binding():
    with pytest.raises(IRLoweringError, match=r"immutable bir değerdir"):
        lower_source("stok <- 3\nstok artır 1\n")


def test_name_mutation_rejects_undefined_target_before_backend():
    with pytest.raises(IRLoweringError, match=r"Semantik doğrulama başarısız"):
        lower_source("stok artır 1\n")
