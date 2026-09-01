from __future__ import annotations

import pytest

from sahin.test_runner import discover_tests, run_tests


def test_discovery_is_deterministic_and_filters_non_tests() -> None:
    sources = {
        "tests/z_test.shn": "yaz 3\n",
        "tests/helper.shn": "yaz 2\n",
        "tests/test_a.shn": "yaz 1\n",
    }

    assert discover_tests(sources) == ("tests/test_a.shn", "tests/z_test.shn")


def test_runner_executes_all_tests_and_preserves_output() -> None:
    run = run_tests(
        {
            "tests/test_b.shn": "yaz 2\n",
            "tests/test_a.shn": "yaz 1\n",
        }
    )

    assert run.ok
    assert run.passed == 2
    assert run.failed == 0
    assert tuple(result.path for result in run.results) == (
        "tests/test_a.shn",
        "tests/test_b.shn",
    )
    assert run.results[0].output == ("1",)
    assert run.results[1].output == ("2",)


def test_runner_does_not_hide_semantic_or_parser_failures() -> None:
    run = run_tests(
        {
            "tests/test_good.shn": "deger = 1\nyaz deger\n",
            "tests/test_semantic.shn": "yaz eksik\n",
            "tests/test_parser.shn": "yaz\n",
        }
    )

    assert not run.ok
    assert run.passed == 1
    assert run.failed == 2
    by_path = {result.path: result for result in run.results}
    assert by_path["tests/test_good.shn"].passed
    assert "SHN-S301" in (by_path["tests/test_semantic.shn"].error or "")
    assert by_path["tests/test_parser.shn"].error


def test_discovery_rejects_path_traversal() -> None:
    with pytest.raises(ValueError):
        discover_tests({"../test_escape.shn": "yaz 1\n"})


def test_discovery_normalizes_windows_separators() -> None:
    assert discover_tests({"tests\\test_a.shn": "yaz 1\n"}) == ("tests/test_a.shn",)
