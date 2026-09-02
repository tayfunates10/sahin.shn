from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import json

from .ast_nodes import (
    Assignment,
    Binary,
    Binding,
    Expression,
    ExpressionStatement,
    IfStatement,
    Literal,
    Name,
    Predicate,
    Program,
    Unary,
    Write,
)
from .lexer import tokenize
from .parser import parse
from .semantics import SemanticAnalyzer


class IRLoweringError(ValueError):
    """Şahin AST/semantic modelinden IR üretimi güvenle tamamlanamadığında oluşur."""


@dataclass(frozen=True, slots=True)
class IRInstruction:
    opcode: str
    operands: tuple[str, ...] = ()
    result: str | None = None

    def canonical(self) -> str:
        payload = {
            "op": self.opcode,
            "args": list(self.operands),
            "result": self.result,
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class IRProgram:
    version: int
    instructions: tuple[IRInstruction, ...]

    def canonical(self) -> str:
        payload = {
            "instructions": [json.loads(item.canonical()) for item in self.instructions],
            "version": self.version,
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class _Lowerer:
    def __init__(self) -> None:
        self.instructions: list[IRInstruction] = []
        self._next_temp = 0
        self._next_label = 0
        self._next_scope = 0
        self._scopes: list[tuple[int | None, dict[str, str]]] = [(None, {})]

    def lower(self, program: Program) -> IRProgram:
        for statement in program.statements:
            self._statement(statement)
        return IRProgram(version=1, instructions=tuple(self.instructions))

    def _temp(self) -> str:
        name = f"%{self._next_temp}"
        self._next_temp += 1
        return name

    def _labels(self, stem: str, *roles: str) -> tuple[str, ...]:
        sequence = self._next_label
        self._next_label += 1
        return tuple(f"__shn_{stem}_{sequence}_{role}" for role in roles)

    def _push_scope(self) -> None:
        scope_id = self._next_scope
        self._next_scope += 1
        self._scopes.append((scope_id, {}))

    def _pop_scope(self) -> None:
        if len(self._scopes) == 1:
            raise IRLoweringError("IR lexical scope yığını global kapsamın altına inemez.")
        self._scopes.pop()

    def _declare_name(self, name: str) -> str:
        scope_id, names = self._scopes[-1]
        if name in names:
            return names[name]
        physical = name if scope_id is None else f"__shn_scope_{scope_id}_{name}"
        names[name] = physical
        return physical

    def _resolve_name(self, name: str) -> str | None:
        for _, names in reversed(self._scopes):
            if name in names:
                return names[name]
        return None

    def _emit(self, opcode: str, operands: tuple[str, ...] = (), result: str | None = None) -> None:
        self.instructions.append(IRInstruction(opcode, operands, result))

    def _statement(self, statement) -> None:
        if isinstance(statement, Assignment):
            value = self._expression(statement.expression)
            target = self._resolve_name(statement.name)
            if target is None:
                target = self._declare_name(statement.name)
            self._emit("store", (target, value))
            return
        if isinstance(statement, Binding):
            value = self._expression(statement.source)
            target = self._declare_name(statement.name)
            self._emit("bind", (target, value))
            return
        if isinstance(statement, Write):
            value = self._expression(statement.expression)
            self._emit("write", (value,))
            return
        if isinstance(statement, IfStatement):
            condition = self._expression(statement.condition)
            true_label, false_label, end_label = self._labels("if", "true", "false", "end")
            self._emit("branch", (condition, true_label, false_label))

            self._emit("label", (true_label,))
            self._push_scope()
            try:
                for child in statement.body:
                    self._statement(child)
            finally:
                self._pop_scope()
            self._emit("jump", (end_label,))

            self._emit("label", (false_label,))
            self._push_scope()
            try:
                for child in statement.else_body:
                    self._statement(child)
            finally:
                self._pop_scope()
            self._emit("jump", (end_label,))

            self._emit("label", (end_label,))
            return
        if isinstance(statement, ExpressionStatement):
            raise IRLoweringError(
                "Aşama 10 IR v1 ExpressionStatement düğümünü semantik analiz açıkça doğrulayana kadar desteklemiyor."
            )
        raise IRLoweringError(
            f"Aşama 10 IR v1 henüz {type(statement).__name__} düğümünü desteklemiyor."
        )

    def _short_circuit(self, expression: Binary) -> str:
        left = self._expression(expression.left)
        rhs_label, short_label, end_label = self._labels("logic", "rhs", "short", "end")
        # '$' kaynak dilinde geçerli bir identifier başlangıcı değildir. Böylece join slotu
        # kullanıcı isim alanıyla çakışamaz; ilerideki equivalence yürütücüsü de bu alanı
        # açıkça internal state olarak ayırabilir.
        result_name = f"$internal_{end_label}_result"

        if expression.operator == "ve":
            self._emit("branch", (left, rhs_label, short_label))
            short_literal = False
        elif expression.operator == "veya":
            self._emit("branch", (left, short_label, rhs_label))
            short_literal = True
        else:
            raise IRLoweringError(f"Desteklenmeyen kısa devre operatörü: {expression.operator!r}")

        self._emit("label", (rhs_label,))
        right = self._expression(expression.right)
        self._emit("store", (result_name, right))
        self._emit("jump", (end_label,))

        self._emit("label", (short_label,))
        short_value = self._temp()
        self._emit("const", (self._literal(short_literal),), short_value)
        self._emit("store", (result_name, short_value))
        self._emit("jump", (end_label,))

        self._emit("label", (end_label,))
        result = self._temp()
        self._emit("load", (result_name,), result)
        return result

    def _expression(self, expression: Expression) -> str:
        if isinstance(expression, Literal):
            result = self._temp()
            self._emit("const", (self._literal(expression.value),), result)
            return result
        if isinstance(expression, Name):
            physical = self._resolve_name(expression.value)
            if physical is None:
                raise IRLoweringError(
                    f"Semantik doğrulama sonrası çözülemeyen isim: {expression.value!r}."
                )
            result = self._temp()
            self._emit("load", (physical,), result)
            return result
        if isinstance(expression, Unary):
            operand = self._expression(expression.operand)
            result = self._temp()
            self._emit("unary", (expression.operator, operand), result)
            return result
        if isinstance(expression, Binary):
            if expression.operator in {"ve", "veya"}:
                return self._short_circuit(expression)
            left = self._expression(expression.left)
            right = self._expression(expression.right)
            result = self._temp()
            self._emit("binary", (expression.operator, left, right), result)
            return result
        if isinstance(expression, Predicate):
            operand = self._expression(expression.expression)
            if expression.predicate not in {"yok", "boş", "boş_değil"}:
                raise IRLoweringError(f"Bilinmeyen Şahin yüklemi IR'a indirgenemedi: {expression.predicate!r}")
            result = self._temp()
            self._emit("predicate", (expression.predicate, operand), result)
            return result
        raise IRLoweringError(
            f"Aşama 10 IR v1 henüz {type(expression).__name__} ifadesini desteklemiyor."
        )

    @staticmethod
    def _literal(value: str | int | Decimal | bool | None) -> str:
        if value is None:
            return "yok:null"
        if isinstance(value, bool):
            return "evet_hayır:evet" if value else "evet_hayır:hayır"
        if isinstance(value, Decimal):
            return f"ondalık:{format(value, 'f')}"
        if isinstance(value, int):
            return f"tam:{value}"
        if isinstance(value, str):
            return "metin:" + json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        raise IRLoweringError(f"Desteklenmeyen sabit türü: {type(value).__name__}")


def lower_program(program: Program) -> IRProgram:
    """Semantik olarak doğrulanmış bir Program için deterministik Şahin IR v1 üretir."""
    model = SemanticAnalyzer().analyze(program)
    if not model.ok:
        details = "; ".join(item.format() for item in model.diagnostics)
        raise IRLoweringError(f"Semantik doğrulama başarısız: {details}")
    return _Lowerer().lower(program)


def lower_source(source: str) -> IRProgram:
    """Kaynağı gerçek Lexer → Parser → SemanticAnalyzer hattından geçirip IR'a indirger."""
    return lower_program(parse(tokenize(source)))
