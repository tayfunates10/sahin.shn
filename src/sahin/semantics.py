from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from difflib import get_close_matches

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
from .optional_flow import parse_type_spec
from .type_model import TypeSpec
from .types import NUMERIC_TYPES, TypeKind


_NUMERIC = set(NUMERIC_TYPES)


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
    type_spec: TypeSpec | None = None
    parameter_specs: tuple[TypeSpec, ...] = ()
    return_spec: TypeSpec | None = None


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
    """Şahin AST üzerinde isim çözümleme, TypeSpec çıkarımı ve tip güvenliği."""

    def __init__(self) -> None:
        self.global_scope = Scope()
        self.diagnostics: list[SemanticDiagnostic] = []

    def analyze(self, program: Program) -> SemanticModel:
        self.global_scope = Scope()
        self.diagnostics = []
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

            parameter_specs = tuple(parse_type_spec(p.type_name) for p in statement.parameters)
            return_spec = parse_type_spec(statement.return_type)
            parameter_types = tuple(self._kind_from_spec(spec) for spec in parameter_specs)
            return_type = self._kind_from_spec(return_spec)
            declaration_kind = _DECLARATION_TYPES.get(statement.kind, TypeKind.BILINMEYEN)
            self.global_scope.symbols[statement.name] = Symbol(
                statement.name,
                declaration_kind,
                statement.kind,
                False,
                statement.location,
                parameter_types,
                return_type,
                TypeSpec.of(declaration_kind),
                parameter_specs,
                return_spec,
            )

    def _statement(
        self,
        statement,
        scope: Scope,
        expected_return: TypeSpec | None = None,
    ) -> None:
        if isinstance(statement, Binding):
            inferred = self._expression(statement.source, scope)
            inferred_spec = self._spec_for_expression(statement.source, scope, inferred)
            if statement.name in scope.symbols:
                self._diagnose(
                    f"{statement.name!r} adı zaten tanımlı; yeni bir '<-' bağlaması için farklı ad kullanın.",
                    statement.location,
                    "SHN-S202",
                )
                return
            scope.symbols[statement.name] = Symbol(
                statement.name,
                self._kind_from_spec(inferred_spec),
                "bağlama",
                True,
                statement.location,
                type_spec=inferred_spec,
            )
            return

        if isinstance(statement, Assignment):
            inferred = self._expression(statement.expression, scope)
            actual_spec = self._spec_for_expression(statement.expression, scope, inferred)
            existing = scope.resolve(statement.name)
            if existing is not None and existing.binding:
                self._diagnose(
                    f"{statement.name!r} '<-' ile bağlı bir değerdir; doğrudan '=' ile değiştirilemez.",
                    statement.location,
                    "SHN-S201",
                )
                return
            if existing is not None:
                expected_spec = self._symbol_spec(existing)
                if not expected_spec.accepts(actual_spec):
                    code = "SHN-T203" if expected_spec.is_optional else "SHN-T201"
                    self._diagnose(
                        f"{statement.name!r} {expected_spec.display()} olarak belirlendi; "
                        f"{actual_spec.display()} değer atanamaz.",
                        statement.location,
                        code,
                    )
                    return
                chosen_spec = expected_spec if not expected_spec.is_unknown else actual_spec
                chosen_kind = self._kind_from_spec(chosen_spec)
            else:
                chosen_spec = actual_spec
                chosen_kind = inferred
            scope.symbols[statement.name] = Symbol(
                statement.name,
                chosen_kind,
                "değer",
                False,
                statement.location,
                type_spec=chosen_spec,
            )
            return

        if isinstance(statement, Write):
            self._expression(statement.expression, scope)
            return

        if isinstance(statement, Declaration):
            child = Scope(scope)
            for parameter in statement.parameters:
                spec = parse_type_spec(parameter.type_name)
                child.symbols[parameter.name] = Symbol(
                    parameter.name,
                    self._kind_from_spec(spec),
                    "parametre",
                    False,
                    parameter.location,
                    type_spec=spec,
                )
            declared_return = parse_type_spec(statement.return_type)
            for nested in statement.body:
                self._statement(nested, child, declared_return)
            if statement.inline_expression is not None:
                inline_type = self._expression(statement.inline_expression, child)
                inline_spec = self._spec_for_expression(statement.inline_expression, child, inline_type)
                self._check_return_type(inline_spec, declared_return, statement.location)
            return

        if isinstance(statement, FieldDeclaration):
            spec = parse_type_spec(statement.type_name)
            scope.symbols[statement.name] = Symbol(
                statement.name,
                self._kind_from_spec(spec),
                "alan",
                False,
                statement.location,
                type_spec=spec,
            )
            return

        if isinstance(statement, IfStatement):
            condition_type = self._expression(statement.condition, scope)
            if condition_type not in {TypeKind.MANTIK, TypeKind.BILINMEYEN}:
                self._diagnose(
                    "'ise' koşulu evet/hayır sonucu üretmelidir.",
                    statement.location,
                    "SHN-T401",
                )
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
            unknown = TypeSpec.of(TypeKind.BILINMEYEN)
            child.symbols[statement.name] = Symbol(
                statement.name,
                TypeKind.BILINMEYEN,
                "yineleme",
                False,
                statement.location,
                type_spec=unknown,
            )
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
                unknown = TypeSpec.of(TypeKind.BILINMEYEN)
                error_scope.symbols[statement.error_name] = Symbol(
                    statement.error_name,
                    TypeKind.BILINMEYEN,
                    "hata",
                    type_spec=unknown,
                )
            for nested in statement.except_body:
                self._statement(nested, error_scope, expected_return)
            return

        if isinstance(statement, Command):
            if statement.name == "ver" and statement.arguments:
                actual_kind = self._expression(statement.arguments[0], scope)
                actual_spec = self._spec_for_expression(statement.arguments[0], scope, actual_kind)
                self._check_return_type(actual_spec, expected_return, statement.location)
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
            target_type = self._expression(
                expression.target,
                scope,
                allow_implicit_names=allow_implicit_names,
            )
            if isinstance(expression.target, Name):
                target_symbol = scope.resolve(expression.target.value)
                if target_symbol is not None:
                    target_spec = self._symbol_spec(target_symbol)
                    if target_spec.members == frozenset({TypeKind.YOK}):
                        self._diagnose(
                            "'yok' değerinin bir alanına erişilemez; önce değerin varlığını doğrulayın.",
                            expression.location,
                            "SHN-T301",
                        )
                    elif target_spec.can_be_yok:
                        self._diagnose(
                            f"{expression.target.value!r} değeri {target_spec.display()} olabilir; "
                            "alan erişiminden önce 'yok' durumu daraltılmalıdır.",
                            expression.location,
                            "SHN-T302",
                        )
            elif target_type is TypeKind.YOK:
                self._diagnose(
                    "'yok' değerinin bir alanına erişilemez; önce değerin varlığını doğrulayın.",
                    expression.location,
                    "SHN-T301",
                )
            return TypeKind.BILINMEYEN

        if isinstance(expression, Call):
            callee_type = self._expression(
                expression.callee,
                scope,
                allow_implicit_names=allow_implicit_names,
            )
            argument_types = tuple(
                self._expression(argument, scope, allow_implicit_names=allow_implicit_names)
                for argument in expression.arguments
            )
            argument_specs = tuple(
                self._spec_for_expression(argument, scope, kind)
                for argument, kind in zip(expression.arguments, argument_types)
            )
            if isinstance(expression.callee, Name):
                symbol = scope.resolve(expression.callee.value)
                if symbol is not None and symbol.kind == "akış":
                    self._check_call(symbol, argument_types, argument_specs, expression.location)
                    return symbol.return_type
            return TypeKind.BILINMEYEN if callee_type is TypeKind.BILINMEYEN else TypeKind.BILINMEYEN

        if isinstance(expression, Unary):
            operand_type = self._expression(
                expression.operand,
                scope,
                allow_implicit_names=allow_implicit_names,
            )
            if expression.operator in {"!", "değil"}:
                if operand_type not in {TypeKind.MANTIK, TypeKind.BILINMEYEN}:
                    self._diagnose(
                        "'değil' yalnızca evet/hayır değerine uygulanabilir.",
                        expression.location,
                        "SHN-T402",
                    )
                return TypeKind.MANTIK
            if expression.operator in {"+", "-"} and operand_type not in _NUMERIC | {TypeKind.BILINMEYEN}:
                self._diagnose(
                    "Sayısal tekli işlem yalnızca sayı/ondalık/para üzerinde kullanılabilir.",
                    expression.location,
                    "SHN-T403",
                )
            return operand_type

        if isinstance(expression, Binary):
            left = self._expression(expression.left, scope, allow_implicit_names=allow_implicit_names)
            right = self._expression(expression.right, scope, allow_implicit_names=allow_implicit_names)
            op = expression.operator
            if op in {"ve", "veya"}:
                if left not in {TypeKind.MANTIK, TypeKind.BILINMEYEN} or right not in {
                    TypeKind.MANTIK,
                    TypeKind.BILINMEYEN,
                }:
                    self._diagnose(
                        "'ve/veya' yalnızca evet/hayır değerleriyle kullanılabilir.",
                        expression.location,
                        "SHN-T404",
                    )
                return TypeKind.MANTIK
            if op in {"==", "!="}:
                if not self._comparable(left, right):
                    self._diagnose(
                        f"{left.value} ile {right.value} karşılaştırılamaz.",
                        expression.location,
                        "SHN-T405",
                    )
                return TypeKind.MANTIK
            if op in {"<", "<=", ">", ">="}:
                if not (left in _NUMERIC and right in _NUMERIC) and TypeKind.BILINMEYEN not in {
                    left,
                    right,
                }:
                    self._diagnose(
                        "Sıralı karşılaştırma iki sayısal değer gerektirir.",
                        expression.location,
                        "SHN-T406",
                    )
                return TypeKind.MANTIK
            if op in {"+", "-", "*", "/", "%"}:
                if op == "+" and left is TypeKind.YAZI and right is TypeKind.YAZI:
                    return TypeKind.YAZI
                if TypeKind.BILINMEYEN not in {left, right} and not (
                    left in _NUMERIC and right in _NUMERIC
                ):
                    self._diagnose(
                        "Aritmetik işlem uyumlu sayısal değerler gerektirir.",
                        expression.location,
                        "SHN-T407",
                    )
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
            self._expression(
                expression.expression,
                scope,
                allow_implicit_names=allow_implicit_names,
            )
            return TypeKind.MANTIK

        if isinstance(expression, RangeExpression):
            start = self._expression(expression.start, scope, allow_implicit_names=allow_implicit_names)
            end = self._expression(expression.end, scope, allow_implicit_names=allow_implicit_names)
            if TypeKind.BILINMEYEN not in {start, end} and not (
                start in _NUMERIC and end in _NUMERIC
            ):
                self._diagnose(
                    "Aralık başlangıcı ve sonu sayısal olmalıdır.",
                    expression.location,
                    "SHN-T408",
                )
            return TypeKind.BILINMEYEN

        if isinstance(expression, Pipeline):
            self._expression(expression.source, scope, allow_implicit_names=allow_implicit_names)
            for stage in expression.stages:
                for argument in stage.arguments:
                    self._expression(argument, scope, allow_implicit_names=True)
            return TypeKind.BILINMEYEN

        return TypeKind.BILINMEYEN

    def _check_call(
        self,
        symbol: Symbol,
        actual: tuple[TypeKind, ...],
        actual_specs: tuple[TypeSpec, ...],
        location: SourceLocation | None,
    ) -> None:
        expected_specs = symbol.parameter_specs or tuple(
            TypeSpec.of(kind) for kind in symbol.parameter_types
        )
        if len(actual_specs) != len(expected_specs):
            self._diagnose(
                f"{symbol.name!r} akışı {len(expected_specs)} parametre bekliyor; "
                f"{len(actual_specs)} verildi.",
                location,
                "SHN-T101",
            )
            return
        for index, (expected_spec, got_spec) in enumerate(
            zip(expected_specs, actual_specs),
            start=1,
        ):
            if not expected_spec.accepts(got_spec):
                self._diagnose(
                    f"{symbol.name!r} akışının {index}. parametresi {expected_spec.display()} "
                    f"bekliyor; {got_spec.display()} verildi.",
                    location,
                    "SHN-T102",
                )

    def _check_return_type(
        self,
        actual: TypeSpec,
        expected: TypeSpec | None,
        location: SourceLocation | None,
    ) -> None:
        if expected is None or expected.is_unknown:
            return
        if not expected.accepts(actual):
            self._diagnose(
                f"Akış {expected.display()} döndürmeli; {actual.display()} döndürülüyor.",
                location,
                "SHN-T103",
            )

    def _apply_narrowing(self, condition, yes_scope: Scope, no_scope: Scope) -> None:
        if not isinstance(condition, Predicate) or not isinstance(condition.expression, Name):
            return
        source = yes_scope.parent.resolve(condition.expression.value) if yes_scope.parent else None
        if source is None or condition.predicate != "yok":
            return
        source_spec = self._symbol_spec(source)
        if not source_spec.can_be_yok:
            return
        yes_spec = TypeSpec.of(TypeKind.YOK)
        no_spec = source_spec.narrowed_present()
        yes_scope.symbols[source.name] = self._copy_symbol_with_spec(source, yes_spec)
        no_scope.symbols[source.name] = self._copy_symbol_with_spec(source, no_spec)

    @staticmethod
    def _copy_symbol_with_spec(source: Symbol, spec: TypeSpec) -> Symbol:
        return Symbol(
            source.name,
            SemanticAnalyzer._kind_from_spec(spec),
            source.kind,
            source.binding,
            source.location,
            source.parameter_types,
            source.return_type,
            spec,
            source.parameter_specs,
            source.return_spec,
        )

    @staticmethod
    def _symbol_spec(symbol: Symbol) -> TypeSpec:
        return symbol.type_spec or TypeSpec.of(symbol.type_kind)

    def _spec_for_expression(
        self,
        expression,
        scope: Scope,
        fallback_kind: TypeKind,
    ) -> TypeSpec:
        if isinstance(expression, Literal):
            return TypeSpec.of(self._literal_type(expression.value))
        if isinstance(expression, Name):
            symbol = scope.resolve(expression.value)
            if symbol is not None:
                return self._symbol_spec(symbol)
        if isinstance(expression, Call) and isinstance(expression.callee, Name):
            symbol = scope.resolve(expression.callee.value)
            if symbol is not None and symbol.kind == "akış":
                return symbol.return_spec or TypeSpec.of(symbol.return_type)
        return TypeSpec.of(fallback_kind)

    @staticmethod
    def _kind_from_spec(spec: TypeSpec) -> TypeKind:
        if len(spec.members) == 1:
            return next(iter(spec.members))
        return TypeKind.BILINMEYEN

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
        return SemanticAnalyzer._kind_from_spec(parse_type_spec(name))

    def _diagnose(self, message: str, location: SourceLocation | None, code: str) -> None:
        self.diagnostics.append(SemanticDiagnostic(message, location, code))


def analyze(program: Program) -> SemanticModel:
    return SemanticAnalyzer().analyze(program)
