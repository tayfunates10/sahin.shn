from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import json

from .ast_nodes import (
    Assignment,
    Binary,
    Binding,
    Call,
    Command,
    Declaration,
    Expression,
    ExpressionStatement,
    IfStatement,
    Literal,
    Member,
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
class IRFlow:
    """Bir Şahin `akış` tanımının bağımsız, çağrı-frame güvenli IR gövdesi."""

    name: str
    parameters: tuple[str, ...]
    parameter_types: tuple[str | None, ...]
    return_type: str | None
    captures: tuple[str, ...]
    instructions: tuple[IRInstruction, ...]

    def canonical(self) -> str:
        payload = {
            "captures": list(self.captures),
            "instructions": [json.loads(item.canonical()) for item in self.instructions],
            "name": self.name,
            "parameter_types": list(self.parameter_types),
            "parameters": list(self.parameters),
            "return_type": self.return_type,
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class IRProgram:
    version: int
    instructions: tuple[IRInstruction, ...]
    flows: tuple[IRFlow, ...] = ()

    def canonical(self) -> str:
        payload = {
            "instructions": [json.loads(item.canonical()) for item in self.instructions],
            "version": self.version,
        }
        # Mevcut IR v1 canonical sözleşmesini akış içermeyen programlarda byte-byte koru.
        if self.flows:
            payload["flows"] = [json.loads(flow.canonical()) for flow in self.flows]
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class _Lowerer:
    def __init__(
        self,
        *,
        flow_names: dict[str, str] | None = None,
        initial_names: dict[str, str] | None = None,
        in_flow: bool = False,
    ) -> None:
        self.instructions: list[IRInstruction] = []
        self.flows: list[IRFlow] = []
        self._next_temp = 0
        self._next_label = 0
        self._next_scope = 0
        self._scopes: list[tuple[int | None, dict[str, str]]] = [(None, dict(initial_names or {}))]
        self._flow_names = dict(flow_names or {})
        self._in_flow = in_flow
        self._capture_candidates = set((initial_names or {}).values())
        self._captures: set[str] = set()

    def lower(self, program: Program) -> IRProgram:
        if not self._in_flow:
            self._predeclare_flows(program)
        for statement in program.statements:
            self._statement(statement)
        return IRProgram(version=1, instructions=tuple(self.instructions), flows=tuple(self.flows))

    def _predeclare_flows(self, program: Program) -> None:
        for statement in program.statements:
            if isinstance(statement, Declaration) and statement.kind == "akış" and statement.name:
                self._flow_names.setdefault(statement.name, f"@akış:{statement.name}")

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
                physical = names[name]
                if physical in self._capture_candidates:
                    self._captures.add(physical)
                return physical
        return None

    def _visible_names(self) -> dict[str, str]:
        visible: dict[str, str] = {}
        for _, names in self._scopes:
            visible.update(names)
        return visible

    def _emit(self, opcode: str, operands: tuple[str, ...] = (), result: str | None = None) -> None:
        self.instructions.append(IRInstruction(opcode, operands, result))

    def _lower_flow(self, declaration: Declaration) -> None:
        if not declaration.name:
            raise IRLoweringError("İsimsiz `akış` tanımı IR ABI'ına indirgenemez.")
        flow_name = self._flow_names.get(declaration.name)
        if flow_name is None:
            raise IRLoweringError(f"Ön tanımı bulunmayan `akış`: {declaration.name!r}.")

        child = _Lowerer(
            flow_names=self._flow_names,
            initial_names=self._visible_names(),
            in_flow=True,
        )
        child._push_scope()
        parameters: list[str] = []
        try:
            for parameter in declaration.parameters:
                parameters.append(child._declare_name(parameter.name))

            if declaration.inline_expression is not None:
                value = child._expression(declaration.inline_expression)
                child._emit("return", (value,))
            else:
                for statement in declaration.body:
                    child._statement(statement)

            # Runtime gibi blok sonunda örtük `yok` döndür. Açık `return` sonrası bu
            # instruction unreachable olabilir; control-flow doğrulaması bunu güvenle tolere eder.
            implicit = child._temp()
            child._emit("const", (child._literal(None),), implicit)
            child._emit("return", (implicit,))
        finally:
            child._pop_scope()

        self.flows.append(
            IRFlow(
                name=flow_name,
                parameters=tuple(parameters),
                parameter_types=tuple(parameter.type_name for parameter in declaration.parameters),
                return_type=declaration.return_type,
                captures=tuple(sorted(child._captures)),
                instructions=tuple(child.instructions),
            )
        )

    def _statement(self, statement) -> None:
        if isinstance(statement, Declaration):
            if statement.kind != "akış":
                raise IRLoweringError(
                    f"Aşama 10 IR v1 henüz {statement.kind!r} Declaration ABI'ını desteklemiyor."
                )
            if self._in_flow:
                raise IRLoweringError("İç içe `akış` Declaration ABI'ı henüz fail-closed tutuluyor.")
            self._lower_flow(statement)
            return
        if isinstance(statement, Command):
            if statement.name == "ver" and self._in_flow:
                if statement.arguments:
                    value = self._expression(statement.arguments[0])
                else:
                    value = self._temp()
                    self._emit("const", (self._literal(None),), value)
                self._emit("return", (value,))
                return
            raise IRLoweringError(
                f"Aşama 10 IR v1 henüz {statement.name!r} Command düğümünü bu kapsamda desteklemiyor."
            )
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
        if isinstance(expression, Call):
            if not isinstance(expression.callee, Name):
                raise IRLoweringError("Call ABI v1 yalnız doğrudan adlandırılmış `akış` çağrılarını destekliyor.")
            flow_name = self._flow_names.get(expression.callee.value)
            if flow_name is None:
                raise IRLoweringError(
                    f"Call ABI için doğrulanmış `akış` bulunamadı: {expression.callee.value!r}."
                )
            arguments = tuple(self._expression(argument) for argument in expression.arguments)
            result = self._temp()
            self._emit("call", (flow_name, *arguments), result)
            return result
        if isinstance(expression, Name):
            if expression.value in self._flow_names:
                raise IRLoweringError("`akış` değeri doğrudan taşınamaz; Call ABI v1 yalnız doğrudan çağrıyı destekler.")
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
        if isinstance(expression, Member):
            target = self._expression(expression.target)
            if not expression.name or expression.name.startswith("%"):
                raise IRLoweringError(f"Geçersiz üye adı IR'a indirgenemedi: {expression.name!r}")
            result = self._temp()
            self._emit("member", (expression.name, target), result)
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
