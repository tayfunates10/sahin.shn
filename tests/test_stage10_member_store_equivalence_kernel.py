from __future__ import annotations

import pytest

from sahin.member_store_equivalence import MemberStoreEquivalenceError, apply_member_store


def test_member_store_equivalence_kernel_matches_runtime_dict_mutation_contract() -> None:
    target = {"stok": 10}

    apply_member_store(target, "stok", 13)

    assert target == {"stok": 13}


def test_member_store_equivalence_kernel_can_create_dict_member_like_runtime() -> None:
    target: dict[str, object] = {}

    apply_member_store(target, "stok", 1)

    assert target == {"stok": 1}


@pytest.mark.parametrize("target", ("Şahin", [1, 2], (1, 2), 7, None))
def test_member_store_equivalence_kernel_rejects_non_mutable_member_owner(target: object) -> None:
    with pytest.raises(MemberStoreEquivalenceError, match="değiştirilebilir değil"):
        apply_member_store(target, "stok", 1)


@pytest.mark.parametrize("name", ("", None, 1))
def test_member_store_equivalence_kernel_rejects_invalid_member_name(name: object) -> None:
    with pytest.raises(MemberStoreEquivalenceError, match="alan adı"):
        apply_member_store({}, name, 1)  # type: ignore[arg-type]
