from __future__ import annotations

from sahin.backend_equivalence import compare_source
from sahin.ir import lower_source
from sahin.native_backend import build_native_plan
from sahin.wasm_backend import build_wasm_plan


def test_expression_statement_direct_call_keeps_side_effect_and_discards_result():
    source = """akış yankı x
    yaz x
    ver x * 2
yankı(7)
yaz 9
"""
    program = lower_source(source)
    calls = [item for item in program.instructions if item.opcode == "call"]
    assert len(calls) == 1
    assert calls[0].result is not None
    assert not any(item.opcode == "store" and item.operands[-1] == calls[0].result for item in program.instructions)

    report = compare_source(source)
    assert report.equivalent
    assert report.reference.output == ("7", "9")


def test_expression_statement_does_not_open_backend_capabilities():
    source = """akış kimlik x
    ver x
kimlik(4)
"""
    program = lower_source(source)
    wasm = build_wasm_plan(program)
    native = build_native_plan(program)
    assert wasm.imports == ()
    assert native.capabilities == ()
