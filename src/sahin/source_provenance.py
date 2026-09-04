from __future__ import annotations

from dataclasses import dataclass
import json

from .ast_nodes import (
    Assignment,
    Binary,
    Binding,
    Call,
    Command,
    Declaration,
    ExpressionStatement,
    ForEach,
    IfStatement,
    MatchStatement,
    Member,
    Pipeline,
    Predicate,
    Program,
    RangeExpression,
    TryStatement,
    Unary,
    Write,
)
from .ir import IRFlow, IRProgram
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
    flow_name: str | None = None

    def canonical(self) -> str:
        payload: dict[str, object] = {
            "column": self.column,
            "instruction": self.instruction_index,
            "kind": self.kind,
            "line": self.line,
        }
        # Top-level provenance canonical sözleşmesini byte-byte koru; yalnız flow
        # provenance'ında ayrı instruction index uzayını açıkça adlandır.
        if self.flow_name is not None:
            payload["flow"] = self.flow_name
        return json.dumps(
            payload,
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


def _call_sites_expression(expression, sites: list[tuple[str, int, int]]) -> None:
    if isinstance(expression, Call):
        # IR lowering önce argümanları, sonra call instruction'ını üretir.
        for argument in expression.arguments:
            _call_sites_expression(argument, sites)
        if expression.location is not None and hasattr(expression.callee, "value"):
            sites.append((expression.callee.value, expression.location.line, expression.location.column))
        return
    if isinstance(expression, Binary):
        _call_sites_expression(expression.left, sites)
        _call_sites_expression(expression.right, sites)
        return
    if isinstance(expression, Unary):
        _call_sites_expression(expression.operand, sites)
        return
    if isinstance(expression, Predicate):
        _call_sites_expression(expression.expression, sites)
        return
    if isinstance(expression, Member):
        _call_sites_expression(expression.target, sites)
        return
    if isinstance(expression, RangeExpression):
        _call_sites_expression(expression.start, sites)
        _call_sites_expression(expression.end, sites)
        return
    if isinstance(expression, Pipeline):
        _call_sites_expression(expression.source, sites)
        for stage in expression.stages:
            for argument in stage.arguments[:1]:
                _call_sites_expression(argument, sites)


def _binary_sites_statement(
    statement,
    sites: list[tuple[str, int, int]],
    *,
    descend_declarations: bool = False,
) -> None:
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
            _binary_sites_statement(item, sites, descend_declarations=descend_declarations)
        for item in statement.else_body:
            _binary_sites_statement(item, sites, descend_declarations=descend_declarations)
    elif isinstance(statement, ForEach):
        _binary_sites_expression(statement.iterable, sites)
        for item in statement.body:
            _binary_sites_statement(item, sites, descend_declarations=descend_declarations)
    elif isinstance(statement, MatchStatement):
        _binary_sites_expression(statement.subject, sites)
        for case in statement.cases:
            _binary_sites_expression(case.pattern, sites)
            _binary_sites_statement(case.statement, sites, descend_declarations=descend_declarations)
    elif isinstance(statement, TryStatement):
        for item in statement.body:
            _binary_sites_statement(item, sites, descend_declarations=descend_declarations)
        for item in statement.except_body:
            _binary_sites_statement(item, sites, descend_declarations=descend_declarations)
    elif isinstance(statement, Command):
        if statement.subject is not None:
            _binary_sites_expression(statement.subject, sites)
        for argument in statement.arguments:
            _binary_sites_expression(argument, sites)
        for item in statement.body:
            _binary_sites_statement(item, sites, descend_declarations=descend_declarations)
    elif isinstance(statement, Declaration) and descend_declarations:
        if statement.inline_expression is not None:
            _binary_sites_expression(statement.inline_expression, sites)
        for item in statement.body:
            _binary_sites_statement(item, sites, descend_declarations=True)


def _call_sites_statement(
    statement,
    sites: list[tuple[str, int, int]],
    *,
    descend_declarations: bool = False,
) -> None:
    if isinstance(statement, Assignment):
        _call_sites_expression(statement.expression, sites)
    elif isinstance(statement, Binding):
        _call_sites_expression(statement.source, sites)
    elif isinstance(statement, Write):
        _call_sites_expression(statement.expression, sites)
    elif isinstance(statement, ExpressionStatement):
        _call_sites_expression(statement.expression, sites)
    elif isinstance(statement, IfStatement):
        _call_sites_expression(statement.condition, sites)
        for item in statement.body:
            _call_sites_statement(item, sites, descend_declarations=descend_declarations)
        for item in statement.else_body:
            _call_sites_statement(item, sites, descend_declarations=descend_declarations)
    elif isinstance(statement, ForEach):
        _call_sites_expression(statement.iterable, sites)
        for item in statement.body:
            _call_sites_statement(item, sites, descend_declarations=descend_declarations)
    elif isinstance(statement, MatchStatement):
        _call_sites_expression(statement.subject, sites)
        for case in statement.cases:
            _call_sites_expression(case.pattern, sites)
            _call_sites_statement(case.statement, sites, descend_declarations=descend_declarations)
    elif isinstance(statement, TryStatement):
        for item in statement.body:
            _call_sites_statement(item, sites, descend_declarations=descend_declarations)
        for item in statement.except_body:
            _call_sites_statement(item, sites, descend_declarations=descend_declarations)
    elif isinstance(statement, Command):
        if statement.subject is not None:
            _call_sites_expression(statement.subject, sites)
        # Referans runtime ve IR Command/pipe dilimlerinde yalnız gözlemlenebilir ilk
        # argüman değerlendirildiği yerlerde provenance üretmek güvenlidir.
        for argument in statement.arguments[:1]:
            _call_sites_expression(argument, sites)
        for item in statement.body:
            _call_sites_statement(item, sites, descend_declarations=descend_declarations)
    elif isinstance(statement, Declaration) and descend_declarations:
        if statement.inline_expression is not None:
            _call_sites_expression(statement.inline_expression, sites)
        for item in statement.body:
            _call_sites_statement(item, sites, descend_declarations=True)


def _match_sites(
    sites: list[tuple[str, int, int]],
    instructions,
    *,
    flow_name: str | None,
) -> list[SourceProvenance]:
    result: list[SourceProvenance] = []
    search_from = 0
    for operator, line, column in sites:
        matched_index = None
        for index in range(search_from, len(instructions)):
            instruction = instructions[index]
            if instruction.opcode == "binary" and len(instruction.operands) == 3 and instruction.operands[0] == operator:
                matched_index = index
                break
        if matched_index is None:
            scope = flow_name or "<ana>"
            raise SourceProvenanceError(
                f"Kaynak binary provenance IR ile eşleştirilemedi: {operator!r} satır {line}, sütun {column}, kapsam {scope}."
            )
        result.append(SourceProvenance(matched_index, line, column, "binary", flow_name))
        search_from = matched_index + 1
    return result


def _match_call_sites(
    sites: list[tuple[str, int, int]],
    instructions,
    *,
    flow_name: str | None,
) -> list[SourceProvenance]:
    result: list[SourceProvenance] = []
    search_from = 0
    for source_name, line, column in sites:
        ir_name = f"@akış:{source_name}"
        matched_index = None
        for index in range(search_from, len(instructions)):
            instruction = instructions[index]
            if instruction.opcode == "call" and instruction.operands and instruction.operands[0] == ir_name:
                matched_index = index
                break
        if matched_index is None:
            scope = flow_name or "<ana>"
            raise SourceProvenanceError(
                f"Kaynak call-site provenance IR ile eşleştirilemedi: {source_name!r} satır {line}, sütun {column}, kapsam {scope}."
            )
        result.append(SourceProvenance(matched_index, line, column, "call", flow_name))
        search_from = matched_index + 1
    return result


def _flow_by_name(program: IRProgram, source_name: str) -> IRFlow:
    ir_name = f"@akış:{source_name}"
    matches = [flow for flow in program.flows if flow.name == ir_name]
    if len(matches) != 1:
        raise SourceProvenanceError(
            f"Kaynak akış provenance için tek bir IRFlow bekleniyordu: {source_name!r}."
        )
    return matches[0]


def build_binary_source_provenance(source: str, program: IRProgram) -> tuple[SourceProvenance, ...]:
    """Kaynak Binary düğümlerini top-level ve IRFlow instruction uzaylarına deterministik bağlar."""
    ast: Program = parse(tokenize(source))

    top_sites: list[tuple[str, int, int]] = []
    for statement in ast.statements:
        if not isinstance(statement, Declaration):
            _binary_sites_statement(statement, top_sites)

    result = _match_sites(top_sites, program.instructions, flow_name=None)

    for statement in ast.statements:
        if not isinstance(statement, Declaration) or statement.kind != "akış" or not statement.name:
            continue
        flow_sites: list[tuple[str, int, int]] = []
        if statement.inline_expression is not None:
            _binary_sites_expression(statement.inline_expression, flow_sites)
        for item in statement.body:
            _binary_sites_statement(item, flow_sites, descend_declarations=True)
        flow = _flow_by_name(program, statement.name)
        result.extend(_match_sites(flow_sites, flow.instructions, flow_name=flow.name))

    return tuple(result)


def build_call_source_provenance(source: str, program: IRProgram) -> tuple[SourceProvenance, ...]:
    """Doğrudan `akış` çağrılarını çağıran instruction uzayındaki kaynak konumuna bağlar."""
    ast: Program = parse(tokenize(source))
    top_sites: list[tuple[str, int, int]] = []
    for statement in ast.statements:
        if not isinstance(statement, Declaration):
            _call_sites_statement(statement, top_sites)
    result = _match_call_sites(top_sites, program.instructions, flow_name=None)

    for statement in ast.statements:
        if not isinstance(statement, Declaration) or statement.kind != "akış" or not statement.name:
            continue
        flow_sites: list[tuple[str, int, int]] = []
        if statement.inline_expression is not None:
            _call_sites_expression(statement.inline_expression, flow_sites)
        for item in statement.body:
            _call_sites_statement(item, flow_sites, descend_declarations=True)
        flow = _flow_by_name(program, statement.name)
        result.extend(_match_call_sites(flow_sites, flow.instructions, flow_name=flow.name))
    return tuple(result)


def build_source_provenance(source: str, program: IRProgram) -> tuple[SourceProvenance, ...]:
    """Hata payload ABI için doğrulanmış binary ve call-site provenance kanıtını üretir."""
    return (*build_binary_source_provenance(source, program), *build_call_source_provenance(source, program))
