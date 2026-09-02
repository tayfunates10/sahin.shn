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


def _temp_uses(instruction: IRInstruction) -> tuple[str, ...]:
    if instruction.opcode == "unary":
        return instruction.operands[1:2]
    if instruction.opcode == "binary":
        return instruction.operands[1:3]
    if instruction.opcode in {"store", "bind"}:
        return instruction.operands[1:2]
    if instruction.opcode == "write":
        return instruction.operands[0:1]
    if instruction.opcode == "branch":
        return instruction.operands[0:1]
    return ()


def validate_control_flow(program: IRProgram) -> ControlFlowSummary:
    """IR v1 control-flow ve definite-definition sözleşmesini fail-closed doğrular."""
    if program.version != 1:
        raise IRControlFlowError(f"Desteklenmeyen Şahin IR sürümü: {program.version}")

    labels: list[str] = []
    label_set: set[str] = set()
    label_indices: dict[str, int] = {}
    targets: list[str] = []
    defined_temps: set[str] = set()

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

        in_temps: list[set[str] | None] = [None] * instruction_count
        out_temps: list[set[str] | None] = [None] * instruction_count
        in_names: list[set[str] | None] = [None] * instruction_count
        out_names: list[set[str] | None] = [None] * instruction_count

        changed = True
        while changed:
            changed = False
            for index, instruction in enumerate(program.instructions):
                if index == 0:
                    incoming_temps: set[str] | None = set()
                    incoming_names: set[str] | None = set()
                else:
                    reachable = [pred for pred in predecessors[index] if out_temps[pred] is not None]
                    if not reachable:
                        incoming_temps = None
                        incoming_names = None
                    else:
                        incoming_temps = set(out_temps[reachable[0]] or ())
                        incoming_names = set(out_names[reachable[0]] or ())
                        for pred in reachable[1:]:
                            incoming_temps.intersection_update(out_temps[pred] or ())
                            incoming_names.intersection_update(out_names[pred] or ())

                outgoing_temps = None if incoming_temps is None else set(incoming_temps)
                outgoing_names = None if incoming_names is None else set(incoming_names)
                if outgoing_temps is not None and instruction.result is not None:
                    outgoing_temps.add(instruction.result)
                if outgoing_names is not None and instruction.opcode in {"store", "bind"} and instruction.operands:
                    outgoing_names.add(instruction.operands[0])

                if (
                    in_temps[index] != incoming_temps
                    or out_temps[index] != outgoing_temps
                    or in_names[index] != incoming_names
                    or out_names[index] != outgoing_names
                ):
                    in_temps[index] = incoming_temps
                    out_temps[index] = outgoing_temps
                    in_names[index] = incoming_names
                    out_names[index] = outgoing_names
                    changed = True

        for index, instruction in enumerate(program.instructions):
            incoming_temps = in_temps[index]
            for operand in _temp_uses(instruction):
                if not operand.startswith("%") or incoming_temps is None or operand not in incoming_temps:
                    raise IRControlFlowError(
                        f"Geçici değer tüm ulaşılabilir giriş yollarında tanımlı olmalıdır: {operand} (instruction {index})."
                    )
            if instruction.opcode == "load" and len(instruction.operands) == 1:
                incoming_names = in_names[index]
                name = instruction.operands[0]
                if incoming_names is None or name not in incoming_names:
                    raise IRControlFlowError(
                        f"İsim tüm ulaşılabilir giriş yollarında tanımlı olmalıdır: {name} (instruction {index})."
                    )

    return ControlFlowSummary(labels=tuple(labels), jump_targets=tuple(targets))
