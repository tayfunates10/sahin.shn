from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import platform
import statistics
import time
from collections.abc import Callable, Iterable

from .backend_equivalence import BackendObservation, _execute, compare_source
from .ir import lower_source
from .native_backend import build_native_plan
from .wasm_backend import build_wasm_plan


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

    @property
    def workload_sha256(self) -> str:
        return hashlib.sha256(self.source.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    name: str
    workload_sha256: str
    backend: str
    operation: str
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
                    "workload_sha256": result.workload_sha256,
                    "backend": result.backend,
                    "operation": result.operation,
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


def _measure(
    operation: Callable[[], BackendObservation],
    validate: Callable[[BackendObservation], None],
    config: BenchmarkConfig,
) -> tuple[int, ...]:
    for _ in range(config.warmups):
        observation = operation()
        validate(observation)

    samples: list[int] = []
    for _ in range(config.iterations):
        started = time.perf_counter_ns()
        observation = operation()
        elapsed = time.perf_counter_ns() - started
        if elapsed < 0:
            raise BackendBenchmarkError("monotonic benchmark saati negatif süre üretti")
        # Doğruluk karşılaştırması zaman penceresinin dışında tutulur. Böylece
        # oracle maliyeti backend süresine karışmaz, ancak her örnek doğrulanır.
        validate(observation)
        samples.append(elapsed)
    return tuple(samples)


def _result(
    case: BenchmarkCase,
    backend: str,
    samples: tuple[int, ...],
    config: BenchmarkConfig,
) -> BenchmarkResult:
    return BenchmarkResult(
        name=case.name,
        workload_sha256=case.workload_sha256,
        backend=backend,
        operation="adapter-plan+execute",
        iterations=config.iterations,
        median_ns=int(statistics.median(samples)),
        min_ns=min(samples),
        max_ns=max(samples),
        samples_ns=samples,
    )


def benchmark_case(
    case: BenchmarkCase,
    config: BenchmarkConfig | None = None,
) -> tuple[BenchmarkResult, BenchmarkResult]:
    active_config = config or BenchmarkConfig()

    # Referans ve lowering hazırlığı ölçüm penceresinin dışındadır. Equivalence
    # oracle yine zorunludur ve eşdeğer olmayan kaynak fail-closed reddedilir.
    equivalence = compare_source(case.source)
    if not equivalence.equivalent:
        raise BackendBenchmarkError(f"Semantik eşdeğerlik bozuldu: {case.name}")
    expected = equivalence.reference
    program = lower_source(case.source)

    def validate(observation: BackendObservation) -> None:
        if observation != expected:
            raise BackendBenchmarkError(f"Semantik eşdeğerlik bozuldu: {case.name}")

    def wasm_operation() -> BackendObservation:
        plan = build_wasm_plan(program)
        return _execute(plan.instructions)

    def native_operation() -> BackendObservation:
        plan = build_native_plan(program)
        return _execute(plan.instructions)

    wasm_samples = _measure(wasm_operation, validate, active_config)
    native_samples = _measure(native_operation, validate, active_config)
    return (
        _result(case, "wasm", wasm_samples, active_config),
        _result(case, "native", native_samples, active_config),
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

    results: list[BenchmarkResult] = []
    for case in frozen_cases:
        results.extend(benchmark_case(case, active_config))

    return BenchmarkReport(
        schema_version=2,
        python=platform.python_version(),
        implementation=platform.python_implementation(),
        machine=platform.machine() or "unknown",
        config=active_config,
        results=tuple(results),
    )
