from __future__ import annotations

import json

import pytest

from sahin.ir import IRLoweringError
from sahin.native_backend import build_native_plan_from_source
from sahin.record_ir import lower_source_with_record_metadata
from sahin.runtime import Runtime
from sahin.lexer import tokenize
from sahin.parser import parse
from sahin.wasm_backend import build_wasm_plan_from_source


SOURCE = """kayıt Kullanıcı
    ad: yazı gerekli
    eposta: eposta gerekli benzersiz
    katılım: zaman otomatik

yaz \"hazır\"
"""


def test_record_metadata_is_carried_without_runtime_opcode_or_capability_expansion() -> None:
    bundle = lower_source_with_record_metadata(SOURCE)
    assert len(bundle.record_schemas) == 1
    schema = bundle.record_schemas[0]
    assert schema.name == "Kullanıcı"
    assert [field.name for field in schema.fields] == ["ad", "eposta", "katılım"]
    assert [field.modifiers for field in schema.fields] == [
        ("gerekli",),
        ("gerekli", "benzersiz"),
        ("otomatik",),
    ]
    assert all(instruction.opcode not in {"record", "field"} for instruction in bundle.program.instructions)

    wasm = build_wasm_plan_from_source(SOURCE)
    native = build_native_plan_from_source(SOURCE)
    assert wasm.imports == ()
    assert native.capabilities == ()
    assert wasm.record_schemas == bundle.record_schemas
    assert native.record_schemas == bundle.record_schemas
    assert wasm.instructions == native.instructions == bundle.program.instructions

    wasm_payload = json.loads(wasm.canonical())
    native_payload = json.loads(native.canonical())
    assert wasm_payload["record_schemas"] == native_payload["record_schemas"]
    assert wasm_payload["record_schemas"][0]["name"] == "Kullanıcı"


def test_record_declaration_remains_runtime_structural_noop() -> None:
    output: list[str] = []
    Runtime(output.append).execute(parse(tokenize(SOURCE)))
    assert output == ["hazır"]


def test_invalid_record_metadata_fails_before_backend_plan_is_built() -> None:
    source = """kayıt Kullanıcı
    ad: yazı gizli
"""
    with pytest.raises(IRLoweringError, match="Kayıt metadata doğrulaması başarısız"):
        lower_source_with_record_metadata(source)
    with pytest.raises(IRLoweringError, match="bilinmeyen modifier"):
        build_wasm_plan_from_source(source)
    with pytest.raises(IRLoweringError, match="bilinmeyen modifier"):
        build_native_plan_from_source(source)


def test_existing_non_record_backend_canonical_contract_does_not_gain_empty_metadata_key() -> None:
    source = 'yaz "aynı"\n'
    assert "record_schemas" not in json.loads(build_wasm_plan_from_source(source).canonical())
    assert "record_schemas" not in json.loads(build_native_plan_from_source(source).canonical())
