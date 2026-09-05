from __future__ import annotations

from dataclasses import dataclass

from .ir import IRInstruction


class MemberStoreABIError(ValueError):
    """Member write primitive sözleşmesi güvenle doğrulanamadığında oluşur."""


@dataclass(frozen=True, slots=True)
class MemberStoreOperation:
    member_name: str
    target_temp: str
    value_temp: str

    def instruction(self) -> IRInstruction:
        return IRInstruction(
            "member_store",
            (self.member_name, self.target_temp, self.value_temp),
        )


def validate_member_store_instruction(instruction: IRInstruction) -> MemberStoreOperation:
    """`member_store` için fail-closed backend şemasını doğrular.

    Bu primitive yalnız bir member adı, hedef object temp'i ve yeni değer temp'i alır;
    sonuç üretmez. Ana backend validator entegrasyonu sonraki dilimde yapılacaktır.
    """
    if instruction.opcode != "member_store":
        raise MemberStoreABIError("Yalnız member_store instruction'ı bu ABI ile doğrulanabilir.")
    if instruction.result is not None:
        raise MemberStoreABIError("member_store sonuç üretmemelidir.")
    if len(instruction.operands) != 3:
        raise MemberStoreABIError("member_store üye adı + hedef temp + değer temp almalıdır.")

    member_name, target_temp, value_temp = instruction.operands
    if not member_name or member_name.startswith("%"):
        raise MemberStoreABIError("member_store üye adı boş veya geçici değer biçiminde olamaz.")
    if not target_temp.startswith("%"):
        raise MemberStoreABIError("member_store hedefi tanımlı bir geçici değer olmalıdır.")
    if not value_temp.startswith("%"):
        raise MemberStoreABIError("member_store yeni değeri tanımlı bir geçici değer olmalıdır.")

    return MemberStoreOperation(member_name, target_temp, value_temp)


def apply_member_store(target: object, member_name: str, value: object) -> None:
    """Referans runtime `_set_member` davranışının backend-side saf çekirdeği."""
    if not member_name:
        raise MemberStoreABIError("Member adı boş olamaz.")
    if not isinstance(target, dict):
        raise MemberStoreABIError(f"{member_name!r} üyesi değiştirilebilir değil.")
    target[member_name] = value
