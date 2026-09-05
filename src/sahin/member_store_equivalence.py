from __future__ import annotations


class MemberStoreEquivalenceError(ValueError):
    """member_store equivalence yürütmesi güvenle uygulanamadığında oluşur."""


def apply_member_store(target: object, name: str, value: object) -> None:
    """Referans runtime ile aynı fail-closed üye yazma semantiğini uygular.

    Şahin runtime yalnızca sözlük tabanlı member owner'larını değiştirilebilir
    kabul eder. Backend equivalence yürütücüsü de aynı sınırı korumalıdır;
    string/list gibi yalnızca okunabilir member kaynaklarına sessizce yazamaz.
    """
    if not isinstance(name, str) or not name:
        raise MemberStoreEquivalenceError("member_store alan adı boş olmayan yazı olmalıdır.")
    if isinstance(target, dict):
        target[name] = value
        return
    raise MemberStoreEquivalenceError(f"{name!r} üyesi değiştirilebilir değil.")
