from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from decimal import Decimal

from .ast_nodes import (
    Assignment,
    Binary,
    Binding,
    Call,
    Command,
    Declaration,
    ExpressionStatement,
    ForEach,
    IfStatement,
    Literal,
    MatchStatement,
    Member,
    Name,
    Pipeline,
    Predicate,
    Program,
    RangeExpression,
    SourceLocation,
    TryStatement,
    Unary,
    Write,
)


@dataclass(frozen=True, slots=True)
class TraceFrame:
    name: str
    location: SourceLocation | None


class RuntimeErrorSHN(RuntimeError):
    def __init__(self, message: str, *, location: SourceLocation | None = None, frames: tuple[TraceFrame, ...] = ()) -> None:
        self.message = message
        self.location = location
        self.frames = frames
        super().__init__(self._render())

    def with_frame(self, name: str, location: SourceLocation | None) -> "RuntimeErrorSHN":
        return RuntimeErrorSHN(self.message, location=self.location, frames=(*self.frames, TraceFrame(name, location)))

    def _render(self) -> str:
        where = _format_location(self.location)
        lines = [f"Şahin çalışma hatası{where}: {self.message}"]
        if self.frames:
            lines.append("Akış zinciri:")
            for frame in reversed(self.frames):
                lines.append(f"  - {frame.name}{_format_location(frame.location)}")
        return "\n".join(lines)


class _ReturnSignal(Exception):
    def __init__(self, value: object) -> None:
        self.value = value


class _BreakSignal(Exception):
    pass


class Frame:
    def __init__(self, name: str, parent: "Frame | None" = None) -> None:
        self.name = name
        self.parent = parent
        self.values: dict[str, object] = {}
        self.bindings: set[str] = set()

    def define(self, name: str, value: object, *, bound: bool = False) -> None:
        self.values[name] = value
        if bound:
            self.bindings.add(name)

    def lookup(self, name: str) -> object:
        frame = self._find(name)
        if frame is None:
            raise KeyError(name)
        return frame.values[name]

    def assign(self, name: str, value: object) -> None:
        frame = self._find(name)
        if frame is not None:
            if name in frame.bindings:
                raise RuntimeErrorSHN(f"{name!r} '<-' ile bağlandığı için '=' ile yeniden atanamaz.")
            frame.values[name] = value
            return
        self.values[name] = value

    def _find(self, name: str) -> "Frame | None":
        current: Frame | None = self
        while current is not None:
            if name in current.values:
                return current
            current = current.parent
        return None

    def visible_names(self) -> tuple[str, ...]:
        result: list[str] = []
        current: Frame | None = self
        while current is not None:
            result.extend(name for name in current.values if name not in result)
            current = current.parent
        return tuple(result)


@dataclass(frozen=True, slots=True)
class FlowValue:
    declaration: Declaration
    closure: Frame


class Runtime:
    def __init__(self, output: Callable[[str], None] = print) -> None:
        self.output = output
        self.global_frame = Frame("<ana>")
        # Geriye dönük API: Aşama 1/2 testleri `values` alanını okuyabiliyor.
        self.values = self.global_frame.values

    def execute(self, program: Program) -> dict[str, object]:
        self._execute_block(program.statements, self.global_frame)
        return dict(self.global_frame.values)

    def _execute_block(self, statements, frame: Frame) -> None:
        # Akışlar lexical kapsamda, çağrıdan önce görünür olsun.
        for statement in statements:
            if isinstance(statement, Declaration) and statement.kind == "akış" and statement.name:
                frame.define(statement.name, FlowValue(statement, frame))

        for statement in statements:
            self._execute_statement(statement, frame)

    def _execute_statement(self, statement, frame: Frame) -> None:
        try:
            if isinstance(statement, Declaration):
                # `akış` yukarıda kaydedilir. Diğer declaration türleri ileriki
                # motorların (UI/veri/sunucu) yapısal girdileridir.
                return

            if isinstance(statement, Binding):
                if statement.name in frame.values:
                    raise self._error(f"{statement.name!r} aynı kapsamda zaten tanımlı.", statement.location)
                frame.define(statement.name, self._evaluate(statement.source, frame), bound=True)
                return

            if isinstance(statement, Assignment):
                try:
                    frame.assign(statement.name, self._evaluate(statement.expression, frame))
                except RuntimeErrorSHN as exc:
                    if exc.location is None:
                        raise self._error(exc.message, statement.location) from exc
                    raise
                return

            if isinstance(statement, Write):
                self.output(self._format(self._evaluate(statement.expression, frame)))
                return

            if isinstance(statement, ExpressionStatement):
                self._evaluate(statement.expression, frame)
                return

            if isinstance(statement, IfStatement):
                chosen = statement.body if self._truthy(self._evaluate(statement.condition, frame)) else statement.else_body
                self._execute_block(chosen, Frame("koşul", frame))
                return

            if isinstance(statement, ForEach):
                iterable = self._evaluate(statement.iterable, frame)
                if isinstance(iterable, (str, bytes)) or not isinstance(iterable, Iterable):
                    raise self._error("'her' ifadesinin kaynağı yinelenebilir bir değer olmalı.", statement.location)
                for item in iterable:
                    loop_frame = Frame(f"her {statement.name}", frame)
                    loop_frame.define(statement.name, item)
                    try:
                        self._execute_block(statement.body, loop_frame)
                    except _BreakSignal:
                        break
                return

            if isinstance(statement, MatchStatement):
                subject = self._evaluate(statement.subject, frame)
                for case in statement.cases:
                    if subject == self._evaluate(case.pattern, frame):
                        self._execute_statement(case.statement, Frame("duruma göre", frame))
                        break
                return

            if isinstance(statement, TryStatement):
                try:
                    self._execute_block(statement.body, Frame("dene", frame))
                except RuntimeErrorSHN as exc:
                    rescue = Frame("olmazsa", frame)
                    if statement.error_name:
                        rescue.define(statement.error_name, exc)
                    self._execute_block(statement.except_body, rescue)
                return

            if isinstance(statement, Command):
                self._execute_command(statement, frame)
                return

            raise self._error(f"Desteklenmeyen AST düğümü: {type(statement).__name__}", getattr(statement, "location", None))
        except RuntimeErrorSHN:
            raise

    def _execute_command(self, command: Command, frame: Frame) -> None:
        if command.name == "ver":
            value = self._evaluate(command.arguments[0], frame) if command.arguments else None
            raise _ReturnSignal(value)
        if command.name == "bitir":
            raise _BreakSignal()
        if command.name in {"bildir", "yaz"}:
            value = self._evaluate(command.arguments[0], frame) if command.arguments else None
            self.output(self._format(value))
            return

        if command.subject is not None and command.name in {"azalt", "artır"}:
            subject = self._evaluate(command.subject, frame)
            amount = self._evaluate(command.arguments[0], frame) if command.arguments else 1
            delta = -amount if command.name == "azalt" else amount
            if isinstance(command.subject, Name):
                frame.assign(command.subject.value, subject + delta)
                return
            if isinstance(command.subject, Member):
                self._set_member(command.subject, subject + delta, frame)
                return

        # Gövdeli genel eylemler deterministik lexical blok olarak yürür.
        if command.body:
            self._execute_block(command.body, Frame(command.name, frame))
            return
        raise self._error(f"{command.name!r} eylemi çalışma motorunda tanımlı değil.", command.location)

    def _evaluate(self, expression, frame: Frame) -> object:
        if isinstance(expression, Literal):
            return expression.value
        if isinstance(expression, Name):
            try:
                return frame.lookup(expression.value)
            except KeyError:
                suggestion = self._nearest_name(expression.value, frame)
                suffix = f" Şunu mu demek istediniz: {suggestion}?" if suggestion else ""
                raise self._error(f"{expression.value!r} adında bir değer bulunamadı.{suffix}", expression.location) from None
        if isinstance(expression, Unary):
            value = self._evaluate(expression.operand, frame)
            if expression.operator in {"değil", "!"}:
                return not self._truthy(value)
            if expression.operator == "-":
                return -value
            if expression.operator == "+":
                return +value
            raise self._error(f"Bilinmeyen tekli işlem: {expression.operator}", expression.location)
        if isinstance(expression, Binary):
            if expression.operator == "ve":
                left = self._evaluate(expression.left, frame)
                return self._evaluate(expression.right, frame) if self._truthy(left) else left
            if expression.operator == "veya":
                left = self._evaluate(expression.left, frame)
                return left if self._truthy(left) else self._evaluate(expression.right, frame)
            left = self._evaluate(expression.left, frame)
            right = self._evaluate(expression.right, frame)
            operations = {
                "+": lambda: left + right,
                "-": lambda: left - right,
                "*": lambda: left * right,
                "/": lambda: left / right,
                "%": lambda: left % right,
                "==": lambda: left == right,
                "!=": lambda: left != right,
                "<": lambda: left < right,
                "<=": lambda: left <= right,
                ">": lambda: left > right,
                ">=": lambda: left >= right,
            }
            operation = operations.get(expression.operator)
            if operation is None:
                raise self._error(f"Bilinmeyen ikili işlem: {expression.operator}", expression.location)
            try:
                return operation()
            except (ArithmeticError, TypeError) as exc:
                raise self._error(f"{expression.operator!r} işlemi uygulanamadı: {exc}", expression.location) from exc
        if isinstance(expression, Predicate):
            value = self._evaluate(expression.expression, frame)
            if expression.predicate == "yok":
                return value is None
            if expression.predicate == "boş":
                return value is None or value == "" or value == [] or value == {} or value == ()
            if expression.predicate == "boş_değil":
                return not (value is None or value == "" or value == [] or value == {} or value == ())
            raise self._error(f"Bilinmeyen yüklem: {expression.predicate}", expression.location)
        if isinstance(expression, Member):
            target = self._evaluate(expression.target, frame)
            return self._get_member(target, expression.name, expression.location)
        if isinstance(expression, Call):
            callee = self._evaluate(expression.callee, frame)
            arguments = tuple(self._evaluate(arg, frame) for arg in expression.arguments)
            if not isinstance(callee, FlowValue):
                raise self._error("Yalnızca Şahin 'akış' değerleri doğrudan çağrılabilir.", expression.location)
            return self._call_flow(callee, arguments, expression.location)
        if isinstance(expression, RangeExpression):
            start = self._evaluate(expression.start, frame)
            end = self._evaluate(expression.end, frame)
            if not isinstance(start, int) or isinstance(start, bool) or not isinstance(end, int) or isinstance(end, bool):
                raise self._error("'..' aralığının iki ucu tam sayı olmalı.", expression.location)
            step = 1 if end >= start else -1
            return tuple(range(start, end + step, step))
        if isinstance(expression, Pipeline):
            value = self._evaluate(expression.source, frame)
            for stage in expression.stages:
                value = self._pipeline_stage(value, stage.name, stage.arguments, frame, stage.location)
            return value
        raise self._error(f"Desteklenmeyen ifade: {type(expression).__name__}", getattr(expression, "location", None))

    def _call_flow(self, flow: FlowValue, arguments: tuple[object, ...], call_location: SourceLocation | None) -> object:
        declaration = flow.declaration
        if len(arguments) != len(declaration.parameters):
            raise self._error(
                f"{declaration.name!r} akışı {len(declaration.parameters)} argüman bekliyor, {len(arguments)} verildi.",
                call_location,
            )
        local = Frame(declaration.name or "<akış>", flow.closure)
        for parameter, value in zip(declaration.parameters, arguments, strict=True):
            local.define(parameter.name, value)
        try:
            if declaration.inline_expression is not None:
                return self._evaluate(declaration.inline_expression, local)
            self._execute_block(declaration.body, local)
            return None
        except _ReturnSignal as signal:
            return signal.value
        except _BreakSignal as exc:
            raise self._error("'bitir' yalnızca yineleme içinde kullanılabilir.", declaration.location) from exc
        except RuntimeErrorSHN as exc:
            raise exc.with_frame(declaration.name or "<akış>", call_location) from exc

    def _pipeline_stage(self, value: object, name: str, arguments, frame: Frame, location: SourceLocation | None) -> object:
        if name == "ilk":
            count = self._evaluate(arguments[0], frame) if arguments else 1
            if not isinstance(count, int) or count < 0:
                raise self._error("'ilk' aşamasının miktarı sıfır veya pozitif tam sayı olmalı.", location)
            return tuple(value)[:count]
        if name == "sırala":
            key = self._evaluate(arguments[0], frame) if arguments else None
            items = tuple(value)
            if key is None:
                return tuple(sorted(items))
            if isinstance(key, str):
                return tuple(sorted(items, key=lambda item: self._get_member(item, key, location)))
            raise self._error("'sırala' anahtarı yazı olmalı.", location)
        if name == "seç":
            selector = self._evaluate(arguments[0], frame) if arguments else True
            items = tuple(value)
            if isinstance(selector, bool):
                return items if selector else ()
            if isinstance(selector, str):
                return tuple(item for item in items if self._truthy(self._get_member(item, selector, location)))
            raise self._error("'seç' aşaması evet/hayır veya alan adı bekliyor.", location)
        raise self._error(f"Bilinmeyen pipeline aşaması: {name!r}", location)

    def _get_member(self, target: object, name: str, location: SourceLocation | None) -> object:
        if isinstance(target, dict):
            if name in target:
                return target[name]
        if name == "uzunluk" and isinstance(target, (str, tuple, list, dict)):
            return len(target)
        raise self._error(f"{name!r} üyesi bulunamadı.", location)

    def _set_member(self, member: Member, value: object, frame: Frame) -> None:
        target = self._evaluate(member.target, frame)
        if isinstance(target, dict):
            target[member.name] = value
            return
        raise self._error(f"{member.name!r} üyesi değiştirilebilir değil.", member.location)

    def _nearest_name(self, target: str, frame: Frame) -> str | None:
        names = frame.visible_names()
        if not names:
            return None
        best = min(names, key=lambda name: _distance(target, name))
        return best if _distance(target, best) <= max(2, len(target) // 3) else None

    @staticmethod
    def _truthy(value: object) -> bool:
        return bool(value)

    @staticmethod
    def _format(value: object) -> str:
        if value is True:
            return "evet"
        if value is False:
            return "hayır"
        if value is None:
            return "yok"
        if isinstance(value, Decimal):
            return format(value, "f")
        return str(value)

    @staticmethod
    def _error(message: str, location: SourceLocation | None) -> RuntimeErrorSHN:
        return RuntimeErrorSHN(message, location=location)


def _format_location(location: SourceLocation | None) -> str:
    if location is None:
        return ""
    return f" (satır {location.line}, sütun {location.column})"


def _distance(a: str, b: str) -> int:
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current = [i]
        for j, cb in enumerate(b, start=1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (ca != cb)))
        previous = current
    return previous[-1]
