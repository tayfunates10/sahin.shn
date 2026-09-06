import json

from sahin.native_backend import build_native_plan_from_source
from sahin.wasm_backend import build_wasm_plan_from_source


SOURCE = """
uygulama Mağaza
    yaz "hazır"

kayıt Ürün
    ad: yazı gerekli

x = 1
yaz x
"""


def test_native_adapter_carries_structural_and_record_metadata_without_capabilities():
    plan = build_native_plan_from_source(SOURCE)

    assert plan.capabilities == ()
    assert len(plan.record_metadata) == 1
    assert len(plan.structural_declarations) == 1
    declaration = plan.structural_declarations[0]
    assert (declaration.kind, declaration.name, declaration.header_arity, declaration.body_arity) == (
        "uygulama",
        "Mağaza",
        0,
        1,
    )

    payload = json.loads(plan.canonical())
    assert payload["structural_declarations"] == [
        {"body_arity": 1, "header_arity": 0, "kind": "uygulama", "name": "Mağaza"}
    ]
    assert payload["record_schemas"][0]["name"] == "Ürün"


def test_wasm_adapter_carries_structural_metadata_without_imports():
    plan = build_wasm_plan_from_source(SOURCE)

    assert plan.imports == ()
    assert len(plan.structural_declarations) == 1
    payload = json.loads(plan.canonical())
    assert payload["structural_declarations"][0]["kind"] == "uygulama"
    assert payload["record_schemas"][0]["name"] == "Ürün"


def test_sources_without_structural_declarations_preserve_existing_canonical_shape():
    native = json.loads(build_native_plan_from_source('yaz "ok"').canonical())
    wasm = json.loads(build_wasm_plan_from_source('yaz "ok"').canonical())

    assert "structural_declarations" not in native
    assert "structural_declarations" not in wasm
