from __future__ import annotations

import pytest

import sahin.backend_equivalence as backend_equivalence
from sahin.backend_equivalence import BackendEquivalenceError
from sahin.ir import IRInstruction


def test_member_store_executor_resolves_operands_and_dispatches_kernel(monkeypatch) -> None:
    observed: list[tuple[object, str, object]] = []

    def fake_apply_member_store(target: object, name: str, value: object) -> None:
        observed.append((target, name, value))

    monkeypatch.setattr(backend_equivalence, "apply_member_store", fake_apply_member_store)

    result = backend_equivalence._execute(
        (
            IRInstruction("const", ('metin:\"owner\"',), "%0"),
            IRInstruction("const", ("tam:7",), "%1"),
            IRInstruction("member_store", ("stok", "%0", "%1")),
        )
    )

    assert observed == [("owner", "stok", 7)]
    assert result.state == ()
    assert result.output == ()


def test_member_store_executor_preserves_fail_closed_kernel_error() -> None:
    with pytest.raises(BackendEquivalenceError, match="değiştirilebilir değil"):
        backend_equivalence._execute(
            (
                IRInstruction("const", ('metin:\"salt-okunur\"',), "%0"),
                IRInstruction("const", ("tam:7",), "%1"),
                IRInstruction("member_store", ("stok", "%0", "%1")),
            )
        )
