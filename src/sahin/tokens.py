from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TokenKind(str, Enum):
    IDENTIFIER = "IDENTIFIER"
    NUMBER = "NUMBER"
    STRING = "STRING"
    NEWLINE = "NEWLINE"
    INDENT = "INDENT"
    DEDENT = "DEDENT"
    ASSIGN = "="
    BIND = "<-"
    ARROW = "->"
    FAT_ARROW = "=>"
    COLON = ":"
    COMMA = ","
    DOT = "."
    PIPE = "|"
    RANGE = ".."
    OPERATOR = "OPERATOR"
    EOF = "EOF"


@dataclass(frozen=True, slots=True)
class Token:
    kind: TokenKind
    value: str
    line: int
    column: int

    def __repr__(self) -> str:
        return f"Token({self.kind.value!r}, {self.value!r}, {self.line}:{self.column})"
