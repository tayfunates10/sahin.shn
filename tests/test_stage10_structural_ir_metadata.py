from __future__ import annotations

import json

from sahin.structural_ir import lower_source_with_structural_metadata


def test_structural_metadata_is_carried_without_executable_opcode() -> None:
    bundle = lower_source_with_structural_metadata(
        """
uygulama Ana
    ekran Giris
        yaz \"merhaba\"
"""
    )

    assert [(item.kind, item.name) for item in bundle.declarations] == [
        ("uygulama", "Ana"),
    ]
    assert all("uygulama" not in item.canonical() for item in bundle.program.instructions)


def test_structural_metadata_canonical_is_deterministic_and_unicode_safe() -> None:
    bundle = lower_source_with_structural_metadata(
        """
görünüm Özet
    yaz \"tamam\"
"""
    )

    payload = json.loads(bundle.canonical())
    assert payload["version"] == 1
    assert payload["structural_declarations"][0] == {
        "body_arity": 1,
        "header_arity": 0,
        "kind": "görünüm",
        "name": "Özet",
    }
    assert "Özet" in bundle.canonical()
    assert "görünüm" in bundle.canonical()


def test_non_structural_program_keeps_empty_metadata_channel() -> None:
    bundle = lower_source_with_structural_metadata('x = 1\nyaz x')

    assert bundle.declarations == ()
    assert bundle.program.instructions
