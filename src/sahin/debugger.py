from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .ast_nodes import SourceLocation
from .runtime import Frame, Runtime


@dataclass(frozen=True, slots=True)
class DebugScope:
    frame_name: str
    values: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class DebugStop:
    reason: str
    location: SourceLocation | None
    statement_type: str
    scopes: tuple[DebugScope, ...]


class Debugger(Runtime):
    """Şahin runtime semantiğini değiştirmeden salt-okunur debugger gözlemi sağlar."""

    def __init__(
        self,
        output: Callable[[str], None] = print,
        *,
        on_stop: Callable[[DebugStop], None] | None = None,
    ) -> None:
        super().__init__(output)
        self._breakpoints: set[int] = set()
        self._step_enabled = False
        self._on_stop = on_stop or (lambda _: None)

    def add_breakpoint(self, line: int) -> None:
        if line <= 0:
            raise ValueError("Breakpoint satırı pozitif olmalı.")
        self._breakpoints.add(line)

    def remove_breakpoint(self, line: int) -> None:
        self._breakpoints.discard(line)

    def clear_breakpoints(self) -> None:
        self._breakpoints.clear()

    def enable_step(self) -> None:
        self._step_enabled = True

    def disable_step(self) -> None:
        self._step_enabled = False

    def inspect_scopes(self, frame: Frame) -> tuple[DebugScope, ...]:
        scopes: list[DebugScope] = []
        current: Frame | None = frame
        while current is not None:
            values = tuple(sorted((name, repr(value)) for name, value in current.values.items()))
            scopes.append(DebugScope(current.name, values))
            current = current.parent
        return tuple(scopes)

    def _execute_statement(self, statement, frame: Frame) -> None:
        location = getattr(statement, "location", None)
        breakpoint_hit = location is not None and location.line in self._breakpoints
        if self._step_enabled or breakpoint_hit:
            reason = "breakpoint" if breakpoint_hit else "step"
            self._on_stop(
                DebugStop(
                    reason=reason,
                    location=location,
                    statement_type=type(statement).__name__,
                    scopes=self.inspect_scopes(frame),
                )
            )
        super()._execute_statement(statement, frame)
