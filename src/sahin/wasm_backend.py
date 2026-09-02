from __future__ import annotations

from dataclasses import dataclass
import json

from .ir import IRInstruction, IRProgram, lower_source
from .ir_control_flow import IRControlFlowError, validate_control_flow


class WasmBackendError(ValueError):
    """Şahin IR güvenli WASM adapter sözleşmesine çevrilemediğinde oluşur."""


_ALLOWED_OPCODES = frozenset({"const", "load", "unary", "binary", "store", "bind", "write", "label", "jump", "branch"})


@dataclass(frozen=True, slots=True)
class WasmAdapterPlan:
    ir_version: int
    adapter_version: int
    imports: tuple[str, ...]
    instructions: tuple[IRInstruction, ...]

    def canonical(self) -> str:
        payload = {
            "adapter_version": self.adapter_version,
            "imports": list(self.imports),
            "instructions": [json.loads(item.canonical()) for item in self.instructions],
            "ir_version": self.ir_version,
            "target": "wasm32-sahin-safe",
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _schema_error(instruction: IRInstruction, instruction_index: int, detail: str) -> None:
    raise WasmBackendError(
        f"WASM adapter geçersiz {instruction.opcode} instruction şemasını reddetti "
        f"(instruction {instruction_index}): {detail}"
    )


def _validate_temp_operand(operand: str, defined: set[str], instruction_index: int) -> None:
    if not operand.startswith("%"):
        raise WasmBackendError(f"WASM adapter geçici değer beklenen operandı reddetti: {operand} (instruction {instruction_index}).")
    if operand not in defined:
        raise WasmBackendError(f"WASM adapter tanımsız geçici değer kullanımı reddetti: {operand} (instruction {instruction_index}).")


def _validate_non_temp_operand(instruction: IRInstruction, operand: str, instruction_index: int, role: str, *, allow_percent_operator: bool = False) -> None:
    is_reserved_temp_syntax = operand.startswith("%") and not (allow_percent_operator and operand == "%")
    if not operand or is_reserved_temp_syntax:
        _schema_error(instruction, instruction_index, f"{role} geçici değer olamaz ve boş bırakılamaz")


def _validate_instruction_schema(instruction: IRInstruction, defined: set[str], instruction_index: int) -> None:
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
        _validate_non_temp_operand(instruction, operands[0], instruction_index, "operatör", allow_percent_operator=True)
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
    if opcode == "label":
        if len(operands) != 1 or result is not None:
            _schema_error(instruction, instruction_index, "label tam olarak 1 etiket almalı ve sonuç üretmemelidir")
        _validate_non_temp_operand(instruction, operands[0], instruction_index, "etiket")
        return
    if opcode == "jump":
        if len(operands) != 1 or result is not None:
            _schema_error(instruction, instruction_index, "jump tam olarak 1 hedef etiket almalı ve sonuç üretmemelidir")
        _validate_non_temp_operand(instruction, operands[0], instruction_index, "hedef etiket")
        return
    if opcode == "branch":
        if len(operands) != 3 or result is not None:
            _schema_error(instruction, instruction_index, "branch koşul + doğru/yanlış hedefleri almalı ve sonuç üretmemelidir")
        _validate_temp_operand(operands[0], defined, instruction_index)
        _validate_non_temp_operand(instruction, operands[1], instruction_index, "doğru hedef")
        _validate_non_temp_operand(instruction, operands[2], instruction_index, "yanlış hedef")
        return
    raise WasmBackendError(f"WASM adapter desteklenmeyen opcode'u reddetti: {opcode}")


def _validate_instruction(instruction: IRInstruction, defined: set[str], instruction_index: int) -> None:
    if instruction.opcode not in _ALLOWED_OPCODES:
        raise WasmBackendError(f"WASM adapter desteklenmeyen opcode'u reddetti: {instruction.opcode}")
    _validate_instruction_schema(instruction, defined, instruction_index)
    if instruction.result is not None:
        if not instruction.result.startswith("%"):
            raise WasmBackendError(f"WASM adapter geçersiz geçici sonuç adını reddetti: {instruction.result}")
        if instruction.result in defined:
            raise WasmBackendError(f"WASM adapter yeniden tanımlanan geçici sonucu reddetti: {instruction.result}")
        defined.add(instruction.result)


def build_wasm_plan(program: IRProgram) -> WasmAdapterPlan:
    """IR v1'i capability importu açmadan deterministik WASM adapter planına çevirir."""
    if program.version != 1:
        raise WasmBackendError(f"Desteklenmeyen Şahin IR sürümü: {program.version}")
    try:
        validate_control_flow(program)
    except IRControlFlowError as exc:
        raise WasmBackendError(f"WASM adapter control-flow sözleşmesini reddetti: {exc}") from exc

    defined: set[str] = set()
    defined_names: set[str] = set()
    for index, instruction in enumerate(program.instructions):
        _validate_instruction(instruction, defined, index)
        if instruction.opcode == "load":
            name = instruction.operands[0]
            if name not in defined_names:
                raise WasmBackendError(f"WASM adapter tanımsız isim yüklemesini reddetti: {name} (instruction {index}).")
        if instruction.opcode in {"store", "bind"}:
            defined_names.add(instruction.operands[0])

    return WasmAdapterPlan(ir_version=program.version, adapter_version=1, imports=(), instructions=program.instructions)


def build_wasm_plan_from_source(source: str) -> WasmAdapterPlan:
    """Gerçek frontend → Şahin IR → güvenli WASM adapter sınırını çalıştırır."""
    return build_wasm_plan(lower_source(source))
