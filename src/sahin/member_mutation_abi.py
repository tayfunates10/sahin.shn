from __future__ import annotations

from dataclasses import dataclass

from .ast_nodes import Command, Member, Name


class MemberMutationABIError(ValueError):
    """Member-target mutation sözleşmesi güvenle kurulamadığında oluşur."""


@dataclass(frozen=True, slots=True)
class MemberMutationTarget:
    root_name: str
    path: tuple[str, ...]
    operator: str

    def canonical(self) -> tuple[str, tuple[str, ...], str]:
        return self.root_name, self.path, self.operator


def analyze_member_mutation(command: Command) -> MemberMutationTarget:
    """`ürün.stok artır/azalt` için deterministik lvalue ABI çekirdeğini çıkarır.

    Bu çekirdek backend opcode üretmez. Yalnızca parser AST'sinin güvenli bir
    Member lvalue zinciri olduğunu kanıtlar; sonraki IR dilimi bu sözleşmeyi
    kullanarak okuma-hesaplama-yazma semantiğini kuracaktır.
    """
    if command.name not in {"artır", "azalt"}:
        raise MemberMutationABIError("Yalnız artır/azalt komutları member mutation ABI'ına girebilir.")
    if not isinstance(command.subject, Member):
        raise MemberMutationABIError("Member mutation hedefi bir Member AST düğümü olmalıdır.")
    if len(command.arguments) > 1:
        raise MemberMutationABIError("artır/azalt en fazla bir miktar argümanı kabul eder.")
    if command.arrow is not None or command.body:
        raise MemberMutationABIError("Member mutation arrow veya gövdeli komut biçimini kabul etmez.")

    path: list[str] = []
    current = command.subject
    while isinstance(current, Member):
        if not current.name:
            raise MemberMutationABIError("Member mutation alan adı boş olamaz.")
        path.append(current.name)
        current = current.target

    if not isinstance(current, Name) or not current.value:
        raise MemberMutationABIError("Member mutation kökü doğrudan adlandırılmış bir Name olmalıdır.")

    path.reverse()
    return MemberMutationTarget(
        root_name=current.value,
        path=tuple(path),
        operator="+" if command.name == "artır" else "-",
    )
