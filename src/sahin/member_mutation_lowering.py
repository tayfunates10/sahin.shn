from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .ir import IRInstruction
from .member_mutation_abi import MemberMutationTarget
from .member_store_abi import validate_member_store_instruction


class MemberMutationLoweringError(ValueError):
    """Member mutation read-modify-write IR dizisi güvenle üretilemediğinde oluşur."""


@dataclass(frozen=True, slots=True)
class MemberMutationLoweringPlan:
    instructions: tuple[IRInstruction, ...]
    result_temp: str


def lower_member_mutation_kernel(
    mutation: MemberMutationTarget,
    *,
    target_temp: str,
    amount_temp: str | None,
    next_temp: Callable[[], str],
) -> MemberMutationLoweringPlan:
    """Doğrulanmış Member mutation'ı capability-siz IR read-modify-write dizisine çevirir.

    `target_temp`, son üyenin sahibi olan nesnenin daha önce tam bir kez değerlendirilmiş
    geçicisidir. Kernel target expression'ı yeniden değerlendirmez. Miktar verilmemişse
    Şahin runtime sözleşmesiyle aynı biçimde `1` üretir.
    """
    validate_member_mutation_for_lowering(mutation)
    if not target_temp.startswith("%"):
        raise MemberMutationLoweringError("Member mutation hedefi geçici bir nesne değeri olmalıdır.")
    if amount_temp is not None and not amount_temp.startswith("%"):
        raise MemberMutationLoweringError("Member mutation miktarı geçici bir değer olmalıdır.")

    member_name = mutation.path[-1]
    current = next_temp()
    if not current.startswith("%"):
        raise MemberMutationLoweringError("Temp üreticisi geçerli bir IR geçicisi üretmelidir.")

    instructions: list[IRInstruction] = [
        IRInstruction("member", (member_name, target_temp), current)
    ]

    effective_amount = amount_temp
    if effective_amount is None:
        effective_amount = next_temp()
        if not effective_amount.startswith("%"):
            raise MemberMutationLoweringError("Temp üreticisi geçerli bir IR geçicisi üretmelidir.")
        instructions.append(IRInstruction("const", ("tam:1",), effective_amount))

    result = next_temp()
    if not result.startswith("%"):
        raise MemberMutationLoweringError("Temp üreticisi geçerli bir IR geçicisi üretmelidir.")
    instructions.append(IRInstruction("binary", (mutation.operator, current, effective_amount), result))

    store = IRInstruction("member_store", (member_name, target_temp, result))
    try:
        validate_member_store_instruction(store)
    except ValueError as exc:
        raise MemberMutationLoweringError(str(exc)) from exc
    instructions.append(store)

    return MemberMutationLoweringPlan(tuple(instructions), result)


def validate_member_mutation_for_lowering(mutation: MemberMutationTarget) -> None:
    """Kernel'e yalnız doğrulanmış lvalue ABI nesnesi girmesini fail-closed doğrular."""
    if mutation.operator not in {"+", "-"}:
        raise MemberMutationLoweringError(f"Desteklenmeyen mutation operatörü: {mutation.operator!r}.")
    if not mutation.root_name:
        raise MemberMutationLoweringError("Member mutation kökü boş olamaz.")
    if not mutation.path:
        raise MemberMutationLoweringError("Member mutation yolu boş olamaz.")
    if any(not segment for segment in mutation.path):
        raise MemberMutationLoweringError("Member mutation yolunda boş alan adı olamaz.")
