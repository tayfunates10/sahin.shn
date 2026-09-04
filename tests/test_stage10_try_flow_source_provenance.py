import json

from sahin.native_backend import build_native_plan_from_source
from sahin.wasm_backend import build_wasm_plan_from_source


SOURCE = '''akış böl
    dene
        yaz 1 / 0
    olmazsa hata
        yaz hata
    ver yok

böl
'''


def test_flow_binary_provenance_uses_separate_instruction_index_space():
    wasm = build_wasm_plan_from_source(SOURCE)
    native = build_native_plan_from_source(SOURCE)

    assert wasm.source_provenance == native.source_provenance
    flow_sites = [site for site in wasm.source_provenance if site.flow_name == "@akış:böl"]
    assert len(flow_sites) == 1
    site = flow_sites[0]
    assert site.kind == "binary"
    assert site.line == 3
    flow = next(item for item in wasm.flows if item.name == "@akış:böl")
    assert flow.instructions[site.instruction_index].opcode == "binary"
    assert flow.instructions[site.instruction_index].operands[0] == "/"


def test_flow_provenance_is_part_of_adapter_canonical_evidence_without_capability_growth():
    wasm = build_wasm_plan_from_source(SOURCE)
    native = build_native_plan_from_source(SOURCE)
    wasm_payload = json.loads(wasm.canonical())
    native_payload = json.loads(native.canonical())

    assert wasm.imports == ()
    assert native.capabilities == ()
    assert wasm_payload["source_provenance"] == native_payload["source_provenance"]
    flow_evidence = [item for item in wasm_payload["source_provenance"] if item.get("flow") == "@akış:böl"]
    assert len(flow_evidence) == 1
    assert flow_evidence[0]["line"] == 3
    assert flow_evidence[0]["kind"] == "binary"


def test_top_level_provenance_canonical_shape_remains_backward_compatible():
    source = '''dene
    yaz 1 / 0
olmazsa hata
    yaz hata
'''
    payload = json.loads(build_wasm_plan_from_source(source).canonical())
    assert len(payload["source_provenance"]) == 1
    assert "flow" not in payload["source_provenance"][0]
