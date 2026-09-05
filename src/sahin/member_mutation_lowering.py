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
    read_target_temp: str,
    write_target_temp: str,
    amount_temp: str | None,
    next_temp: Callable[[], str],
) -> MemberMutationLoweringPlan:
    """Doğrulanmış Member mutation için owner-order güvenli read-modify-write IR üretir.

    `read_target_temp`, alanın mevcut değerini okuyan owner'dır. `write_target_temp` ise
    miktar ifadesi ve aritmetik tamamlandıktan sonra çağıran lowerer tarafından yeniden
    değerlendirilmiş owner olmalıdır. Kernel owner ifadelerini kendisi değerlendirmez;
    böylece referans runtime'ın read -> amount -> binary -> write-owner -> member_store
    sırası üst katmanda açıkça korunabilir. Miktar verilmemişse varsayılan değer 1'dir.
    """
    validate_member_mutation_for_lowering(mutation)
    _validate_temp(read_target_temp, "Member mutation okuma hedefi")
    _validate_temp(write_target_temp, "Member mutation yazma hedefi")
    if amount_temp is not None:
        _validate_temp(amount_temp, "Member mutation miktarı")

    member_name = mutation.path[-1]
    current = next_temp()
    _validate_temp(current, "Temp üreticisi")

    instructions: list[IRInstruction] = [
        IRInstruction("member", (member_name, read_target_temp), current)
    ]

    effective_amount = amount_temp
    if effective_amount is None:
        effective_amount = next_temp()
        _validate_temp(effective_amount, "Temp üreticisi")
        instructions.append(IRInstruction("const", ("tam:1",), effective_amount))

    result = next_temp()
    _validate_temp(result, "Temp üreticisi")
    instructions.append(IRInstruction("binary", (mutation.operator, current, effective_amount), result))

    store = IRInstruction("member_store", (member_name, write_target_temp, result))
    try:
        validate_member_store_instruction(store)
    except ValueError as exc:
        raise MemberMutationLoweringError(str(exc)) from exc
    instructions.append(store)

    return MemberMutationLoweringPlan(tuple(instructions), result)


def _validate_temp(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.startswith("%"):
        raise MemberMutationLoweringError(f"{label} geçerli bir IR geçicisi olmalıdır.")


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
