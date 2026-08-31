from __future__ import annotations

import unicodedata

from .tokens import Token, TokenKind


class LexerError(ValueError):
    pass


_TWO_CHAR = {
    "<-": TokenKind.BIND,
    "->": TokenKind.ARROW,
    "=>": TokenKind.FAT_ARROW,
    "..": TokenKind.RANGE,
    "<=": TokenKind.OPERATOR,
    ">=": TokenKind.OPERATOR,
    "==": TokenKind.OPERATOR,
    "!=": TokenKind.OPERATOR,
}

_SINGLE = {
    "=": TokenKind.ASSIGN,
    ":": TokenKind.COLON,
    ",": TokenKind.COMMA,
    ".": TokenKind.DOT,
    "|": TokenKind.PIPE,
    "(": TokenKind.LPAREN,
    ")": TokenKind.RPAREN,
}

_OPERATOR_CHARS = set("+-*/%<>!")


def _is_identifier_start(ch: str) -> bool:
    return ch == "_" or ch.isalpha()


def _is_identifier_continue(ch: str) -> bool:
    return ch == "_" or ch.isalpha() or ch.isdigit()


class Lexer:
    """Şahin kaynak kodunu dilin kendi token akışına dönüştürür."""

    def __init__(self, source: str) -> None:
        self.source = unicodedata.normalize(
            "NFC", source.replace("\r\n", "\n").replace("\r", "\n")
        )

    def tokenize(self) -> list[Token]:
        tokens: list[Token] = []
        indents = [0]
        lines = self.source.split("\n")

        for line_no, raw_line in enumerate(lines, start=1):
            if "\t" in raw_line[: len(raw_line) - len(raw_line.lstrip())]:
                raise LexerError(
                    f"Satır {line_no}: girintide sekme kullanılamaz; boşluk kullanın."
                )

            stripped = raw_line.lstrip(" ")
            if not stripped or stripped.startswith("//"):
                continue

            indent = len(raw_line) - len(stripped)
            if indent % 4 != 0:
                raise LexerError(f"Satır {line_no}: girinti 4 boşluğun katı olmalı.")

            if indent > indents[-1]:
                indents.append(indent)
                tokens.append(Token(TokenKind.INDENT, "", line_no, 1))
            else:
                while indent < indents[-1]:
                    indents.pop()
                    tokens.append(Token(TokenKind.DEDENT, "", line_no, 1))
                if indent != indents[-1]:
                    raise LexerError(
                        f"Satır {line_no}: girinti daha önce açılmış bir blokla eşleşmiyor."
                    )

            self._tokenize_line(stripped, line_no, indent + 1, tokens)
            tokens.append(Token(TokenKind.NEWLINE, "", line_no, len(raw_line) + 1))

        final_line = max(1, len(lines))
        while len(indents) > 1:
            indents.pop()
            tokens.append(Token(TokenKind.DEDENT, "", final_line, 1))
        tokens.append(Token(TokenKind.EOF, "", final_line, 1))
        return self._collapse_type_contracts(tokens)

    @staticmethod
    def _collapse_type_contracts(tokens: list[Token]) -> list[Token]:
        """Tip konumundaki `X veya yok` yazımını tek IDENTIFIER olarak kanonikleştirir.

        `veya` normal ifadelerde bir mantıksal operatördür. Bu nedenle birleştirme
        yalnızca `:` parametre/alan tipi veya `->` dönüş tipi sonrasında yapılır.
        Parser böylece başka dillerdeki union operatörünü taklit eden ayrı bir AST
        düğümüne ihtiyaç duymadan Şahin'in doğal tip sözleşmesini alır.
        """
        out: list[Token] = []
        i = 0
        type_context = False

        while i < len(tokens):
            token = tokens[i]
            out.append(token)

            if token.kind in {TokenKind.COLON, TokenKind.ARROW}:
                type_context = True
                i += 1
                continue

            if type_context and token.kind is TokenKind.IDENTIFIER:
                if (
                    i + 2 < len(tokens)
                    and tokens[i + 1].kind is TokenKind.IDENTIFIER
                    and tokens[i + 1].value == "veya"
                    and tokens[i + 2].kind is TokenKind.IDENTIFIER
                    and tokens[i + 2].value == "yok"
                ):
                    out[-1] = Token(
                        TokenKind.IDENTIFIER,
                        f"{token.value} veya yok",
                        token.line,
                        token.column,
                    )
                    i += 3
                    type_context = False
                    continue
                type_context = False

            if token.kind in {
                TokenKind.NEWLINE,
                TokenKind.COMMA,
                TokenKind.ASSIGN,
                TokenKind.BIND,
                TokenKind.FAT_ARROW,
            }:
                type_context = False

            i += 1

        return out

    def _tokenize_line(
        self, text: str, line: int, base_column: int, out: list[Token]
    ) -> None:
        i = 0
        size = len(text)

        while i < size:
            ch = text[i]
            column = base_column + i

            if ch.isspace():
                i += 1
                continue

            if text.startswith("//", i):
                return

            pair = text[i : i + 2]
            if pair in _TWO_CHAR:
                out.append(Token(_TWO_CHAR[pair], pair, line, column))
                i += 2
                continue

            if ch in ('"', "'"):
                value, i = self._read_string(text, i, line)
                out.append(Token(TokenKind.STRING, value, line, column))
                continue

            if ch.isdigit():
                start = i
                while i < size and text[i].isdigit():
                    i += 1
                if (
                    i < size
                    and text[i] in ".,"
                    and i + 1 < size
                    and text[i + 1].isdigit()
                ):
                    decimal = text[i]
                    i += 1
                    while i < size and text[i].isdigit():
                        i += 1
                    value = text[start:i].replace(decimal, ".")
                else:
                    value = text[start:i]
                if i < size and text[i] == "₺":
                    value += "₺"
                    i += 1
                out.append(Token(TokenKind.NUMBER, value, line, column))
                continue

            if _is_identifier_start(ch):
                start = i
                i += 1
                while i < size and _is_identifier_continue(text[i]):
                    i += 1
                out.append(Token(TokenKind.IDENTIFIER, text[start:i], line, column))
                continue

            if ch in _SINGLE:
                out.append(Token(_SINGLE[ch], ch, line, column))
                i += 1
                continue

            if ch in _OPERATOR_CHARS:
                start = i
                i += 1
                while i < size and text[i] in _OPERATOR_CHARS:
                    i += 1
                out.append(Token(TokenKind.OPERATOR, text[start:i], line, column))
                continue

            raise LexerError(
                f"Satır {line}, sütun {column}: tanınmayan karakter {ch!r}."
            )

    @staticmethod
    def _read_string(text: str, start: int, line: int) -> tuple[str, int]:
        quote = text[start]
        i = start + 1
        chars: list[str] = []

        while i < len(text):
            ch = text[i]
            if ch == quote:
                return "".join(chars), i + 1
            if ch == "\\":
                i += 1
                if i >= len(text):
                    break
                escapes = {
                    "n": "\n",
                    "t": "\t",
                    "r": "\r",
                    "\\": "\\",
                    '"': '"',
                    "'": "'",
                }
                chars.append(escapes.get(text[i], text[i]))
                i += 1
                continue
            chars.append(ch)
            i += 1

        raise LexerError(f"Satır {line}: kapanmamış metin değeri.")


def tokenize(source: str) -> list[Token]:
    return Lexer(source).tokenize()
