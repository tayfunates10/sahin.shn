from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from difflib import get_close_matches
from enum import Enum

from .ast_nodes import (
    Assignment,
    Binary,
    Binding,
    Call,
    Command,
    Declaration,
    FieldDeclaration,
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


class TypeKind(str, Enum):
    YAZI = "yazı"
    SAYI = "sayı"
    ONDALIK = "ondalık"
    MANTIK = "mantık"
    YOK = "yok"
    AKIS = "akış"
    KAYIT = "kayıt"
    EKRAN = "ekran"
    GORUNUM = "görünüm"
    UYGULAMA = "uygulama"
    BILINMEYEN = "bilinmeyen"


@dataclass(frozen=True, slots=True)
class SemanticDiagnostic:
    message: str
    location: SourceLocation | None = None
    code: str = "SHN-S000"

    def format(self) -> str:
        if self.location is None:
            return f"{self.code}: {self.message}"
        return (
            f"{self.code} · Satır {self.location.line}, sütun {self.location.column}: "
            f"{self.message}"
        )


@dataclass(slots=True)
class Symbol:
    name: str
    type_kind: TypeKind = TypeKind.BILINMEYEN
    kind: str = "değer"
    binding: bool = False
    location: SourceLocation | None = None


@dataclass(slots=True)
class Scope:
    parent: Scope | None = None
    symbols: dict[str, Symbol] = field(default_factory=dict)

    def resolve(self, name: str) -> Symbol | None:
        scope: Scope | None = self
        while scope is not None:
            if name in scope.symbols:
                return scope.symbols[name]
            scope = scope.parent
        return None

    def visible_names(self) -> list[str]:
        names: list[str] = []
        scope: Scope | None = self
        while scope is not None:
            names.extend(scope.symbols)
            scope = scope.parent
        return names


@dataclass(frozen=True, slots=True)
class SemanticModel:
    global_symbols: dict[str, Symbol]
    diagnostics: tuple[SemanticDiagnostic, ...]

    @property
    def ok(self) -> bool:
        return not self.diagnostics


_DECLARATION_TYPES = {
    "akış": TypeKind.AKIS,
    "kayıt": TypeKind.KAYIT,
    "ekran": TypeKind.EKRAN,
    "görünüm": TypeKind.GORUNUM,
    "uygulama": TypeKind.UYGULAMA,
}


class SemanticAnalyzer:
    """Şahin AST üzerinde isim çözümleme ve ilk tip çıkarımı katmanı."""

    def __init__(self) -> None:
        self.global_scope = Scope()
        self.diagnostics: list[SemanticDiagnostic] = []

    def analyze(self, program: Program) -> SemanticModel:
        self._predeclare(program)
        for statement in program.statements:
            self._statement(statement, self.global_scope)
        return SemanticModel(dict(self.global_scope.symbols), tuple(self.diagnostics))

    def _predeclare(self, program: Program) -> None:
        for statement in program.statements:
            if isinstance(statement, Declaration) and statement.name:
                if statement.name in self.global_scope.symbols:
                    self._diagnose(
                        f"{statement.name!r} adı birden fazla üst seviye tanımda kullanılmış.",
                        statement.location,
                        "SHN-S101",
                    )
                    continue
                self.global_scope.symbols[statement.name] = Symbol(
                    statement.name,
                    _DECLARATION_TYPES.get(statement.kind, TypeKind.BILINMEYEN),
                    statement.kind,
                    False,
                    statement.location,
                )

    def _statement(self, statement, scope: Scope) -> None:
        if isinstance(statement, Binding):
            inferred = self._expression(statement.source, scope)
            if statement.name in scope.symbols:
                self._diagnose(
                    f"{statement.name!r} adı zaten tanımlı; yeni bir '<-' bağlaması için farklı ad kullanın.",
                    statement.location,
                    "SHN-S202",
                )
                return
            scope.symbols[statement.name] = Symbol(
                statement.name,
                inferred,
                "bağlama",
                True,
                statement.location,
            )
            return

        if isinstance(statement, Assignment):
            inferred = self._expression(statement.expression, scope)
            existing = scope.symbols.get(statement.name)
            if existing is not None and existing.binding:
                self._diagnose(
                    f"{statement.name!r} '<-' ile bağlı bir değerdir; doğrudan '=' ile değiştirilemez.",
                    statement.location,
                    "SHN-S201",
                )
                return
            scope.symbols[statement.name] = Symbol(
                statement.name,
                inferred,
                "değer",
                False,
                statement.location,
            )
            return

        if isinstance(statement, Write):
            self._expression(statement.expression, scope)
            return

        if isinstance(statement, Declaration):
            child = Scope(scope)
            for parameter in statement.parameters:
                child.symbols[parameter.name] = Symbol(
                    parameter.name,
                    self._type_from_name(parameter.type_name),
                    "parametre",
                    False,
                    parameter.location,
                )
            for nested in statement.body:
                self._statement(nested, child)
            if statement.inline_expression is not None:
                self._expression(statement.inline_expression, child)
            return

        if isinstance(statement, FieldDeclaration):
            scope.symbols[statement.name] = Symbol(
                statement.name,
                self._type_from_name(statement.type_name),
                "alan",
                False,
                statement.location,
            )
            return

        if isinstance(statement, IfStatement):
            self._expression(statement.condition, scope)
            yes_scope = Scope(scope)
            for nested in statement.body:
                self._statement(nested, yes_scope)
            no_scope = Scope(scope)
            for nested in statement.else_body:
                self._statement(nested, no_scope)
            return

        if isinstance(statement, ForEach):
            self._expression(statement.iterable, scope)
            child = Scope(scope)
            child.symbols[statement.name] = Symbol(
                statement.name,
                TypeKind.BILINMEYEN,
                "yineleme",
                False,
                statement.location,
            )
            for nested in statement.body:
                self._statement(nested, child)
            return

        if isinstance(statement, MatchStatement):
            self._expression(statement.subject, scope)
            for case in statement.cases:
                child = Scope(scope)
                self._statement(case.statement, child)
            return

        if isinstance(statement, TryStatement):
            body_scope = Scope(scope)
            for nested in statement.body:
                self._statement(nested, body_scope)
            error_scope = Scope(scope)
            if statement.error_name:
                error_scope.symbols[statement.error_name] = Symbol(
                    statement.error_name, TypeKind.BILINMEYEN, "hata"
                )
            for nested in statement.except_body:
                self._statement(nested, error_scope)
            return

        if isinstance(statement, Command):
            if statement.subject is not None:
                self._expression(statement.subject, scope)
            for argument in statement.arguments:
                if not isinstance(argument, Name):
                    self._expression(argument, scope, allow_implicit_names=True)
            if statement.arrow is not None:
                self._expression(statement.arrow, scope)
            child = Scope(scope)
            for nested in statement.body:
                self._statement(nested, child)
            return

    def _expression(
        self, expression, scope: Scope, *, allow_implicit_names: bool = False
    ) -> TypeKind:
        if isinstance(expression, Literal):
            return self._literal_type(expression.value)

        if isinstance(expression, Name):
            symbol = scope.resolve(expression.value)
            if symbol is not None:
                return symbol.type_kind
            if allow_implicit_names:
                return TypeKind.BILINMEYEN
            suggestion = get_close_matches(
                expression.value, scope.visible_names(), n=1, cutoff=0.6
            )
            suffix = (
                f" Şunu mu demek istediniz: {suggestion[0]}?" if suggestion else ""
            )
            self._diagnose(
                f"{expression.value!r} adı bu kapsamda tanımlı değil.{suffix}",
                expression.location,
                "SHN-S301",
            )
            return TypeKind.BILINMEYEN

        if isinstance(expression, Member):
            self._expression(expression.target, scope, allow_implicit_names=allow_implicit_names)
            return TypeKind.BILINMEYEN

        if isinstance(expression, Call):
            self._expression(expression.callee, scope, allow_implicit_names=allow_implicit_names)
            for argument in expression.arguments:
                self._expression(argument, scope, allow_implicit_names=allow_implicit_names)
            return TypeKind.BILINMEYEN

        if isinstance(expression, Unary):
            operand_type = self._expression(
                expression.operand, scope, allow_implicit_names=allow_implicit_names
            )
            if expression.operator in {"!", "değil"}:
                return TypeKind.MANTIK
            return operand_type

        if isinstance(expression, Binary):
            left = self._expression(
                expression.left, scope, allow_implicit_names=allow_implicit_names
            )
            right = self._expression(
                expression.right, scope, allow_implicit_names=allow_implicit_names
            )
            if expression.operator in {"==", "!=", "<", "<=", ">", ">=", "ve", "veya"}:
                return TypeKind.MANTIK
            if TypeKind.ONDALIK in {left, right}:
                return TypeKind.ONDALIK
            if left is TypeKind.SAYI and right is TypeKind.SAYI:
                return TypeKind.SAYI
            return TypeKind.BILINMEYEN

        if isinstance(expression, Predicate):
            self._expression(
                expression.expression, scope, allow_implicit_names=allow_implicit_names
            )
            return TypeKind.MANTIK

        if isinstance(expression, RangeExpression):
            self._expression(expression.start, scope, allow_implicit_names=allow_implicit_names)
            self._expression(expression.end, scope, allow_implicit_names=allow_implicit_names)
            return TypeKind.BILINMEYEN

        if isinstance(expression, Pipeline):
            self._expression(expression.source, scope, allow_implicit_names=allow_implicit_names)
            for stage in expression.stages:
                for argument in stage.arguments:
                    self._expression(argument, scope, allow_implicit_names=True)
            return TypeKind.BILINMEYEN

        return TypeKind.BILINMEYEN

    @staticmethod
    def _literal_type(value: object) -> TypeKind:
        if value is None:
            return TypeKind.YOK
        if isinstance(value, bool):
            return TypeKind.MANTIK
        if isinstance(value, int):
            return TypeKind.SAYI
        if isinstance(value, Decimal):
            return TypeKind.ONDALIK
        if isinstance(value, str):
            return TypeKind.YAZI
        return TypeKind.BILINMEYEN

    @staticmethod
    def _type_from_name(name: str | None) -> TypeKind:
        mapping = {
            "yazı": TypeKind.YAZI,
            "sayı": TypeKind.SAYI,
            "ondalık": TypeKind.ONDALIK,
            "para": TypeKind.ONDALIK,
            "mantık": TypeKind.MANTIK,
        }
        return mapping.get(name or "", TypeKind.BILINMEYEN)

    def _diagnose(
        self, message: str, location: SourceLocation | None, code: str
    ) -> None:
        self.diagnostics.append(SemanticDiagnostic(message, location, code))


def analyze(program: Program) -> SemanticModel:
    return SemanticAnalyzer().analyze(program)
