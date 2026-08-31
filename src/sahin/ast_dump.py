from __future__ import annotations

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
    TryStatement,
    Unary,
    Write,
)


def dump_ast(node: object) -> str:
    """AST'yi test/geliştirici amaçlı kararlı ve konumdan bağımsız metne çevirir."""

    lines: list[str] = []
    _emit(node, lines, 0)
    return "\n".join(lines) + "\n"


def _emit(node: object, lines: list[str], depth: int) -> None:
    pad = "  " * depth

    if isinstance(node, Program):
        lines.append(f"{pad}Program")
        for statement in node.statements:
            _emit(statement, lines, depth + 1)
        return

    if isinstance(node, Declaration):
        suffix = f" {node.name}" if node.name else ""
        lines.append(f"{pad}Declaration({node.kind}{suffix})")
        for parameter in node.parameters:
            type_suffix = f":{parameter.type_name}" if parameter.type_name else ""
            lines.append(f"{pad}  Parameter({parameter.name}{type_suffix})")
        for item in node.header:
            _emit(item, lines, depth + 1)
        for statement in node.body:
            _emit(statement, lines, depth + 1)
        if node.inline_expression is not None:
            lines.append(f"{pad}  Inline")
            _emit(node.inline_expression, lines, depth + 2)
        return

    if isinstance(node, FieldDeclaration):
        modifiers = " " + " ".join(node.modifiers) if node.modifiers else ""
        lines.append(f"{pad}Field({node.name}:{node.type_name}{modifiers})")
        return

    if isinstance(node, Binding):
        lines.append(f"{pad}Binding({node.name})")
        _emit(node.source, lines, depth + 1)
        return

    if isinstance(node, Assignment):
        lines.append(f"{pad}Assignment({node.name})")
        _emit(node.expression, lines, depth + 1)
        return

    if isinstance(node, Write):
        lines.append(f"{pad}Write")
        _emit(node.expression, lines, depth + 1)
        return

    if isinstance(node, ForEach):
        lines.append(f"{pad}ForEach({node.name})")
        _emit(node.iterable, lines, depth + 1)
        for statement in node.body:
            _emit(statement, lines, depth + 1)
        return

    if isinstance(node, IfStatement):
        lines.append(f"{pad}If")
        _emit(node.condition, lines, depth + 1)
        lines.append(f"{pad}  Then")
        for statement in node.body:
            _emit(statement, lines, depth + 2)
        if node.else_body:
            lines.append(f"{pad}  Else")
            for statement in node.else_body:
                _emit(statement, lines, depth + 2)
        return

    if isinstance(node, MatchStatement):
        lines.append(f"{pad}Match")
        _emit(node.subject, lines, depth + 1)
        for case in node.cases:
            lines.append(f"{pad}  Case")
            _emit(case.pattern, lines, depth + 2)
            _emit(case.statement, lines, depth + 2)
        return

    if isinstance(node, TryStatement):
        error = node.error_name or "_"
        lines.append(f"{pad}Try({error})")
        for statement in node.body:
            _emit(statement, lines, depth + 1)
        lines.append(f"{pad}  Otherwise")
        for statement in node.except_body:
            _emit(statement, lines, depth + 2)
        return

    if isinstance(node, Command):
        lines.append(f"{pad}Command({node.name})")
        if node.subject is not None:
            lines.append(f"{pad}  Subject")
            _emit(node.subject, lines, depth + 2)
        for argument in node.arguments:
            _emit(argument, lines, depth + 1)
        if node.arrow is not None:
            lines.append(f"{pad}  Arrow")
            _emit(node.arrow, lines, depth + 2)
        for statement in node.body:
            _emit(statement, lines, depth + 1)
        return

    if isinstance(node, Pipeline):
        lines.append(f"{pad}Pipeline")
        _emit(node.source, lines, depth + 1)
        for stage in node.stages:
            lines.append(f"{pad}  Stage({stage.name})")
            for argument in stage.arguments:
                _emit(argument, lines, depth + 2)
        return

    if isinstance(node, Member):
        lines.append(f"{pad}Member({node.name})")
        _emit(node.target, lines, depth + 1)
        return

    if isinstance(node, Call):
        lines.append(f"{pad}Call")
        _emit(node.callee, lines, depth + 1)
        for argument in node.arguments:
            _emit(argument, lines, depth + 1)
        return

    if isinstance(node, Binary):
        lines.append(f"{pad}Binary({node.operator})")
        _emit(node.left, lines, depth + 1)
        _emit(node.right, lines, depth + 1)
        return

    if isinstance(node, Unary):
        lines.append(f"{pad}Unary({node.operator})")
        _emit(node.operand, lines, depth + 1)
        return

    if isinstance(node, Predicate):
        lines.append(f"{pad}Predicate({node.predicate})")
        _emit(node.expression, lines, depth + 1)
        return

    if isinstance(node, RangeExpression):
        lines.append(f"{pad}Range")
        _emit(node.start, lines, depth + 1)
        _emit(node.end, lines, depth + 1)
        return

    if isinstance(node, Name):
        lines.append(f"{pad}Name({node.value})")
        return

    if isinstance(node, Literal):
        lines.append(f"{pad}Literal({node.value!r})")
        return

    lines.append(f"{pad}{type(node).__name__}")
