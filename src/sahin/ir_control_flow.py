from __future__ import annotations

from dataclasses import dataclass

from .ir import IRInstruction, IRProgram


class IRControlFlowError(ValueError):
    """Şahin IR control-flow sözleşmesi ihlal edildiğinde oluşur."""


CONTROL_FLOW_OPCODES = frozenset({"label", "jump", "branch"})
NON_CONTROL_FLOW_OPCODES = frozenset({"const", "load", "unary", "binary", "store", "bind", "write"})
KNOWN_OPCODES = CONTROL_FLOW_OPCODES | NON_CONTROL_FLOW_OPCODES


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
    label_indices: dict[str, int] = {}
    targets: list[str] = []
    defined_temps: set[str] = set()
    temp_definition_index: dict[str, int] = {}

    for index, instruction in enumerate(program.instructions):
        opcode = instruction.opcode

        if opcode not in KNOWN_OPCODES:
            raise IRControlFlowError(
                f"Bilinmeyen IR opcode fail-closed reddedildi: {opcode!r} (instruction {index})."
            )

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
            label_indices[label] = index
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
            if not condition.startswith("%"):
                raise IRControlFlowError(
                    f"branch geçici bir koşul bekler: {condition} (instruction {index})."
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
            temp_definition_index[instruction.result] = index

    missing = tuple(target for target in targets if target not in label_set)
    if missing:
        raise IRControlFlowError(
            "Tanımsız control-flow hedefi reddedildi: " + ", ".join(missing)
        )

    instruction_count = len(program.instructions)
    if instruction_count:
        successors: list[set[int]] = [set() for _ in range(instruction_count)]
        predecessors: list[set[int]] = [set() for _ in range(instruction_count)]

        for index, instruction in enumerate(program.instructions):
            if instruction.opcode == "jump":
                successors[index].add(label_indices[instruction.operands[0]])
            elif instruction.opcode == "branch":
                successors[index].add(label_indices[instruction.operands[1]])
                successors[index].add(label_indices[instruction.operands[2]])
            elif index + 1 < instruction_count:
                successors[index].add(index + 1)

        for source, target_indices in enumerate(successors):
            for target in target_indices:
                predecessors[target].add(source)

        in_defs: list[set[str] | None] = [None for _ in range(instruction_count)]
        out_defs: list[set[str] | None] = [None for _ in range(instruction_count)]
        in_defs[0] = set()

        changed = True
        while changed:
            changed = False
            for index, instruction in enumerate(program.instructions):
                if index == 0:
                    incoming = set()
                else:
                    reachable_predecessors = [
                        out_defs[pred] for pred in predecessors[index] if out_defs[pred] is not None
                    ]
                    if not reachable_predecessors:
                        incoming = None
                    else:
                        incoming = set(reachable_predecessors[0])
                        for pred_defs in reachable_predecessors[1:]:
                            incoming.intersection_update(pred_defs)

                outgoing = None if incoming is None else set(incoming)
                if outgoing is not None and instruction.result is not None:
                    outgoing.add(instruction.result)

                if in_defs[index] != incoming or out_defs[index] != outgoing:
                    in_defs[index] = incoming
                    out_defs[index] = outgoing
                    changed = True

        for index, instruction in enumerate(program.instructions):
            if instruction.opcode != "branch":
                continue
            condition = instruction.operands[0]
            incoming = in_defs[index]
            if condition not in defined_temps or incoming is None or condition not in incoming:
                raise IRControlFlowError(
                    f"branch koşulu tüm ulaşılabilir giriş yollarında tanımlı olmalıdır: {condition} (instruction {index})."
                )

    return ControlFlowSummary(labels=tuple(labels), jump_targets=tuple(targets))
