from __future__ import annotations

from dataclasses import dataclass

from .ir import IRInstruction, IRProgram


class IRControlFlowError(ValueError):
    """Şahin IR control-flow sözleşmesi ihlal edildiğinde oluşur."""


CONTROL_FLOW_OPCODES = frozenset({"label", "jump", "branch"})


@dataclass(frozen=True, slots=True)
class ControlFlowSummary:
    labels: tuple[str, ...]
    jump_targets: tuple[str, ...]


def _validate_label_name(name: str, instruction_index: int) -> None:
    if not name or name.startswith("%"):
        raise IRControlFlowError(
            f"Geçersiz control-flow etiketi: {name!r} (instruction {instruction_index})."
        )


def validate_control_flow(program: IRProgram) -> ControlFlowSummary:
    """IR v1 label/jump/branch yapısını deterministik ve fail-closed doğrular.

    Bu doğrulayıcı henüz backend lowering yapmaz. Aşama 10'un sonraki dilimlerinde
    WASM/native adapterlar bu sözleşmeyi tüketir. Böylece bilinmeyen veya bozuk
    control-flow instruction'ları sessizce kabul edilmez.
    """
    if program.version != 1:
        raise IRControlFlowError(f"Desteklenmeyen Şahin IR sürümü: {program.version}")

    labels: list[str] = []
    label_set: set[str] = set()
    targets: list[str] = []
    defined_temps: set[str] = set()

    for index, instruction in enumerate(program.instructions):
        opcode = instruction.opcode

        if opcode == "label":
            if len(instruction.operands) != 1 or instruction.result is not None:
                raise IRControlFlowError(
                    f"label tam olarak 1 etiket operandı almalı ve sonuç üretmemelidir (instruction {index})."
                )
            label = instruction.operands[0]
            _validate_label_name(label, index)
            if label in label_set:
                raise IRControlFlowError(
                    f"Yinelenen control-flow etiketi reddedildi: {label} (instruction {index})."
                )
            label_set.add(label)
            labels.append(label)
            continue

        if opcode == "jump":
            if len(instruction.operands) != 1 or instruction.result is not None:
                raise IRControlFlowError(
                    f"jump tam olarak 1 hedef etiketi almalı ve sonuç üretmemelidir (instruction {index})."
                )
            target = instruction.operands[0]
            _validate_label_name(target, index)
            targets.append(target)
            continue

        if opcode == "branch":
            if len(instruction.operands) != 3 or instruction.result is not None:
                raise IRControlFlowError(
                    f"branch koşul geçicisi + doğru/yanlış hedefleri almalı ve sonuç üretmemelidir (instruction {index})."
                )
            condition, true_target, false_target = instruction.operands
            if not condition.startswith("%") or condition not in defined_temps:
                raise IRControlFlowError(
                    f"branch tanımlı bir geçici koşul bekler: {condition} (instruction {index})."
                )
            _validate_label_name(true_target, index)
            _validate_label_name(false_target, index)
            targets.extend((true_target, false_target))
            continue

        if instruction.result is not None:
            if not instruction.result.startswith("%"):
                raise IRControlFlowError(
                    f"Geçersiz geçici sonuç adı: {instruction.result} (instruction {index})."
                )
            if instruction.result in defined_temps:
                raise IRControlFlowError(
                    f"Yinelenen geçici sonuç reddedildi: {instruction.result} (instruction {index})."
                )
            defined_temps.add(instruction.result)

    missing = tuple(target for target in targets if target not in label_set)
    if missing:
        raise IRControlFlowError(
            "Tanımsız control-flow hedefi reddedildi: " + ", ".join(missing)
        )

    return ControlFlowSummary(labels=tuple(labels), jump_targets=tuple(targets))
