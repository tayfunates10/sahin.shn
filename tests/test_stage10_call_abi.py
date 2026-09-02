from __future__ import annotations

import pytest

from sahin.backend_equivalence import compare_source
from sahin.ir import IRFlow, IRInstruction, IRLoweringError, IRProgram, lower_source
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
    validate_control_flow(IRProgram(version=1, instructions=flow.instructions), predefined_names=flow.parameters)


def test_flow_without_explicit_return_gets_single_reachable_implicit_yok_return():
    source = """akış sessiz x
    y = x
sonuç = sessiz(3)
"""
    flow = lower_source(source).flows[0]
    returns = [item for item in flow.instructions if item.opcode == "return"]
    assert len(returns) == 1
    assert any(item.opcode == "const" and item.operands == ("yok:null",) for item in flow.instructions)
    validate_control_flow(IRProgram(version=1, instructions=flow.instructions), predefined_names=flow.parameters)


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


def test_backends_accept_validated_flow_call_abi_without_opening_capabilities():
    source = """akış iki_katı x
    ver x * 2
sonuç = iki_katı(3)
"""
    program = lower_source(source)
    wasm = build_wasm_plan(program)
    native = build_native_plan(program)
    assert wasm.flows == program.flows
    assert native.flows == program.flows
    assert wasm.imports == ()
    assert native.capabilities == ()
    assert '"flows"' in wasm.canonical()
    assert '"flows"' in native.canonical()


def test_flow_call_equivalence_preserves_parameter_return_and_capture_semantics():
    source = """çarpan = 3
akış katla x
    ver x * çarpan
sonuç = katla(4)
yaz sonuç
"""
    report = compare_source(source)
    assert report.equivalent
    assert report.reference.state == (("sonuç", 12), ("çarpan", 3))
    assert report.reference.output == ("12",)


def test_flow_call_equivalence_preserves_assignment_to_lexical_capture():
    source = """sayaç = 1
akış artır x
    sayaç = sayaç + x
    ver sayaç
sonuç = artır(2)
yaz sayaç
yaz sonuç
"""
    report = compare_source(source)
    assert report.equivalent
    assert report.reference.state == (("sayaç", 3), ("sonuç", 3))
    assert report.reference.output == ("3", "3")


def test_backends_reject_unknown_call_target_and_wrong_arity_fail_closed():
    flow = IRFlow(
        name="@akış:f",
        parameters=("x",),
        parameter_types=(None,),
        return_type=None,
        captures=(),
        instructions=(IRInstruction("load", ("x",), "%0"), IRInstruction("return", ("%0",))),
    )
    unknown = IRProgram(version=1, instructions=(IRInstruction("call", ("@akış:yok",), "%0"),), flows=(flow,))
    wrong_arity = IRProgram(version=1, instructions=(IRInstruction("call", ("@akış:f",), "%0"),), flows=(flow,))
    with pytest.raises(WasmBackendError, match="bilinmeyen call hedefi"):
        build_wasm_plan(unknown)
    with pytest.raises(NativeBackendError, match="bilinmeyen call hedefi"):
        build_native_plan(unknown)
    with pytest.raises(WasmBackendError, match="argüman sayısını reddetti"):
        build_wasm_plan(wrong_arity)
    with pytest.raises(NativeBackendError, match="argüman sayısını reddetti"):
        build_native_plan(wrong_arity)


def test_backends_reject_flow_with_reachable_fallthrough():
    flow = IRFlow(
        name="@akış:bozuk",
        parameters=(),
        parameter_types=(),
        return_type=None,
        captures=(),
        instructions=(),
    )
    program = IRProgram(
        version=1,
        instructions=(IRInstruction("call", (flow.name,), "%0"),),
        flows=(flow,),
    )
    with pytest.raises(WasmBackendError, match="dönüş üretmeden sonlanabilen"):
        build_wasm_plan(program)
    with pytest.raises(NativeBackendError, match="dönüş üretmeden sonlanabilen"):
        build_native_plan(program)


def test_backends_reject_call_when_required_capture_is_not_definitely_defined():
    flow = IRFlow(
        name="@akış:yakala",
        parameters=(),
        parameter_types=(),
        return_type=None,
        captures=("eksik",),
        instructions=(IRInstruction("load", ("eksik",), "%0"), IRInstruction("return", ("%0",))),
    )
    program = IRProgram(
        version=1,
        instructions=(IRInstruction("call", (flow.name,), "%0"),),
        flows=(flow,),
    )
    with pytest.raises(WasmBackendError, match="lexical capture.*tanımlı değil"):
        build_wasm_plan(program)
    with pytest.raises(NativeBackendError, match="lexical capture.*tanımlı değil"):
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
