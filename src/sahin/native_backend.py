from __future__ import annotations

from dataclasses import dataclass
import json

from .ir import IRInstruction, IRProgram, lower_source


class NativeBackendError(ValueError):
    """Şahin IR güvenli native adapter sözleşmesine çevrilemediğinde oluşur."""


_ALLOWED_OPCODES = frozenset({"const", "load", "unary", "binary", "store", "bind", "write"})


@dataclass(frozen=True, slots=True)
class NativeAdapterPlan:
    ir_version: int
    adapter_version: int
    target: str
    capabilities: tuple[str, ...]
    instructions: tuple[IRInstruction, ...]

    def canonical(self) -> str:
        payload = {
            "adapter_version": self.adapter_version,
            "capabilities": list(self.capabilities),
            "instructions": [json.loads(item.canonical()) for item in self.instructions],
            "ir_version": self.ir_version,
            "target": self.target,
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _schema_error(instruction: IRInstruction, instruction_index: int, detail: str) -> None:
    raise NativeBackendError(
        f"Native adapter geçersiz {instruction.opcode} instruction şemasını reddetti "
        f"(instruction {instruction_index}): {detail}"
    )


def _validate_non_temp_operand(
    instruction: IRInstruction,
    operand: str,
    instruction_index: int,
    role: str,
    *,
    allow_percent_operator: bool = False,
) -> None:
    is_reserved_temp_syntax = operand.startswith("%") and not (allow_percent_operator and operand == "%")
    if not operand or is_reserved_temp_syntax:
        _schema_error(instruction, instruction_index, f"{role} geçici değer olamaz ve boş bırakılamaz")


def _validate_temp_operand(operand: str, defined: set[str], instruction_index: int) -> None:
    if not operand.startswith("%"):
        raise NativeBackendError(
            f"Native adapter geçici değer beklenen operandı reddetti: {operand} (instruction {instruction_index})."
        )
    if operand not in defined:
        raise NativeBackendError(
            f"Native adapter tanımsız geçici değer kullanımı reddetti: {operand} (instruction {instruction_index})."
        )


def _validate_instruction_schema(
    instruction: IRInstruction,
    defined: set[str],
    instruction_index: int,
) -> None:
    opcode = instruction.opcode
    operands = instruction.operands
    result = instruction.result

    if opcode == "const":
        if len(operands) != 1 or result is None:
            _schema_error(instruction, instruction_index, "const tam olarak 1 literal operand ve sonuç üretmelidir")
        _validate_non_temp_operand(instruction, operands[0], instruction_index, "literal operand")
        return

    if opcode == "load":
        if len(operands) != 1 or result is None:
            _schema_error(instruction, instruction_index, "load tam olarak 1 isim operandı ve sonuç üretmelidir")
        _validate_non_temp_operand(instruction, operands[0], instruction_index, "isim operandı")
        return

    if opcode == "unary":
        if len(operands) != 2 or result is None:
            _schema_error(instruction, instruction_index, "unary operatör + 1 geçici operand ve sonuç üretmelidir")
        _validate_non_temp_operand(instruction, operands[0], instruction_index, "operatör")
        _validate_temp_operand(operands[1], defined, instruction_index)
        return

    if opcode == "binary":
        if len(operands) != 3 or result is None:
            _schema_error(instruction, instruction_index, "binary operatör + 2 geçici operand ve sonuç üretmelidir")
        _validate_non_temp_operand(
            instruction,
            operands[0],
            instruction_index,
            "operatör",
            allow_percent_operator=True,
        )
        _validate_temp_operand(operands[1], defined, instruction_index)
        _validate_temp_operand(operands[2], defined, instruction_index)
        return

    if opcode in {"store", "bind"}:
        if len(operands) != 2 or result is not None:
            _schema_error(instruction, instruction_index, f"{opcode} isim + 1 geçici operand almalı ve sonuç üretmemelidir")
        _validate_non_temp_operand(instruction, operands[0], instruction_index, "isim operandı")
        _validate_temp_operand(operands[1], defined, instruction_index)
        return

    if opcode == "write":
        if len(operands) != 1 or result is not None:
            _schema_error(instruction, instruction_index, "write tam olarak 1 geçici operand almalı ve sonuç üretmemelidir")
        _validate_temp_operand(operands[0], defined, instruction_index)
        return

    raise NativeBackendError(f"Native adapter desteklenmeyen opcode'u reddetti: {opcode}")


def _validate_instruction(instruction: IRInstruction, defined: set[str], instruction_index: int) -> None:
    if instruction.opcode not in _ALLOWED_OPCODES:
        raise NativeBackendError(f"Native adapter desteklenmeyen opcode'u reddetti: {instruction.opcode}")

    _validate_instruction_schema(instruction, defined, instruction_index)

    if instruction.result is not None:
        if not instruction.result.startswith("%"):
            raise NativeBackendError(f"Native adapter geçersiz geçici sonuç adını reddetti: {instruction.result}")
        if instruction.result in defined:
            raise NativeBackendError(f"Native adapter yeniden tanımlanan geçici sonucu reddetti: {instruction.result}")
        defined.add(instruction.result)


def build_native_plan(program: IRProgram, *, target: str = "native-sahin-safe") -> NativeAdapterPlan:
    """IR v1'i capability açmadan deterministik native adapter planına çevirir."""
    if program.version != 1:
        raise NativeBackendError(f"Desteklenmeyen Şahin IR sürümü: {program.version}")
    if target != "native-sahin-safe":
        raise NativeBackendError(f"Desteklenmeyen native hedefi: {target}")

    defined: set[str] = set()
    defined_names: set[str] = set()
    for index, instruction in enumerate(program.instructions):
        _validate_instruction(instruction, defined, index)

        if instruction.opcode == "load":
            name = instruction.operands[0]
            if name not in defined_names:
                raise NativeBackendError(
                    f"Native adapter tanımsız isim yüklemesini reddetti: {name} (instruction {index})."
                )

        if instruction.opcode in {"store", "bind"}:
            defined_names.add(instruction.operands[0])

    return NativeAdapterPlan(
        ir_version=program.version,
        adapter_version=1,
        target=target,
        capabilities=(),
        instructions=program.instructions,
    )


def build_native_plan_from_source(source: str) -> NativeAdapterPlan:
    """Gerçek frontend → Şahin IR → güvenli native adapter sınırını çalıştırır."""
    return build_native_plan(lower_source(source))
