from __future__ import annotations

from decimal import Decimal

from .ast_nodes import Assignment, Literal, Name, Program, Write
from .tokens import Token, TokenKind


class ParserError(ValueError):
    pass


class Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.index = 0

    def parse(self) -> Program:
        statements = []
        while not self._at(TokenKind.EOF):
            if self._match(TokenKind.NEWLINE):
                continue
            if self._at(TokenKind.INDENT) or self._at(TokenKind.DEDENT):
                token = self._current()
                raise ParserError(
                    f"Satır {token.line}: bu bootstrap parser henüz blok ifadesi beklemiyordu."
                )
            statements.append(self._statement())
        return Program(tuple(statements))

    def _statement(self):
        first = self._expect(TokenKind.IDENTIFIER, "Bir ifade adı bekleniyordu.")

        if first.value == "yaz":
            expression = self._expression()
            self._line_end()
            return Write(expression)

        if self._at(TokenKind.ASSIGN) or self._at(TokenKind.BIND):
            operator = self._advance()
            expression = self._expression()
            self._line_end()
            return Assignment(first.value, expression, binding=operator.kind is TokenKind.BIND)

        raise ParserError(
            f"Satır {first.line}, sütun {first.column}: {first.value!r} sonrasında '=' veya '<-' bekleniyordu."
        )

    def _expression(self):
        token = self._advance()

        if token.kind is TokenKind.STRING:
            return Literal(token.value)
        if token.kind is TokenKind.NUMBER:
            raw = token.value
            if raw.endswith("₺"):
                return Literal(Decimal(raw[:-1]))
            if "." in raw:
                return Literal(Decimal(raw))
            return Literal(int(raw))
        if token.kind is TokenKind.IDENTIFIER:
            constants = {"evet": True, "hayır": False, "yok": None}
            if token.value in constants:
                return Literal(constants[token.value])
            return Name(token.value)

        raise ParserError(
            f"Satır {token.line}, sütun {token.column}: değer veya isim bekleniyordu."
        )

    def _line_end(self) -> None:
        if self._match(TokenKind.NEWLINE):
            return
        if self._at(TokenKind.EOF):
            return
        token = self._current()
        raise ParserError(
            f"Satır {token.line}, sütun {token.column}: ifade sonunda yeni satır bekleniyordu."
        )

    def _current(self) -> Token:
        return self.tokens[self.index]

    def _advance(self) -> Token:
        token = self._current()
        if token.kind is not TokenKind.EOF:
            self.index += 1
        return token

    def _at(self, kind: TokenKind) -> bool:
        return self._current().kind is kind

    def _match(self, kind: TokenKind) -> bool:
        if self._at(kind):
            self._advance()
            return True
        return False

    def _expect(self, kind: TokenKind, message: str) -> Token:
        if self._at(kind):
            return self._advance()
        token = self._current()
        raise ParserError(f"Satır {token.line}, sütun {token.column}: {message}")


def parse(tokens: list[Token]) -> Program:
    return Parser(tokens).parse()
