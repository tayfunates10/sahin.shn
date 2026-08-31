from __future__ import annotations

from collections.abc import Callable

from .ast_nodes import Assignment, Literal, Name, Program, Write


class RuntimeErrorSHN(RuntimeError):
    pass


class Runtime:
    def __init__(self, output: Callable[[str], None] = print) -> None:
        self.values: dict[str, object] = {}
        self.output = output

    def execute(self, program: Program) -> dict[str, object]:
        for statement in program.statements:
            if isinstance(statement, Assignment):
                # v0.1 bootstrap'ta '<-' tek seferlik çözülür; reaktif bağlama
                # semantiği veri/ekran çalışma zamanı geldiğinde uygulanacaktır.
                self.values[statement.name] = self._evaluate(statement.expression)
                continue

            if isinstance(statement, Write):
                value = self._evaluate(statement.expression)
                self.output(self._format(value))
                continue

            raise RuntimeErrorSHN(f"Desteklenmeyen AST düğümü: {type(statement).__name__}")

        return dict(self.values)

    def _evaluate(self, expression):
        if isinstance(expression, Literal):
            return expression.value
        if isinstance(expression, Name):
            if expression.value not in self.values:
                suggestion = self._nearest_name(expression.value)
                suffix = f" Şunu mu demek istediniz: {suggestion}?" if suggestion else ""
                raise RuntimeErrorSHN(f"{expression.value!r} adında bir değer bulunamadı.{suffix}")
            return self.values[expression.value]
        raise RuntimeErrorSHN(f"Desteklenmeyen ifade: {type(expression).__name__}")

    def _nearest_name(self, target: str) -> str | None:
        if not self.values:
            return None
        best = min(self.values, key=lambda name: _distance(target, name))
        return best if _distance(target, best) <= max(2, len(target) // 3) else None

    @staticmethod
    def _format(value: object) -> str:
        if value is True:
            return "evet"
        if value is False:
            return "hayır"
        if value is None:
            return "yok"
        return str(value)


def _distance(a: str, b: str) -> int:
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current = [i]
        for j, cb in enumerate(b, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[j] + 1,
                    previous[j - 1] + (ca != cb),
                )
            )
        previous = current
    return previous[-1]
