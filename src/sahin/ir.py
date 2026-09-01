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
    Literal,
    Name,
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

    def lower(self, program: Program) -> IRProgram:
        for statement in program.statements:
            self._statement(statement)
        return IRProgram(version=1, instructions=tuple(self.instructions))

    def _temp(self) -> str:
        name = f"%{self._next_temp}"
        self._next_temp += 1
        return name

    def _emit(self, opcode: str, operands: tuple[str, ...] = (), result: str | None = None) -> None:
        self.instructions.append(IRInstruction(opcode, operands, result))

    def _statement(self, statement) -> None:
        if isinstance(statement, Assignment):
            value = self._expression(statement.expression)
            self._emit("store", (statement.name, value))
            return
        if isinstance(statement, Binding):
            value = self._expression(statement.source)
            self._emit("bind", (statement.name, value))
            return
        if isinstance(statement, Write):
            value = self._expression(statement.expression)
            self._emit("write", (value,))
            return
        if isinstance(statement, ExpressionStatement):
            raise IRLoweringError(
                "Aşama 10 IR v1 ExpressionStatement düğümünü semantik analiz açıkça doğrulayana kadar desteklemiyor."
            )
        raise IRLoweringError(
            f"Aşama 10 IR v1 henüz {type(statement).__name__} düğümünü desteklemiyor."
        )

    def _expression(self, expression: Expression) -> str:
        if isinstance(expression, Literal):
            result = self._temp()
            self._emit("const", (self._literal(expression.value),), result)
            return result
        if isinstance(expression, Name):
            result = self._temp()
            self._emit("load", (expression.value,), result)
            return result
        if isinstance(expression, Unary):
            operand = self._expression(expression.operand)
            result = self._temp()
            self._emit("unary", (expression.operator, operand), result)
            return result
        if isinstance(expression, Binary):
            if expression.operator in {"ve", "veya"}:
                raise IRLoweringError(
                    "Aşama 10 IR v1 kısa devreli 've/veya' işlemlerini kontrol akışı/lazy RHS modeli eklenene kadar desteklemiyor."
                )
            left = self._expression(expression.left)
            right = self._expression(expression.right)
            result = self._temp()
            self._emit("binary", (expression.operator, left, right), result)
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
