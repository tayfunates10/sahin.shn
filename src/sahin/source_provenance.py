from __future__ import annotations

from dataclasses import dataclass
import json

from .ast_nodes import (
    Assignment,
    Binary,
    Binding,
    Command,
    Declaration,
    ExpressionStatement,
    ForEach,
    IfStatement,
    MatchStatement,
    Pipeline,
    Program,
    TryStatement,
    Unary,
    Write,
    Call,
    Member,
    Predicate,
    RangeExpression,
)
from .ir import IRProgram
from .lexer import tokenize
from .parser import parse


class SourceProvenanceError(ValueError):
    """Kaynak konumu IR instruction'ına deterministik biçimde bağlanamadığında oluşur."""


@dataclass(frozen=True, slots=True)
class SourceProvenance:
    instruction_index: int
    line: int
    column: int
    kind: str

    def canonical(self) -> str:
        return json.dumps(
            {
                "column": self.column,
                "instruction": self.instruction_index,
                "kind": self.kind,
                "line": self.line,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )


def _binary_sites_expression(expression, sites: list[tuple[str, int, int]]) -> None:
    if isinstance(expression, Binary):
        _binary_sites_expression(expression.left, sites)
        _binary_sites_expression(expression.right, sites)
        if expression.operator not in {"ve", "veya"} and expression.location is not None:
            sites.append((expression.operator, expression.location.line, expression.location.column))
        return
    if isinstance(expression, Unary):
        _binary_sites_expression(expression.operand, sites)
        return
    if isinstance(expression, Predicate):
        _binary_sites_expression(expression.expression, sites)
        return
    if isinstance(expression, Member):
        _binary_sites_expression(expression.target, sites)
        return
    if isinstance(expression, Call):
        _binary_sites_expression(expression.callee, sites)
        for argument in expression.arguments:
            _binary_sites_expression(argument, sites)
        return
    if isinstance(expression, RangeExpression):
        _binary_sites_expression(expression.start, sites)
        _binary_sites_expression(expression.end, sites)
        return
    if isinstance(expression, Pipeline):
        _binary_sites_expression(expression.source, sites)
        for stage in expression.stages:
            for argument in stage.arguments:
                _binary_sites_expression(argument, sites)


def _binary_sites_statement(statement, sites: list[tuple[str, int, int]]) -> None:
    if isinstance(statement, Assignment):
        _binary_sites_expression(statement.expression, sites)
    elif isinstance(statement, Binding):
        _binary_sites_expression(statement.source, sites)
    elif isinstance(statement, Write):
        _binary_sites_expression(statement.expression, sites)
    elif isinstance(statement, ExpressionStatement):
        _binary_sites_expression(statement.expression, sites)
    elif isinstance(statement, IfStatement):
        _binary_sites_expression(statement.condition, sites)
        for item in statement.body:
            _binary_sites_statement(item, sites)
        for item in statement.else_body:
            _binary_sites_statement(item, sites)
    elif isinstance(statement, ForEach):
        _binary_sites_expression(statement.iterable, sites)
        for item in statement.body:
            _binary_sites_statement(item, sites)
    elif isinstance(statement, MatchStatement):
        _binary_sites_expression(statement.subject, sites)
        for case in statement.cases:
            _binary_sites_expression(case.pattern, sites)
            _binary_sites_statement(case.statement, sites)
    elif isinstance(statement, TryStatement):
        for item in statement.body:
            _binary_sites_statement(item, sites)
        for item in statement.except_body:
            _binary_sites_statement(item, sites)
    elif isinstance(statement, Command):
        if statement.subject is not None:
            _binary_sites_expression(statement.subject, sites)
        for argument in statement.arguments:
            _binary_sites_expression(argument, sites)
        for item in statement.body:
            _binary_sites_statement(item, sites)
    elif isinstance(statement, Declaration):
        # Flow gövdeleri ayrı IRFlow instruction dizileridir. Bu ilk ABI dilimi yalnız
        # top-level instruction provenance'ını taşır; flow provenance sonraki dilimde
        # ayrı indeks alanı ile modellenene kadar fail-closed kalır.
        return


def build_binary_source_provenance(source: str, program: IRProgram) -> tuple[SourceProvenance, ...]:
    """Kaynak Binary düğümlerini top-level IR binary instruction'larına deterministik bağlar."""
    ast: Program = parse(tokenize(source))
    sites: list[tuple[str, int, int]] = []
    for statement in ast.statements:
        _binary_sites_statement(statement, sites)

    result: list[SourceProvenance] = []
    search_from = 0
    for operator, line, column in sites:
        matched_index = None
        for index in range(search_from, len(program.instructions)):
            instruction = program.instructions[index]
            if instruction.opcode == "binary" and len(instruction.operands) == 3 and instruction.operands[0] == operator:
                matched_index = index
                break
        if matched_index is None:
            raise SourceProvenanceError(
                f"Kaynak binary provenance IR ile eşleştirilemedi: {operator!r} satır {line}, sütun {column}."
            )
        result.append(SourceProvenance(matched_index, line, column, "binary"))
        search_from = matched_index + 1
    return tuple(result)
