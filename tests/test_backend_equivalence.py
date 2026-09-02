from __future__ import annotations

from decimal import Decimal

import pytest

from sahin.backend_equivalence import compare_source


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


@pytest.mark.parametrize(
    ("source", "expected_state", "expected_output"),
    (
        (
            "sonuç = evet veya (1 / 0 == 1)\nyaz sonuç\n",
            (("sonuç", True),),
            ("evet",),
        ),
        (
            "sonuç = hayır ve (1 / 0 == 1)\nyaz sonuç\n",
            (("sonuç", False),),
            ("hayır",),
        ),
    ),
)
def test_control_flow_equivalence_preserves_lazy_short_circuit(source, expected_state, expected_output):
    report = compare_source(source)

    assert report.equivalent
    assert report.reference.state == expected_state
    assert report.reference.output == expected_output
    assert report.wasm == report.reference
    assert report.native == report.reference


def test_control_flow_equivalence_hides_internal_join_state_and_preserves_user_name():
    source = (
        "__shn_logic_0_end_result = hayır\n"
        "sonuç = evet veya hayır\n"
        "yaz __shn_logic_0_end_result\n"
        "yaz sonuç\n"
    )
    report = compare_source(source)

    assert report.equivalent
    assert report.reference.state == (
        ("__shn_logic_0_end_result", False),
        ("sonuç", True),
    )
    assert report.reference.output == ("hayır", "evet")
    assert report.wasm == report.reference
    assert report.native == report.reference


def test_reference_runtime_error_is_not_hidden():
    with pytest.raises(Exception):
        compare_source("sonuç = 1 / 0\n")
