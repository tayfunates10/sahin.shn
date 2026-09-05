from __future__ import annotations

import pytest

from sahin.native_backend import build_native_plan_from_source
from sahin.record_adapter_metadata import RecordAdapterMetadataError, validate_adapter_record_schemas
from sahin.record_metadata import RecordFieldABI, RecordSchemaABI
from sahin.wasm_backend import build_wasm_plan_from_source


SOURCE = """kayıt Kullanıcı
    ad: yazı gerekli
    eposta: eposta gerekli benzersiz
    katılım: zaman otomatik

yaz \"hazır\"
"""


def test_native_and_wasm_keep_wire_compatibility_after_canonical_validation() -> None:
    wasm = build_wasm_plan_from_source(SOURCE)
    native = build_native_plan_from_source(SOURCE)

    assert wasm.record_schemas == native.record_schemas
    assert wasm.imports == ()
    assert native.capabilities == ()
    assert wasm.record_schemas[0].fields[1].modifiers == ("gerekli", "benzersiz")


def test_adapter_boundary_rejects_unknown_modifier_fail_closed() -> None:
    schema = RecordSchemaABI(
        "Kullanıcı",
        (RecordFieldABI("ad", "yazı", ("gerekli", "gizli")),),
    )
    with pytest.raises(RecordAdapterMetadataError, match="bilinmeyen modifier"):
        validate_adapter_record_schemas((schema,))


def test_adapter_boundary_rejects_duplicate_field_fail_closed() -> None:
    schema = RecordSchemaABI(
        "Kullanıcı",
        (
            RecordFieldABI("ad", "yazı", ()),
            RecordFieldABI("ad", "yazı", ()),
        ),
    )
    with pytest.raises(RecordAdapterMetadataError, match="yinelenen alan"):
        validate_adapter_record_schemas((schema,))
