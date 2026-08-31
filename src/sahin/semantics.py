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
    PARA = "para"
    MANTIK = "evet_hayır"
    YOK = "yok"
    AKIS = "akış"
    KAYIT = "kayıt"
    EKRAN = "ekran"
    GORUNUM = "görünüm"
    UYGULAMA = "uygulama"
    BILINMEYEN = "bilinmeyen"


_NUMERIC = {TypeKind.SAYI, TypeKind.ONDALIK, TypeKind.PARA}


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
    parameter_types: tuple[TypeKind, ...] = ()
    return_type: TypeKind = TypeKind.BILINMEYEN


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
    """Şahin AST üzerinde isim çözümleme, tip çıkarımı ve tip güvenliği katmanı."""

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
            if not isinstance(statement, Declaration) or not statement.name:
                continue
            if statement.name in self.global_scope.symbols:
                self._diagnose(
                    f"{statement.name!r} adı birden fazla üst seviye tanımda kullanılmış.",
                    statement.location,
                    "SHN-S101",
                )
                continue
            parameter_types = tuple(
                self._type_from_name(parameter.type_name) for parameter in statement.parameters
            )
            return_type = self._type_from_name(statement.return_type)
            self.global_scope.symbols[statement.name] = Symbol(
                statement.name,
                _DECLARATION_TYPES.get(statement.kind, TypeKind.BILINMEYEN),
                statement.kind,
                False,
                statement.location,
                parameter_types,
                return_type,
            )

    def _statement(self, statement, scope: Scope, expected_return: TypeKind = TypeKind.BILINMEYEN) -> None:
        if isinstance(statement, Binding):
            inferred = self._expression(statement.source, scope)
            if statement.name in scope.symbols:
                self._diagnose(
                    f"{statement.name!r} adı zaten tanımlı; yeni bir '<-' bağlaması için farklı ad kullanın.",
                    statement.location,
                    "SHN-S202",
                )
                return
            scope.symbols[statement.name] = Symbol(statement.name, inferred, "bağlama", True, statement.location)
            return

        if isinstance(statement, Assignment):
            inferred = self._expression(statement.expression, scope)
            existing = scope.resolve(statement.name)
            if existing is not None and existing.binding:
                self._diagnose(
                    f"{statement.name!r} '<-' ile bağlı bir değerdir; doğrudan '=' ile değiştirilemez.",
                    statement.location,
                    "SHN-S201",
                )
                return
            if existing is not None and not self._compatible(existing.type_kind, inferred):
                self._diagnose(
                    f"{statement.name!r} {existing.type_kind.value} olarak belirlendi; {inferred.value} değer atanamaz.",
                    statement.location,
                    "SHN-T201",
                )
                return
            scope.symbols[statement.name] = Symbol(statement.name, inferred, "değer", False, statement.location)
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
            declared_return = self._type_from_name(statement.return_type)
            for nested in statement.body:
                self._statement(nested, child, declared_return)
            if statement.inline_expression is not None:
                inline_type = self._expression(statement.inline_expression, child)
                self._check_return_type(inline_type, declared_return, statement.location)
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
            condition_type = self._expression(statement.condition, scope)
            if condition_type not in {TypeKind.MANTIK, TypeKind.BILINMEYEN}:
                self._diagnose("'ise' koşulu evet/hayır sonucu üretmelidir.", statement.location, "SHN-T401")
            yes_scope = Scope(scope)
            no_scope = Scope(scope)
            self._apply_narrowing(statement.condition, yes_scope, no_scope)
            for nested in statement.body:
                self._statement(nested, yes_scope, expected_return)
            for nested in statement.else_body:
                self._statement(nested, no_scope, expected_return)
            return

        if isinstance(statement, ForEach):
            self._expression(statement.iterable, scope)
            child = Scope(scope)
            child.symbols[statement.name] = Symbol(statement.name, TypeKind.BILINMEYEN, "yineleme", False, statement.location)
            for nested in statement.body:
                self._statement(nested, child, expected_return)
            return

        if isinstance(statement, MatchStatement):
            self._expression(statement.subject, scope)
            for case in statement.cases:
                child = Scope(scope)
                self._statement(case.statement, child, expected_return)
            return

        if isinstance(statement, TryStatement):
            body_scope = Scope(scope)
            for nested in statement.body:
                self._statement(nested, body_scope, expected_return)
            error_scope = Scope(scope)
            if statement.error_name:
                error_scope.symbols[statement.error_name] = Symbol(statement.error_name, TypeKind.BILINMEYEN, "hata")
            for nested in statement.except_body:
                self._statement(nested, error_scope, expected_return)
            return

        if isinstance(statement, Command):
            if statement.name == "ver" and statement.arguments:
                actual = self._expression(statement.arguments[0], scope)
                self._check_return_type(actual, expected_return, statement.location)
                return
            if statement.subject is not None:
                self._expression(statement.subject, scope)
            for argument in statement.arguments:
                if not isinstance(argument, Name):
                    self._expression(argument, scope, allow_implicit_names=True)
            if statement.arrow is not None:
                self._expression(statement.arrow, scope)
            child = Scope(scope)
            for nested in statement.body:
                self._statement(nested, child, expected_return)
            return

    def _expression(self, expression, scope: Scope, *, allow_implicit_names: bool = False) -> TypeKind:
        if isinstance(expression, Literal):
            return self._literal_type(expression.value)

        if isinstance(expression, Name):
            symbol = scope.resolve(expression.value)
            if symbol is not None:
                return symbol.type_kind
            if allow_implicit_names:
                return TypeKind.BILINMEYEN
            suggestion = get_close_matches(expression.value, scope.visible_names(), n=1, cutoff=0.6)
            suffix = f" Şunu mu demek istediniz: {suggestion[0]}?" if suggestion else ""
            self._diagnose(
                f"{expression.value!r} adı bu kapsamda tanımlı değil.{suffix}",
                expression.location,
                "SHN-S301",
            )
            return TypeKind.BILINMEYEN

        if isinstance(expression, Member):
            target_type = self._expression(expression.target, scope, allow_implicit_names=allow_implicit_names)
            if target_type is TypeKind.YOK:
                self._diagnose(
                    "'yok' değerinin bir alanına erişilemez; önce değerin varlığını doğrulayın.",
                    expression.location,
                    "SHN-T301",
                )
            return TypeKind.BILINMEYEN

        if isinstance(expression, Call):
            callee_type = self._expression(expression.callee, scope, allow_implicit_names=allow_implicit_names)
            argument_types = tuple(
                self._expression(argument, scope, allow_implicit_names=allow_implicit_names)
                for argument in expression.arguments
            )
            if isinstance(expression.callee, Name):
                symbol = scope.resolve(expression.callee.value)
                if symbol is not None and symbol.kind == "akış":
                    self._check_call(symbol, argument_types, expression.location)
                    return symbol.return_type
            return TypeKind.BILINMEYEN if callee_type is TypeKind.BILINMEYEN else TypeKind.BILINMEYEN

        if isinstance(expression, Unary):
            operand_type = self._expression(expression.operand, scope, allow_implicit_names=allow_implicit_names)
            if expression.operator in {"!", "değil"}:
                if operand_type not in {TypeKind.MANTIK, TypeKind.BILINMEYEN}:
                    self._diagnose("'değil' yalnızca evet/hayır değerine uygulanabilir.", expression.location, "SHN-T402")
                return TypeKind.MANTIK
            if expression.operator in {"+", "-"} and operand_type not in _NUMERIC | {TypeKind.BILINMEYEN}:
                self._diagnose("Sayısal tekli işlem yalnızca sayı/ondalık/para üzerinde kullanılabilir.", expression.location, "SHN-T403")
            return operand_type

        if isinstance(expression, Binary):
            left = self._expression(expression.left, scope, allow_implicit_names=allow_implicit_names)
            right = self._expression(expression.right, scope, allow_implicit_names=allow_implicit_names)
            op = expression.operator
            if op in {"ve", "veya"}:
                if left not in {TypeKind.MANTIK, TypeKind.BILINMEYEN} or right not in {TypeKind.MANTIK, TypeKind.BILINMEYEN}:
                    self._diagnose("'ve/veya' yalnızca evet/hayır değerleriyle kullanılabilir.", expression.location, "SHN-T404")
                return TypeKind.MANTIK
            if op in {"==", "!="}:
                if not self._comparable(left, right):
                    self._diagnose(f"{left.value} ile {right.value} karşılaştırılamaz.", expression.location, "SHN-T405")
                return TypeKind.MANTIK
            if op in {"<", "<=", ">", ">="}:
                if not (left in _NUMERIC and right in _NUMERIC) and TypeKind.BILINMEYEN not in {left, right}:
                    self._diagnose("Sıralı karşılaştırma iki sayısal değer gerektirir.", expression.location, "SHN-T406")
                return TypeKind.MANTIK
            if op in {"+", "-", "*", "/", "%"}:
                if op == "+" and left is TypeKind.YAZI and right is TypeKind.YAZI:
                    return TypeKind.YAZI
                if TypeKind.BILINMEYEN not in {left, right} and not (left in _NUMERIC and right in _NUMERIC):
                    self._diagnose("Aritmetik işlem uyumlu sayısal değerler gerektirir.", expression.location, "SHN-T407")
                    return TypeKind.BILINMEYEN
                if TypeKind.PARA in {left, right}:
                    return TypeKind.PARA
                if TypeKind.ONDALIK in {left, right} or op == "/":
                    return TypeKind.ONDALIK
                if left is TypeKind.SAYI and right is TypeKind.SAYI:
                    return TypeKind.SAYI
                return TypeKind.BILINMEYEN
            return TypeKind.BILINMEYEN

        if isinstance(expression, Predicate):
            self._expression(expression.expression, scope, allow_implicit_names=allow_implicit_names)
            return TypeKind.MANTIK

        if isinstance(expression, RangeExpression):
            start = self._expression(expression.start, scope, allow_implicit_names=allow_implicit_names)
            end = self._expression(expression.end, scope, allow_implicit_names=allow_implicit_names)
            if TypeKind.BILINMEYEN not in {start, end} and not (start in _NUMERIC and end in _NUMERIC):
                self._diagnose("Aralık başlangıcı ve sonu sayısal olmalıdır.", expression.location, "SHN-T408")
            return TypeKind.BILINMEYEN

        if isinstance(expression, Pipeline):
            self._expression(expression.source, scope, allow_implicit_names=allow_implicit_names)
            for stage in expression.stages:
                for argument in stage.arguments:
                    self._expression(argument, scope, allow_implicit_names=True)
            return TypeKind.BILINMEYEN

        return TypeKind.BILINMEYEN

    def _check_call(self, symbol: Symbol, actual: tuple[TypeKind, ...], location: SourceLocation | None) -> None:
        if len(actual) != len(symbol.parameter_types):
            self._diagnose(
                f"{symbol.name!r} akışı {len(symbol.parameter_types)} parametre bekliyor; {len(actual)} verildi.",
                location,
                "SHN-T101",
            )
            return
        for index, (expected, got) in enumerate(zip(symbol.parameter_types, actual), start=1):
            if not self._compatible(expected, got):
                self._diagnose(
                    f"{symbol.name!r} akışının {index}. parametresi {expected.value} bekliyor; {got.value} verildi.",
                    location,
                    "SHN-T102",
                )

    def _check_return_type(self, actual: TypeKind, expected: TypeKind, location: SourceLocation | None) -> None:
        if expected is TypeKind.BILINMEYEN:
            return
        if not self._compatible(expected, actual):
            self._diagnose(
                f"Akış {expected.value} döndürmeli; {actual.value} döndürülüyor.",
                location,
                "SHN-T103",
            )

    def _apply_narrowing(self, condition, yes_scope: Scope, no_scope: Scope) -> None:
        if not isinstance(condition, Predicate) or not isinstance(condition.expression, Name):
            return
        source = yes_scope.parent.resolve(condition.expression.value) if yes_scope.parent else None
        if source is None:
            return
        if condition.predicate == "yok":
            yes_scope.symbols[source.name] = Symbol(source.name, TypeKind.YOK, source.kind, source.binding, source.location)
            if source.type_kind is TypeKind.YOK:
                no_scope.symbols[source.name] = Symbol(source.name, TypeKind.BILINMEYEN, source.kind, source.binding, source.location)

    @staticmethod
    def _compatible(expected: TypeKind, actual: TypeKind) -> bool:
        if TypeKind.BILINMEYEN in {expected, actual}:
            return True
        if expected is actual:
            return True
        if expected in {TypeKind.ONDALIK, TypeKind.PARA} and actual is TypeKind.SAYI:
            return True
        return False

    @staticmethod
    def _comparable(left: TypeKind, right: TypeKind) -> bool:
        if TypeKind.BILINMEYEN in {left, right}:
            return True
        if left is right:
            return True
        return left in _NUMERIC and right in _NUMERIC

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
            "para": TypeKind.PARA,
            "mantık": TypeKind.MANTIK,
            "evet_hayır": TypeKind.MANTIK,
            "yok": TypeKind.YOK,
        }
        return mapping.get(name or "", TypeKind.BILINMEYEN)

    def _diagnose(self, message: str, location: SourceLocation | None, code: str) -> None:
        self.diagnostics.append(SemanticDiagnostic(message, location, code))


def analyze(program: Program) -> SemanticModel:
    return SemanticAnalyzer().analyze(program)
