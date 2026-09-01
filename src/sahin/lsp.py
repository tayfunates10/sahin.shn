from __future__ import annotations

from dataclasses import dataclass

from .lexer import Lexer
from .parser import Parser
from .semantics import SemanticAnalyzer, Symbol
from .toolchain import LintDiagnostic, lint_source


@dataclass(frozen=True, slots=True)
class LspPosition:
    line: int
    column: int


@dataclass(frozen=True, slots=True)
class LspSymbol:
    name: str
    kind: str
    type_name: str
    line: int | None
    column: int | None


@dataclass(frozen=True, slots=True)
class LspHover:
    name: str
    detail: str


@dataclass(frozen=True, slots=True)
class LspDefinition:
    name: str
    position: LspPosition


@dataclass(frozen=True, slots=True)
class LspSnapshot:
    diagnostics: tuple[LintDiagnostic, ...]
    symbols: tuple[LspSymbol, ...]


class LspAdapter:
    """Şahin'in mevcut lexer/parser/semantic zinciri üstünde salt-okunur LSP çekirdeği.

    Bu adapter yeni bir dil semantiği üretmez. Diagnostics, completion, hover,
    go-to-definition ve symbol bilgisi aynı SemanticAnalyzer modelinden türetilir.
    """

    def snapshot(self, source: str) -> LspSnapshot:
        model = self._model(source)
        symbols = tuple(
            self._to_lsp_symbol(symbol)
            for _, symbol in sorted(model.global_symbols.items(), key=lambda item: item[0])
        )
        return LspSnapshot(lint_source(source), symbols)

    def completions(self, source: str, prefix: str = "") -> tuple[str, ...]:
        model = self._model(source)
        names = sorted(name for name in model.global_symbols if name.startswith(prefix))
        return tuple(names)

    def hover(self, source: str, line: int, column: int) -> LspHover | None:
        model = self._model(source)
        name = _word_at(source, line, column)
        symbol = model.global_symbols.get(name)
        if symbol is None:
            return None
        type_name = self._type_name(symbol)
        return LspHover(name, f"{symbol.kind}: {type_name}")

    def definition(self, source: str, line: int, column: int) -> LspDefinition | None:
        model = self._model(source)
        name = _word_at(source, line, column)
        symbol = model.global_symbols.get(name)
        if symbol is None or symbol.location is None:
            return None
        return LspDefinition(name, LspPosition(symbol.location.line, symbol.location.column))

    def symbol_info(self, source: str) -> tuple[LspSymbol, ...]:
        return self.snapshot(source).symbols

    @staticmethod
    def _model(source: str):
        tokens = Lexer(source).tokenize()
        program = Parser(tokens).parse()
        return SemanticAnalyzer().analyze(program)

    @staticmethod
    def _type_name(symbol: Symbol) -> str:
        if symbol.type_spec is not None:
            return symbol.type_spec.display()
        return symbol.type_kind.value

    @classmethod
    def _to_lsp_symbol(cls, symbol: Symbol) -> LspSymbol:
        location = symbol.location
        return LspSymbol(
            name=symbol.name,
            kind=symbol.kind,
            type_name=cls._type_name(symbol),
            line=location.line if location is not None else None,
            column=location.column if location is not None else None,
        )


def _word_at(source: str, line: int, column: int) -> str:
    """1-based source konumundaki tanımlayıcıyı host-independent biçimde bulur."""

    if line < 1 or column < 1:
        return ""
    lines = source.splitlines()
    if line > len(lines):
        return ""
    text = lines[line - 1]
    index = min(column - 1, len(text))

    def is_ident(char: str) -> bool:
        return char == "_" or char.isalnum()

    if index == len(text) or (index < len(text) and not is_ident(text[index])):
        index -= 1
    if index < 0 or not is_ident(text[index]):
        return ""

    start = index
    end = index + 1
    while start > 0 and is_ident(text[start - 1]):
        start -= 1
    while end < len(text) and is_ident(text[end]):
        end += 1
    return text[start:end]
