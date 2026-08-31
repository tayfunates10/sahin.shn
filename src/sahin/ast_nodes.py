from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TypeAlias


@dataclass(frozen=True, slots=True)
class Literal:
    value: str | int | Decimal | bool | None


@dataclass(frozen=True, slots=True)
class Name:
    value: str


Expression: TypeAlias = Literal | Name


@dataclass(frozen=True, slots=True)
class Assignment:
    name: str
    expression: Expression
    binding: bool = False


@dataclass(frozen=True, slots=True)
class Write:
    expression: Expression


Statement: TypeAlias = Assignment | Write


@dataclass(frozen=True, slots=True)
class Program:
    statements: tuple[Statement, ...]
