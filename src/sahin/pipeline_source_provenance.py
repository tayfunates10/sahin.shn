from __future__ import annotations

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
from .source_provenance import SourceProvenance, SourceProvenanceError


def _pipeline_sites_expression(expression, sites: list[tuple[str, int, int]]) -> None:
    if isinstance(expression, Pipeline):
        _pipeline_sites_expression(expression.source, sites)
        for stage in expression.stages:
            # Referans runtime/lowering yalnız ilk stage argümanını değerlendirir.
            if stage.arguments:
                _pipeline_sites_expression(stage.arguments[0], sites)
            if stage.location is not None:
                sites.append((stage.name, stage.location.line, stage.location.column))
        return
    if isinstance(expression, Binary):
        _pipeline_sites_expression(expression.left, sites)
        _pipeline_sites_expression(expression.right, sites)
    elif isinstance(expression, Unary):
        _pipeline_sites_expression(expression.operand, sites)
    elif isinstance(expression, Predicate):
        _pipeline_sites_expression(expression.expression, sites)
    elif isinstance(expression, Member):
        _pipeline_sites_expression(expression.target, sites)
    elif isinstance(expression, Call):
        _pipeline_sites_expression(expression.callee, sites)
        for argument in expression.arguments:
            _pipeline_sites_expression(argument, sites)
    elif isinstance(expression, RangeExpression):
        _pipeline_sites_expression(expression.start, sites)
        _pipeline_sites_expression(expression.end, sites)


def _pipeline_sites_statement(statement, sites: list[tuple[str, int, int]], *, descend_declarations: bool = False) -> None:
    if isinstance(statement, Assignment):
        _pipeline_sites_expression(statement.expression, sites)
    elif isinstance(statement, Binding):
        _pipeline_sites_expression(statement.source, sites)
    elif isinstance(statement, Write):
        _pipeline_sites_expression(statement.expression, sites)
    elif isinstance(statement, ExpressionStatement):
        _pipeline_sites_expression(statement.expression, sites)
    elif isinstance(statement, IfStatement):
        _pipeline_sites_expression(statement.condition, sites)
        for item in statement.body:
            _pipeline_sites_statement(item, sites, descend_declarations=descend_declarations)
        for item in statement.else_body:
            _pipeline_sites_statement(item, sites, descend_declarations=descend_declarations)
    elif isinstance(statement, ForEach):
        _pipeline_sites_expression(statement.iterable, sites)
        for item in statement.body:
            _pipeline_sites_statement(item, sites, descend_declarations=descend_declarations)
    elif isinstance(statement, MatchStatement):
        _pipeline_sites_expression(statement.subject, sites)
        for case in statement.cases:
            _pipeline_sites_expression(case.pattern, sites)
            _pipeline_sites_statement(case.statement, sites, descend_declarations=descend_declarations)
    elif isinstance(statement, TryStatement):
        for item in statement.body:
            _pipeline_sites_statement(item, sites, descend_declarations=descend_declarations)
        for item in statement.except_body:
            _pipeline_sites_statement(item, sites, descend_declarations=descend_declarations)
    elif isinstance(statement, Command):
        if statement.subject is not None:
            _pipeline_sites_expression(statement.subject, sites)
        for argument in statement.arguments[:1]:
            _pipeline_sites_expression(argument, sites)
        for item in statement.body:
            _pipeline_sites_statement(item, sites, descend_declarations=descend_declarations)
    elif isinstance(statement, Declaration) and descend_declarations:
        if statement.inline_expression is not None:
            _pipeline_sites_expression(statement.inline_expression, sites)
        for item in statement.body:
            _pipeline_sites_statement(item, sites, descend_declarations=True)


def _match_pipeline_sites(sites: list[tuple[str, int, int]], instructions, *, flow_name: str | None) -> list[SourceProvenance]:
    result: list[SourceProvenance] = []
    search_from = 0
    for stage_name, line, column in sites:
        matched_index = None
        for index in range(search_from, len(instructions)):
            instruction = instructions[index]
            if instruction.opcode == "pipeline" and instruction.operands and instruction.operands[0] == stage_name:
                matched_index = index
                break
        if matched_index is None:
            scope = flow_name or "<ana>"
            raise SourceProvenanceError(
                f"Kaynak pipeline provenance IR ile eşleştirilemedi: {stage_name!r} satır {line}, sütun {column}, kapsam {scope}."
            )
        result.append(SourceProvenance(matched_index, line, column, "pipeline", flow_name))
        search_from = matched_index + 1
    return result


def _flow_by_name(program: IRProgram, source_name: str) -> IRFlow:
    ir_name = f"@akış:{source_name}"
    matches = [flow for flow in program.flows if flow.name == ir_name]
    if len(matches) != 1:
        raise SourceProvenanceError(f"Kaynak pipeline provenance için tek bir IRFlow bekleniyordu: {source_name!r}.")
    return matches[0]


def build_pipeline_source_provenance(source: str, program: IRProgram) -> tuple[SourceProvenance, ...]:
    """Pipeline stage'lerini top-level ve IRFlow instruction uzaylarına deterministik bağlar."""
    ast: Program = parse(tokenize(source))
    top_sites: list[tuple[str, int, int]] = []
    for statement in ast.statements:
        if not isinstance(statement, Declaration):
            _pipeline_sites_statement(statement, top_sites)
    result = _match_pipeline_sites(top_sites, program.instructions, flow_name=None)

    for statement in ast.statements:
        if not isinstance(statement, Declaration) or statement.kind != "akış" or not statement.name:
            continue
        flow_sites: list[tuple[str, int, int]] = []
        if statement.inline_expression is not None:
            _pipeline_sites_expression(statement.inline_expression, flow_sites)
        for item in statement.body:
            _pipeline_sites_statement(item, flow_sites, descend_declarations=True)
        flow = _flow_by_name(program, statement.name)
        result.extend(_match_pipeline_sites(flow_sites, flow.instructions, flow_name=flow.name))

    return tuple(result)
