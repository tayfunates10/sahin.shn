from __future__ import annotations

from dataclasses import dataclass

from .capabilities import Capability, CapabilitySet
from .lexer import tokenize
from .parser import parse
from .runtime import Runtime
from .semantics import SemanticAnalyzer


class ReplLimitError(RuntimeError):
    """REPL kaynak bütçesi aşıldığında fail-closed hata."""


class ReplSemanticError(RuntimeError):
    """Semantik olarak geçersiz bir snippet çalıştırılmak istendiğinde hata."""


@dataclass(frozen=True, slots=True)
class ReplLimits:
    max_snippet_chars: int = 16_384
    max_history_chars: int = 65_536
    max_snippets: int = 128

    def __post_init__(self) -> None:
        if self.max_snippet_chars <= 0 or self.max_history_chars <= 0 or self.max_snippets <= 0:
            raise ValueError("REPL limitleri pozitif olmalı.")
        if self.max_snippet_chars > self.max_history_chars:
            raise ValueError("Tek snippet limiti toplam geçmiş limitini aşamaz.")


@dataclass(frozen=True, slots=True)
class ReplResult:
    output: tuple[str, ...]
    values: dict[str, object]


class ReplSession:
    """Kontrollü, deterministik ve capability-default-deny Şahin REPL oturumu.

    Başarılı snippet'ler aynı Runtime global scope'unda devam eder. Semantik
    doğrulama, kabul edilmiş kaynak geçmişi + yeni snippet üzerinde yapılır;
    böylece önceki isimler yeniden çalıştırılmadan analizde görünür kalır.
    Dış dünya erişimi için hiçbir capability varsayılan olarak verilmez.
    """

    def __init__(
        self,
        *,
        capabilities: CapabilitySet | None = None,
        limits: ReplLimits | None = None,
    ) -> None:
        granted = set() if capabilities is None else set(capabilities.granted)
        self._capabilities = CapabilitySet(granted)
        self.limits = limits or ReplLimits()
        self._history: list[str] = []
        self._runtime = Runtime(self._capture_output)
        self._pending_output: list[str] = []

    @property
    def snippet_count(self) -> int:
        return len(self._history)

    @property
    def history_chars(self) -> int:
        return sum(len(source) for source in self._history)

    def allows(self, capability: Capability) -> bool:
        return self._capabilities.allows(capability)

    def require_capability(self, capability: Capability) -> None:
        self._capabilities.require(capability)

    def evaluate(self, source: str) -> ReplResult:
        self._check_limits(source)
        candidate = "\n".join((*self._history, source))
        semantic_program = parse(tokenize(candidate))
        model = SemanticAnalyzer().analyze(semantic_program)
        if not model.ok:
            rendered = "\n".join(diagnostic.format() for diagnostic in model.diagnostics)
            raise ReplSemanticError(rendered)

        program = parse(tokenize(source))
        self._pending_output = []
        try:
            values = self._runtime.execute(program)
        except Exception:
            self._pending_output = []
            raise

        output = tuple(self._pending_output)
        self._pending_output = []
        self._history.append(source)
        return ReplResult(output=output, values=values)

    def _check_limits(self, source: str) -> None:
        if len(self._history) >= self.limits.max_snippets:
            raise ReplLimitError("SHN-R001: REPL snippet bütçesi aşıldı.")
        if len(source) > self.limits.max_snippet_chars:
            raise ReplLimitError("SHN-R002: Tek REPL girdisi kaynak bütçesini aşıyor.")
        projected = self.history_chars + len(source)
        if projected > self.limits.max_history_chars:
            raise ReplLimitError("SHN-R003: REPL geçmiş kaynak bütçesi aşıldı.")

    def _capture_output(self, text: str) -> None:
        self._pending_output.append(text)
