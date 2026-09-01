from __future__ import annotations

from decimal import Decimal

import pytest

from sahin.backend_equivalence import BackendEquivalenceError, compare_source
from sahin.ir import IRLoweringError


@pytest.mark.parametrize(
    ("source", "expected_state", "expected_output"),
    (
        (
            'ad = "Şahin"\nsayı = 2 + 3 * 4\nyaz ad\nyaz sayı\n',
            (("ad", "Şahin"), ("sayı", 14)),
            ("Şahin", "14"),
        ),
        (
            'fiyat = 10,50₺\nindirim = 2,25₺\nsonuç = fiyat - indirim\nyaz sonuç\n',
            (("fiyat", Decimal("10.50")), ("indirim", Decimal("2.25")), ("sonuç", Decimal("8.25"))),
            ("8.25",),
        ),
        (
            'aktif = evet\nters = değil aktif\nbüyük = 7 >= 3\nyaz ters\nyaz büyük\n',
            (("aktif", True), ("büyük", True), ("ters", False)),
            ("hayır", "evet"),
        ),
        (
            'sabit <- 4\nsonuç = +sabit * -2\nyaz sonuç\n',
            (("sabit", 4), ("sonuç", -8)),
            ("-8",),
        ),
    ),
)
def test_reference_wasm_and_native_plans_are_semantically_equivalent(source, expected_state, expected_output):
    report = compare_source(source)

    assert report.equivalent
    assert report.reference.state == expected_state
    assert report.reference.output == expected_output
    assert report.wasm == report.reference
    assert report.native == report.reference


def test_equivalence_is_deterministic_across_repeated_runs():
    source = 'x = 9\ny = x % 4\nyaz y\n'

    first = compare_source(source)
    second = compare_source(source)

    assert first == second
    assert first.equivalent


def test_equivalence_does_not_bypass_ir_fail_closed_boundary():
    with pytest.raises(IRLoweringError, match="kısa devreli 've/veya'"):
        compare_source("sonuç = evet veya (1 / 0 == 1)\n")


def test_reference_runtime_error_is_not_hidden():
    with pytest.raises(Exception):
        compare_source("sonuç = 1 / 0\n")
