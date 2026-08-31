from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TypeAlias


@dataclass(frozen=True, slots=True)
class SourceLocation:
    line: int
    column: int


@dataclass(frozen=True, slots=True)
class Literal:
    value: str | int | Decimal | bool | None
    location: SourceLocation | None = None


@dataclass(frozen=True, slots=True)
class Name:
    value: str
    location: SourceLocation | None = None


@dataclass(frozen=True, slots=True)
class Unary:
    operator: str
    operand: Expression
    location: SourceLocation | None = None


@dataclass(frozen=True, slots=True)
class Binary:
    left: Expression
    operator: str
    right: Expression
    location: SourceLocation | None = None


@dataclass(frozen=True, slots=True)
class Predicate:
    expression: Expression
    predicate: str
    location: SourceLocation | None = None


@dataclass(frozen=True, slots=True)
class Member:
    target: Expression
    name: str
    location: SourceLocation | None = None


@dataclass(frozen=True, slots=True)
class Call:
    callee: Expression
    arguments: tuple[Expression, ...]
    location: SourceLocation | None = None


@dataclass(frozen=True, slots=True)
class RangeExpression:
    start: Expression
    end: Expression
    location: SourceLocation | None = None


@dataclass(frozen=True, slots=True)
class PipelineStage:
    name: str
    arguments: tuple[Expression, ...]
    location: SourceLocation | None = None


@dataclass(frozen=True, slots=True)
class Pipeline:
    source: Expression
    stages: tuple[PipelineStage, ...]
    location: SourceLocation | None = None


Expression: TypeAlias = (
    Literal
    | Name
    | Unary
    | Binary
    | Predicate
    | Member
    | Call
    | RangeExpression
    | Pipeline
)


@dataclass(frozen=True, slots=True)
class Parameter:
    name: str
    type_name: str | None = None
    location: SourceLocation | None = None


@dataclass(frozen=True, slots=True)
class Assignment:
    name: str
    expression: Expression
    binding: bool = False
    location: SourceLocation | None = None


@dataclass(frozen=True, slots=True)
class Write:
    expression: Expression
    location: SourceLocation | None = None


@dataclass(frozen=True, slots=True)
class FieldDeclaration:
    name: str
    type_name: str
    modifiers: tuple[str, ...] = ()
    location: SourceLocation | None = None


@dataclass(frozen=True, slots=True)
class Command:
    name: str
    arguments: tuple[Expression, ...] = ()
    subject: Expression | None = None
    arrow: Expression | None = None
    body: tuple[Statement, ...] = ()
    location: SourceLocation | None = None


@dataclass(frozen=True, slots=True)
class Declaration:
    kind: str
    name: str | None
    parameters: tuple[Parameter, ...] = ()
    header: tuple[Expression, ...] = ()
    return_type: str | None = None
    body: tuple[Statement, ...] = ()
    inline_expression: Expression | None = None
    location: SourceLocation | None = None


@dataclass(frozen=True, slots=True)
class IfStatement:
    condition: Expression
    body: tuple[Statement, ...]
    else_body: tuple[Statement, ...] = ()
    location: SourceLocation | None = None


@dataclass(frozen=True, slots=True)
class ForEach:
    name: str
    iterable: Expression
    body: tuple[Statement, ...]
    location: SourceLocation | None = None


@dataclass(frozen=True, slots=True)
class MatchCase:
    pattern: Expression
    statement: Statement
    location: SourceLocation | None = None


@dataclass(frozen=True, slots=True)
class MatchStatement:
    subject: Expression
    cases: tuple[MatchCase, ...]
    location: SourceLocation | None = None


@dataclass(frozen=True, slots=True)
class TryStatement:
    body: tuple[Statement, ...]
    error_name: str | None
    except_body: tuple[Statement, ...]
    location: SourceLocation | None = None


@dataclass(frozen=True, slots=True)
class ExpressionStatement:
    expression: Expression
    location: SourceLocation | None = None


Statement: TypeAlias = (
    Assignment
    | Write
    | FieldDeclaration
    | Command
    | Declaration
    | IfStatement
    | ForEach
    | MatchStatement
    | TryStatement
    | ExpressionStatement
)


@dataclass(frozen=True, slots=True)
class Program:
    statements: tuple[Statement, ...]
