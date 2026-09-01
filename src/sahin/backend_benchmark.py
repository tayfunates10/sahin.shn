from __future__ import annotations

from dataclasses import dataclass
import json
import platform
import statistics
import time
from collections.abc import Callable, Iterable

from .backend_equivalence import compare_source


class BackendBenchmarkError(ValueError):
    """Benchmark yapılandırması veya kaynak kümesi güvenli değilse oluşur."""


@dataclass(frozen=True, slots=True)
class BenchmarkConfig:
    warmups: int = 3
    iterations: int = 15

    def __post_init__(self) -> None:
        if not 0 <= self.warmups <= 100:
            raise BackendBenchmarkError("warmups 0..100 aralığında olmalıdır")
        if not 1 <= self.iterations <= 1_000:
            raise BackendBenchmarkError("iterations 1..1000 aralığında olmalıdır")


@dataclass(frozen=True, slots=True)
class BenchmarkCase:
    name: str
    source: str

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise BackendBenchmarkError("benchmark adı boş olamaz")
        if not self.source or not self.source.strip():
            raise BackendBenchmarkError("benchmark kaynağı boş olamaz")


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    name: str
    iterations: int
    median_ns: int
    min_ns: int
    max_ns: int
    samples_ns: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class BenchmarkReport:
    schema_version: int
    python: str
    implementation: str
    machine: str
    config: BenchmarkConfig
    results: tuple[BenchmarkResult, ...]

    def to_json(self) -> str:
        payload = {
            "schema_version": self.schema_version,
            "environment": {
                "python": self.python,
                "implementation": self.implementation,
                "machine": self.machine,
            },
            "config": {
                "warmups": self.config.warmups,
                "iterations": self.config.iterations,
            },
            "results": [
                {
                    "name": result.name,
                    "iterations": result.iterations,
                    "median_ns": result.median_ns,
                    "min_ns": result.min_ns,
                    "max_ns": result.max_ns,
                    "samples_ns": list(result.samples_ns),
                }
                for result in self.results
            ],
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


DEFAULT_CASES: tuple[BenchmarkCase, ...] = (
    BenchmarkCase(
        "arithmetic",
        "x = 9\ny = x % 4\nz = (x + y) * 3\nyaz z\n",
    ),
    BenchmarkCase(
        "decimal-money",
        "fiyat = 10,50₺\nindirim = 2,25₺\nsonuç = fiyat - indirim\nyaz sonuç\n",
    ),
    BenchmarkCase(
        "unicode-boolean",
        'ad = "Şahin"\naktif = evet\nters = değil aktif\nyaz ad\nyaz ters\n',
    ),
)


def _measure(operation: Callable[[], object], config: BenchmarkConfig) -> tuple[int, ...]:
    for _ in range(config.warmups):
        operation()

    samples: list[int] = []
    for _ in range(config.iterations):
        started = time.perf_counter_ns()
        operation()
        elapsed = time.perf_counter_ns() - started
        if elapsed < 0:
            raise BackendBenchmarkError("monotonic benchmark saati negatif süre üretti")
        samples.append(elapsed)
    return tuple(samples)


def benchmark_case(case: BenchmarkCase, config: BenchmarkConfig | None = None) -> BenchmarkResult:
    active_config = config or BenchmarkConfig()

    # Benchmark performans uğruna doğruluğu atlayamaz: her ölçüm tam equivalence
    # zincirini çalıştırır ve eşdeğer olmayan sonuçta fail-closed davranır.
    def operation() -> object:
        report = compare_source(case.source)
        if not report.equivalent:
            raise BackendBenchmarkError(f"Semantik eşdeğerlik bozuldu: {case.name}")
        return report

    samples = _measure(operation, active_config)
    return BenchmarkResult(
        name=case.name,
        iterations=active_config.iterations,
        median_ns=int(statistics.median(samples)),
        min_ns=min(samples),
        max_ns=max(samples),
        samples_ns=samples,
    )


def run_baseline(
    cases: Iterable[BenchmarkCase] = DEFAULT_CASES,
    config: BenchmarkConfig | None = None,
) -> BenchmarkReport:
    active_config = config or BenchmarkConfig()
    frozen_cases = tuple(cases)
    if not frozen_cases:
        raise BackendBenchmarkError("benchmark corpus'u boş olamaz")

    names = [case.name for case in frozen_cases]
    if len(names) != len(set(names)):
        raise BackendBenchmarkError("benchmark adları benzersiz olmalıdır")

    return BenchmarkReport(
        schema_version=1,
        python=platform.python_version(),
        implementation=platform.python_implementation(),
        machine=platform.machine() or "unknown",
        config=active_config,
        results=tuple(benchmark_case(case, active_config) for case in frozen_cases),
    )
