from __future__ import annotations

import json

from sahin.native_backend import build_native_plan_from_source
from sahin.record_ir_metadata import IRRecordMetadata
from sahin.wasm_backend import build_wasm_plan_from_source


SOURCE = """kayıt Ürün
    stok: tam benzersiz gerekli
    kod: yazı gerekli

yaz \"hazır\"
"""


def test_plans_store_validated_canonical_record_metadata() -> None:
    native = build_native_plan_from_source(SOURCE)
    wasm = build_wasm_plan_from_source(SOURCE)
    assert len(native.record_metadata) == len(wasm.record_metadata) == 1
    assert isinstance(native.record_metadata[0].metadata, IRRecordMetadata)
    assert native.record_metadata[0].metadata == wasm.record_metadata[0].metadata
    assert native.record_metadata[0].metadata.name == "Ürün"


def test_legacy_wire_view_remains_backward_compatible() -> None:
    native = build_native_plan_from_source(SOURCE)
    wasm = build_wasm_plan_from_source(SOURCE)
    assert native.record_schemas == tuple(item.wire_schema for item in native.record_metadata)
    assert wasm.record_schemas == tuple(item.wire_schema for item in wasm.record_metadata)
    assert native.record_schemas == wasm.record_schemas
    assert native.record_schemas[0].fields[0].modifiers == ("benzersiz", "gerekli")
    assert json.loads(native.canonical())["record_schemas"] == json.loads(wasm.canonical())["record_schemas"]


def test_non_record_plans_do_not_gain_empty_record_wire_key() -> None:
    source = 'yaz "aynı"\n'
    native = build_native_plan_from_source(source)
    wasm = build_wasm_plan_from_source(source)
    assert native.record_metadata == wasm.record_metadata == ()
    assert native.record_schemas == wasm.record_schemas == ()
    assert "record_schemas" not in json.loads(native.canonical())
    assert "record_schemas" not in json.loads(wasm.canonical())
