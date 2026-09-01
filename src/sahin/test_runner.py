from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from collections.abc import Mapping
import unicodedata

from .lexer import Lexer
from .parser import Parser
from .runtime import Runtime
from .semantics import SemanticAnalyzer


@dataclass(frozen=True, slots=True)
class TestResult:
    path: str
    passed: bool
    output: tuple[str, ...] = ()
    error: str | None = None


@dataclass(frozen=True, slots=True)
class TestRun:
    results: tuple[TestResult, ...]

    @property
    def passed(self) -> int:
        return sum(result.passed for result in self.results)

    @property
    def failed(self) -> int:
        return len(self.results) - self.passed

    @property
    def ok(self) -> bool:
        return self.failed == 0


def _canonical_path(path: str) -> str:
    normalized = unicodedata.normalize("NFC", path.replace("\\", "/"))
    pure = PurePosixPath(normalized)
    if pure.is_absolute() or ".." in pure.parts or not pure.parts:
        raise ValueError(f"Güvensiz test yolu: {path!r}")
    return pure.as_posix()


def discover_tests(sources: Mapping[str, str]) -> tuple[str, ...]:
    """Şahin test kaynaklarını host-independent ve deterministik keşfeder."""

    discovered: dict[str, str] = {}
    for raw_path in sources:
        path = _canonical_path(raw_path)
        name = PurePosixPath(path).name
        if not (name.startswith("test_") or name.endswith("_test.shn")):
            continue
        if not name.endswith(".shn"):
            continue
        if path in discovered:
            raise ValueError(f"Aynı kanonik test yolu birden fazla kez verildi: {path}")
        discovered[path] = raw_path

    return tuple(sorted(discovered, key=lambda item: item.encode("utf-8")))


def run_tests(sources: Mapping[str, str]) -> TestRun:
    """Keşfedilen tüm testleri çalıştırır; hata alan testleri gizlemez.

    Her `.shn` test dosyası lexer → parser → semantic analyzer → runtime zincirinin
    tamamından geçer. Bir testin lexical, parser, semantic veya runtime hatası o
    test için açık başarısızlık sonucudur; kalan testler yine çalıştırılır.
    """

    canonical_sources = {_canonical_path(path): source for path, source in sources.items()}
    results: list[TestResult] = []

    for path in discover_tests(canonical_sources):
        output: list[str] = []
        try:
            tokens = Lexer(canonical_sources[path]).tokenize()
            program = Parser(tokens).parse()
            model = SemanticAnalyzer().analyze(program)
            if model.diagnostics:
                rendered = "; ".join(
                    f"{diagnostic.code}: {diagnostic.message}" for diagnostic in model.diagnostics
                )
                results.append(TestResult(path=path, passed=False, error=rendered))
                continue
            Runtime(output=output.append).execute(program)
        except Exception as exc:  # Test sonucu olarak yakala; diğer testleri saklama.
            results.append(TestResult(path=path, passed=False, output=tuple(output), error=str(exc)))
        else:
            results.append(TestResult(path=path, passed=True, output=tuple(output)))

    return TestRun(tuple(results))
