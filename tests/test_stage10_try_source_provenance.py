import json

from sahin.ir import lower_source
from sahin.native_backend import build_native_plan, build_native_plan_from_source
from sahin.try_backend_equivalence import compare_try_source
from sahin.wasm_backend import build_wasm_plan, build_wasm_plan_from_source


SOURCE = '''dene
    yaz 1 / 0
olmazsa hata
    yaz hata
'''


def test_from_source_plans_carry_same_binary_provenance_without_widening_capabilities():
    wasm = build_wasm_plan_from_source(SOURCE)
    native = build_native_plan_from_source(SOURCE)

    assert wasm.imports == ()
    assert native.capabilities == ()
    assert wasm.source_provenance == native.source_provenance
    assert len(wasm.source_provenance) == 1
    site = wasm.source_provenance[0]
    assert site.kind == "binary"
    assert site.line == 2
    assert site.column > 0
    assert wasm.instructions[site.instruction_index].opcode == "binary"


def test_source_provenance_is_part_of_adapter_canonical_evidence():
    wasm_payload = json.loads(build_wasm_plan_from_source(SOURCE).canonical())
    native_payload = json.loads(build_native_plan_from_source(SOURCE).canonical())

    assert wasm_payload["source_provenance"] == native_payload["source_provenance"]
    assert wasm_payload["source_provenance"][0]["line"] == 2
    assert wasm_payload["source_provenance"][0]["kind"] == "binary"


def test_manual_ir_plan_does_not_invent_source_provenance():
    program = lower_source(SOURCE)

    assert build_wasm_plan(program).source_provenance == ()
    assert build_native_plan(program).source_provenance == ()


def test_caught_binary_error_payload_matches_reference_with_source_location():
    report = compare_try_source(SOURCE)

    assert report.equivalent
    assert len(report.reference_output) == 1
    assert "Şahin çalışma hatası" in report.reference_output[0]
    assert report.reference_output == report.wasm_output == report.native_output
