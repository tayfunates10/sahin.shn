from __future__ import annotations

import json

import pytest

from sahin.backend_benchmark import (
    BackendBenchmarkError,
    BenchmarkCase,
    BenchmarkConfig,
    DEFAULT_CASES,
    run_baseline,
)


def test_baseline_runs_fixed_corpus_without_skipping_equivalence():
    report = run_baseline(config=BenchmarkConfig(warmups=0, iterations=2))

    assert report.schema_version == 2
    assert [result.name for result in report.results] == [
        name
        for case in DEFAULT_CASES
        for name in (case.name, case.name)
    ]
    assert [result.backend for result in report.results] == [
        backend
        for _case in DEFAULT_CASES
        for backend in ("wasm", "native")
    ]
    for result in report.results:
        assert result.operation == "adapter-plan+execute"
        assert len(result.workload_sha256) == 64
        assert result.iterations == 2
        assert len(result.samples_ns) == 2
        assert result.min_ns <= result.median_ns <= result.max_ns
        assert all(sample >= 0 for sample in result.samples_ns)


def test_baseline_json_is_canonical_and_contains_environment_metadata():
    case = BenchmarkCase("tek", "x = 2\nyaz x\n")
    report = run_baseline(
        cases=(case,),
        config=BenchmarkConfig(warmups=0, iterations=1),
    )

    encoded = report.to_json()
    decoded = json.loads(encoded)

    assert encoded == report.to_json()
    assert decoded["schema_version"] == 2
    assert decoded["config"] == {"iterations": 1, "warmups": 0}
    assert [result["backend"] for result in decoded["results"]] == ["wasm", "native"]
    for result in decoded["results"]:
        assert result["name"] == "tek"
        assert result["workload_sha256"] == case.workload_sha256
        assert result["operation"] == "adapter-plan+execute"
    assert decoded["environment"]["python"]
    assert decoded["environment"]["implementation"]
    assert decoded["environment"]["machine"]


def test_workload_digest_changes_when_source_changes():
    first = BenchmarkCase("aynı-ad", "x = 1\nyaz x\n")
    second = BenchmarkCase("aynı-ad", "x = 2\nyaz x\n")

    assert first.workload_sha256 != second.workload_sha256


@pytest.mark.parametrize(
    "config",
    (
        pytest.param(BenchmarkConfig(warmups=0, iterations=1), id="minimum"),
        pytest.param(BenchmarkConfig(warmups=100, iterations=1_000), id="maximum"),
    ),
)
def test_benchmark_config_accepts_documented_limits(config):
    assert config.iterations >= 1


@pytest.mark.parametrize(
    ("kwargs", "message"),
    (
        ({"warmups": -1}, "warmups"),
        ({"warmups": 101}, "warmups"),
        ({"iterations": 0}, "iterations"),
        ({"iterations": 1001}, "iterations"),
    ),
)
def test_benchmark_config_rejects_unbounded_or_empty_runs(kwargs, message):
    with pytest.raises(BackendBenchmarkError, match=message):
        BenchmarkConfig(**kwargs)


def test_baseline_rejects_empty_corpus():
    with pytest.raises(BackendBenchmarkError, match="boş olamaz"):
        run_baseline(cases=(), config=BenchmarkConfig(warmups=0, iterations=1))


def test_baseline_rejects_duplicate_case_names():
    cases = (
        BenchmarkCase("aynı", "x = 1\n"),
        BenchmarkCase("aynı", "x = 2\n"),
    )

    with pytest.raises(BackendBenchmarkError, match="benzersiz"):
        run_baseline(cases=cases, config=BenchmarkConfig(warmups=0, iterations=1))


def test_benchmark_preserves_fail_closed_ir_boundary():
    bad = BenchmarkCase("short-circuit", "sonuç = evet veya (1 / 0 == 1)\n")

    with pytest.raises(Exception):
        run_baseline(cases=(bad,), config=BenchmarkConfig(warmups=0, iterations=1))
