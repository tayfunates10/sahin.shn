from __future__ import annotations

import pytest

from sahin.debugger import DebugStop, Debugger
from sahin.lexer import tokenize
from sahin.parser import parse


def run_debug(source: str, *, breakpoints=(), step=False):
    stops: list[DebugStop] = []
    output: list[str] = []
    debugger = Debugger(output.append, on_stop=stops.append)
    for line in breakpoints:
        debugger.add_breakpoint(line)
    if step:
        debugger.enable_step()
    values = debugger.execute(parse(tokenize(source)))
    return debugger, values, output, stops


def test_breakpoint_stops_before_statement_without_changing_runtime_result():
    source = """sayı = 1
sayı = sayı + 2
yaz sayı
"""
    _, values, output, stops = run_debug(source, breakpoints=(2,))

    assert values["sayı"] == 3
    assert output == ["3"]
    assert [(stop.reason, stop.location.line) for stop in stops] == [("breakpoint", 2)]
    assert ("sayı", "1") in stops[0].scopes[0].values


def test_step_reports_every_statement_deterministically():
    source = """a = 1
b = a + 1
yaz b
"""
    _, values, output, stops = run_debug(source, step=True)

    assert values["b"] == 2
    assert output == ["2"]
    assert [stop.location.line for stop in stops] == [1, 2, 3]
    assert [stop.reason for stop in stops] == ["step", "step", "step"]


def test_breakpoint_takes_precedence_over_step_reason():
    source = """a = 1
yaz a
"""
    _, _, _, stops = run_debug(source, breakpoints=(2,), step=True)

    assert [stop.reason for stop in stops] == ["step", "breakpoint"]


def test_scope_inspection_is_read_only_string_snapshot():
    source = """değer = 7
yaz değer
"""
    _, values, _, stops = run_debug(source, breakpoints=(2,))

    snapshot = stops[0].scopes[0]
    assert snapshot.frame_name == "<ana>"
    assert snapshot.values == (("değer", "7"),)
    assert values["değer"] == 7


def test_invalid_breakpoint_is_rejected():
    debugger = Debugger(lambda _: None)
    with pytest.raises(ValueError, match="pozitif"):
        debugger.add_breakpoint(0)
