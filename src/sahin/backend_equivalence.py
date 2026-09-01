from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import json
from collections.abc import Sequence

from .ir import IRInstruction, lower_source
from .lexer import tokenize
from .native_backend import build_native_plan
from .parser import parse
from .runtime import Runtime
from .wasm_backend import build_wasm_plan


class BackendEquivalenceError(ValueError):
    """Adapter planının Şahin IR v1 semantiği güvenle gözlemlenemediğinde oluşur."""


@dataclass(frozen=True, slots=True)
class BackendObservation:
    state: tuple[tuple[str, object], ...]
    output: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EquivalenceReport:
    reference: BackendObservation
    wasm: BackendObservation
    native: BackendObservation

    @property
    def equivalent(self) -> bool:
        return self.reference == self.wasm == self.native


def _decode_literal(encoded: str) -> object:
    if encoded == "yok:null":
        return None
    if encoded == "evet_hayır:evet":
        return True
    if encoded == "evet_hayır:hayır":
        return False
    if encoded.startswith("tam:"):
        try:
            return int(encoded[4:])
        except ValueError as exc:
            raise BackendEquivalenceError(f"Geçersiz tam sayı literal'i: {encoded}") from exc
    if encoded.startswith("ondalık:"):
        try:
            return Decimal(encoded[8:])
        except Exception as exc:
            raise BackendEquivalenceError(f"Geçersiz ondalık literal'i: {encoded}") from exc
    if encoded.startswith("metin:"):
        try:
            value = json.loads(encoded[6:])
        except json.JSONDecodeError as exc:
            raise BackendEquivalenceError(f"Geçersiz metin literal'i: {encoded}") from exc
        if not isinstance(value, str):
            raise BackendEquivalenceError("Metin literal'i JSON string olmalıdır.")
        return value
    raise BackendEquivalenceError(f"Bilinmeyen Şahin IR literal kodlaması: {encoded}")


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


def _execute(instructions: Sequence[IRInstruction]) -> BackendObservation:
    temps: dict[str, object] = {}
    values: dict[str, object] = {}
    bindings: set[str] = set()
    output: list[str] = []

    def temp(name: str) -> object:
        try:
            return temps[name]
        except KeyError as exc:
            raise BackendEquivalenceError(f"Tanımsız IR geçici değeri: {name}") from exc

    for instruction in instructions:
        opcode = instruction.opcode
        operands = instruction.operands
        result = instruction.result

        if opcode == "const" and result is not None:
            temps[result] = _decode_literal(operands[0])
            continue
        if opcode == "load" and result is not None:
            name = operands[0]
            if name not in values:
                raise BackendEquivalenceError(f"Tanımsız IR isim yüklemesi: {name}")
            temps[result] = values[name]
            continue
        if opcode == "unary" and result is not None:
            operator, operand_name = operands
            value = temp(operand_name)
            operations = {
                "değil": lambda: not bool(value),
                "!": lambda: not bool(value),
                "-": lambda: -value,
                "+": lambda: +value,
            }
            operation = operations.get(operator)
            if operation is None:
                raise BackendEquivalenceError(f"Bilinmeyen IR tekli işlemi: {operator}")
            temps[result] = operation()
            continue
        if opcode == "binary" and result is not None:
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
            operation = operations.get(operator)
            if operation is None:
                raise BackendEquivalenceError(f"Bilinmeyen IR ikili işlemi: {operator}")
            temps[result] = operation()
            continue
        if opcode == "bind":
            name, value_name = operands
            if name in values:
                raise BackendEquivalenceError(f"IR binding aynı kapsamda yeniden tanımlandı: {name}")
            values[name] = temp(value_name)
            bindings.add(name)
            continue
        if opcode == "store":
            name, value_name = operands
            if name in bindings:
                raise BackendEquivalenceError(f"Bağlı IR değeri '=' ile yeniden atanamaz: {name}")
            values[name] = temp(value_name)
            continue
        if opcode == "write":
            output.append(_format(temp(operands[0])))
            continue
        raise BackendEquivalenceError(f"Desteklenmeyen IR opcode'u: {opcode}")

    return BackendObservation(state=tuple(sorted(values.items())), output=tuple(output))


def compare_source(source: str) -> EquivalenceReport:
    """IR v1 kapsamındaki kaynakta referans runtime ile iki adapter planını karşılaştırır."""
    reference_output: list[str] = []
    reference_runtime = Runtime(reference_output.append)
    reference_state = reference_runtime.execute(parse(tokenize(source)))
    reference = BackendObservation(
        state=tuple(sorted(reference_state.items())),
        output=tuple(reference_output),
    )

    program = lower_source(source)
    wasm_plan = build_wasm_plan(program)
    native_plan = build_native_plan(program)

    return EquivalenceReport(
        reference=reference,
        wasm=_execute(wasm_plan.instructions),
        native=_execute(native_plan.instructions),
    )
