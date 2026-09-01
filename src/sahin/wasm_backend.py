from __future__ import annotations

from dataclasses import dataclass
import json

from .ir import IRInstruction, IRProgram, lower_source


class WasmBackendError(ValueError):
    """Şahin IR güvenli WASM adapter sözleşmesine çevrilemediğinde oluşur."""


_ALLOWED_OPCODES = frozenset({"const", "load", "unary", "binary", "store", "bind", "write"})


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


def _validate_temp_operand(operand: str, defined: set[str], instruction_index: int) -> None:
    if operand.startswith("%") and operand not in defined:
        raise WasmBackendError(
            f"WASM adapter tanımsız geçici değer kullanımı reddetti: {operand} (instruction {instruction_index})."
        )


def _validate_instruction(instruction: IRInstruction, defined: set[str], instruction_index: int) -> None:
    if instruction.opcode not in _ALLOWED_OPCODES:
        raise WasmBackendError(f"WASM adapter desteklenmeyen opcode'u reddetti: {instruction.opcode}")

    for operand in instruction.operands:
        _validate_temp_operand(operand, defined, instruction_index)

    if instruction.result is not None:
        if not instruction.result.startswith("%"):
            raise WasmBackendError(
                f"WASM adapter geçersiz geçici sonuç adını reddetti: {instruction.result}"
            )
        if instruction.result in defined:
            raise WasmBackendError(
                f"WASM adapter yeniden tanımlanan geçici sonucu reddetti: {instruction.result}"
            )
        defined.add(instruction.result)


def build_wasm_plan(program: IRProgram) -> WasmAdapterPlan:
    """IR v1'i capability importu açmadan deterministik WASM adapter planına çevirir."""
    if program.version != 1:
        raise WasmBackendError(f"Desteklenmeyen Şahin IR sürümü: {program.version}")

    defined: set[str] = set()
    for index, instruction in enumerate(program.instructions):
        _validate_instruction(instruction, defined, index)

    # Aşama 10'un bu diliminde host capability importları bilinçli olarak kapalıdır.
    # Dosya/ağ/süreç gibi yetkiler açık bir ABI ve capability politikası gelene kadar
    # adapter planına sessizce eklenmez.
    return WasmAdapterPlan(
        ir_version=program.version,
        adapter_version=1,
        imports=(),
        instructions=program.instructions,
    )


def build_wasm_plan_from_source(source: str) -> WasmAdapterPlan:
    """Gerçek frontend → Şahin IR → güvenli WASM adapter sınırını çalıştırır."""
    return build_wasm_plan(lower_source(source))
