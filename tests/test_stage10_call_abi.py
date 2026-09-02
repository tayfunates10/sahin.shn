from __future__ import annotations

import pytest

from sahin.ir import IRLoweringError, IRProgram, lower_source
from sahin.ir_control_flow import validate_control_flow
from sahin.native_backend import NativeBackendError, build_native_plan
from sahin.wasm_backend import WasmBackendError, build_wasm_plan


def test_flow_declaration_and_direct_call_lower_to_explicit_ir_abi():
    source = """akış iki_katı x
    ver x * 2
sonuç = iki_katı(3)
yaz sonuç
"""

    program = lower_source(source)

    assert len(program.flows) == 1
    flow = program.flows[0]
    assert flow.name == "@akış:iki_katı"
    assert len(flow.parameters) == 1
    assert flow.parameter_types == (None,)
    assert flow.return_type is None
    assert flow.captures == ()
    returns = [item for item in flow.instructions if item.opcode == "return"]
    assert len(returns) == 1
    assert not any(item.opcode == "const" and item.operands == ("yok:null",) for item in flow.instructions)

    calls = [item for item in program.instructions if item.opcode == "call"]
    assert len(calls) == 1
    assert calls[0].operands[0] == flow.name
    assert len(calls[0].operands) == 2
    assert calls[0].result is not None

    validate_control_flow(
        IRProgram(version=1, instructions=flow.instructions),
        predefined_names=flow.parameters,
    )


def test_flow_without_explicit_return_gets_single_reachable_implicit_yok_return():
    source = """akış sessiz x
    y = x
sonuç = sessiz(3)
"""

    flow = lower_source(source).flows[0]
    returns = [item for item in flow.instructions if item.opcode == "return"]

    assert len(returns) == 1
    assert any(item.opcode == "const" and item.operands == ("yok:null",) for item in flow.instructions)
    validate_control_flow(
        IRProgram(version=1, instructions=flow.instructions),
        predefined_names=flow.parameters,
    )


def test_flow_lexical_capture_is_explicit_and_deterministic():
    source = """çarpan = 3
akış katla x
    ver x * çarpan
sonuç = katla(4)
"""

    first = lower_source(source)
    second = lower_source(source)

    assert first.canonical() == second.canonical()
    assert first.flows[0].captures == ("çarpan",)
    validate_control_flow(
        IRProgram(version=1, instructions=first.flows[0].instructions),
        predefined_names=(*first.flows[0].parameters, *first.flows[0].captures),
    )


def test_recursive_direct_flow_call_is_predeclared_in_ir_table():
    source = """akış tekrar x
    ver tekrar(x)
sonuç = tekrar(1)
"""

    program = lower_source(source)
    flow = program.flows[0]
    nested_calls = [item for item in flow.instructions if item.opcode == "call"]

    assert len(nested_calls) == 1
    assert nested_calls[0].operands[0] == flow.name


def test_backends_fail_closed_until_flow_adapter_integration_is_implemented():
    source = """akış iki_katı x
    ver x * 2
sonuç = iki_katı(3)
"""
    program = lower_source(source)

    with pytest.raises(WasmBackendError, match="Call ABI entegrasyonu"):
        build_wasm_plan(program)
    with pytest.raises(NativeBackendError, match="Call ABI entegrasyonu"):
        build_native_plan(program)


def test_call_is_not_silently_lowered_without_callee_abi():
    source = "değer = 1\nsonuç = değer(2)\n"

    with pytest.raises(IRLoweringError, match="Call ABI"):
        lower_source(source)


def test_flow_canonical_metadata_preserves_parameter_and_return_contracts():
    source = """akış iki_katı x: sayı -> sayı
    ver x * 2
sonuç = iki_katı(3)
"""

    program = lower_source(source)
    flow = program.flows[0]

    assert flow.parameter_types == ("sayı",)
    assert flow.return_type == "sayı"
    assert '"flows"' in program.canonical()
