from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import json
from typing import Sequence

from .ir import IRInstruction, lower_source
from .lexer import tokenize
from .native_backend import build_native_plan
from .parser import parse
from .runtime import Runtime
from .wasm_backend import build_wasm_plan


class TryBackendEquivalenceError(ValueError):
    """Try/error-region adapter semantiği güvenle yürütülemediğinde oluşur."""


@dataclass(frozen=True, slots=True)
class TryEquivalenceReport:
    reference_output: tuple[str, ...]
    wasm_output: tuple[str, ...]
    native_output: tuple[str, ...]

    @property
    def equivalent(self) -> bool:
        return self.reference_output == self.wasm_output == self.native_output


def _decode_literal(encoded: str) -> object:
    if encoded == "yok:null":
        return None
    if encoded == "evet_hayır:evet":
        return True
    if encoded == "evet_hayır:hayır":
        return False
    if encoded.startswith("tam:"):
        return int(encoded[4:])
    if encoded.startswith("ondalık:"):
        return Decimal(encoded[8:])
    if encoded.startswith("metin:"):
        value = json.loads(encoded[6:])
        if not isinstance(value, str):
            raise TryBackendEquivalenceError("Metin literal'i JSON string olmalıdır.")
        return value
    raise TryBackendEquivalenceError(f"Bilinmeyen literal kodlaması: {encoded}")


def _format(value: object) -> str:
    if value is True:
        return "evet"
    if value is False:
        return "hayır"
    if value is None:
        return "yok"
    if isinstance(value, Decimal):
        return format(value, "f")
    return str(value)


def _execute(instructions: Sequence[IRInstruction]) -> tuple[str, ...]:
    labels = {
        item.operands[0]: index
        for index, item in enumerate(instructions)
        if item.opcode == "label" and len(item.operands) == 1
    }
    regions: list[tuple[int, int, int]] = []
    for index, item in enumerate(instructions):
        if item.opcode != "try_guard":
            continue
        if len(item.operands) != 2:
            raise TryBackendEquivalenceError("Geçersiz try_guard şeması.")
        handler, protected_end = item.operands
        try:
            handler_index = labels[handler]
            protected_end_index = labels[protected_end]
        except KeyError as exc:
            raise TryBackendEquivalenceError("Tanımsız try_guard hedefi.") from exc
        regions.append((index + 1, protected_end_index, handler_index))

    temps: dict[str, object] = {}
    values: dict[str, object] = {}
    output: list[str] = []
    pending_error: BaseException | None = None

    def temp(name: str) -> object:
        if name not in temps:
            raise TryBackendEquivalenceError(f"Tanımsız geçici değer: {name}")
        return temps[name]

    def exceptional_target(pc: int) -> int | None:
        candidates = [region for region in regions if region[0] <= pc < region[1]]
        if not candidates:
            return None
        start, _end, handler = max(candidates, key=lambda item: item[0])
        del start
        return handler

    pc = 0
    step_budget = max(2048, len(instructions) * 128)
    steps = 0
    while pc < len(instructions):
        steps += 1
        if steps > step_budget:
            raise TryBackendEquivalenceError("Try equivalence adım sınırını aştı.")

        item = instructions[pc]
        opcode = item.opcode
        operands = item.operands
        result = item.result

        if opcode == "label" or opcode == "try_guard":
            pc += 1
            continue
        if opcode == "jump":
            pc = labels[operands[0]]
            continue
        if opcode == "branch":
            pc = labels[operands[1] if bool(temp(operands[0])) else operands[2]]
            continue
        if opcode == "catch":
            if result is None or pending_error is None:
                raise TryBackendEquivalenceError("catch yalnız exceptional try yolunda çalışabilir.")
            temps[result] = pending_error
            pending_error = None
            pc += 1
            continue

        try:
            if opcode == "const" and result is not None:
                temps[result] = _decode_literal(operands[0])
            elif opcode == "load" and result is not None:
                temps[result] = values[operands[0]]
            elif opcode == "store":
                values[operands[0]] = temp(operands[1])
            elif opcode == "bind":
                if operands[0] in values:
                    raise TryBackendEquivalenceError(f"Yinelenen binding: {operands[0]}")
                values[operands[0]] = temp(operands[1])
            elif opcode == "write":
                output.append(_format(temp(operands[0])))
            elif opcode == "unary" and result is not None:
                operator, operand = operands
                value = temp(operand)
                operations = {
                    "değil": lambda: not bool(value),
                    "!": lambda: not bool(value),
                    "+": lambda: +value,
                    "-": lambda: -value,
                }
                if operator not in operations:
                    raise TryBackendEquivalenceError(f"Bilinmeyen unary: {operator}")
                temps[result] = operations[operator]()
            elif opcode == "binary" and result is not None:
                operator, left_name, right_name = operands
                left = temp(left_name)
                right = temp(right_name)
                operations = {
                    "+": lambda: left + right,
                    "-": lambda: left - right,
                    "*": lambda: left * right,
                    "/": lambda: left / right,
                    "%": lambda: left % right,
                    "==": lambda: left == right,
                    "!=": lambda: left != right,
                    "<": lambda: left < right,
                    "<=": lambda: left <= right,
                    ">": lambda: left > right,
                    ">=": lambda: left >= right,
                }
                if operator not in operations:
                    raise TryBackendEquivalenceError(f"Bilinmeyen binary: {operator}")
                temps[result] = operations[operator]()
            else:
                raise TryBackendEquivalenceError(f"Try equivalence diliminde desteklenmeyen opcode: {opcode}")
        except (ArithmeticError, TypeError, KeyError, TryBackendEquivalenceError) as exc:
            target = exceptional_target(pc)
            if target is None:
                if isinstance(exc, TryBackendEquivalenceError):
                    raise
                raise TryBackendEquivalenceError(f"Korunmayan IR hatası: {exc}") from exc
            pending_error = exc
            pc = target
            continue

        pc += 1

    if pending_error is not None:
        raise TryBackendEquivalenceError("Yakalanmamış pending error ile yürütme sonlandı.")
    return tuple(output)


def compare_try_source(source: str) -> TryEquivalenceReport:
    """Try başarı ve hata yollarını referans runtime ile WASM/native planlarında karşılaştırır."""
    program = lower_source(source)

    reference_output: list[str] = []
    Runtime(reference_output.append).execute(parse(tokenize(source)))

    wasm = build_wasm_plan(program)
    native = build_native_plan(program)
    return TryEquivalenceReport(
        reference_output=tuple(reference_output),
        wasm_output=_execute(wasm.instructions),
        native_output=_execute(native.instructions),
    )
