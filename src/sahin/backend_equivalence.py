from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
import json

from .ir import IRFlow, IRInstruction, lower_source
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


def _empty(value: object) -> bool:
    return value is None or value == "" or value == [] or value == {} or value == ()


def _member(target: object, name: str) -> object:
    if isinstance(target, dict) and name in target:
        return target[name]
    if name == "uzunluk" and isinstance(target, (str, tuple, list, dict)):
        return len(target)
    raise BackendEquivalenceError(f"{name!r} üyesi bulunamadı.")


def _binary(operator: str, left: object, right: object) -> object:
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
    return operation()


def _execute(
    instructions: Sequence[IRInstruction],
    flows: Sequence[IRFlow] = (),
) -> BackendObservation:
    root_values: dict[str, object] = {}
    root_bindings: set[str] = set()
    output: list[str] = []
    flow_table = {flow.name: flow for flow in flows}
    step_budget = max(4096, (len(instructions) + sum(len(flow.instructions) for flow in flows)) * 128)
    steps = 0

    def run(
        sequence: Sequence[IRInstruction],
        *,
        local_values: dict[str, object],
        local_bindings: set[str],
        captures: frozenset[str] = frozenset(),
        depth: int = 0,
        expect_return: bool = False,
    ) -> tuple[bool, object | None]:
        nonlocal steps
        if depth > 128:
            raise BackendEquivalenceError("Flow equivalence çağrı derinliği sınırını aştı.")

        temps: dict[str, object] = {}
        labels = {
            item.operands[0]: index
            for index, item in enumerate(sequence)
            if item.opcode == "label" and len(item.operands) == 1
        }

        def temp(name: str) -> object:
            try:
                return temps[name]
            except KeyError as exc:
                raise BackendEquivalenceError(f"Tanımsız IR geçici değeri: {name}") from exc

        def lookup(name: str) -> object:
            if name in local_values:
                return local_values[name]
            if name in captures and name in root_values:
                return root_values[name]
            raise BackendEquivalenceError(f"Tanımsız IR isim yüklemesi: {name}")

        def store(name: str, value: object) -> None:
            if name in local_bindings:
                raise BackendEquivalenceError(f"Bağlı IR değeri '=' ile yeniden atanamaz: {name}")
            if name in captures:
                if name in root_bindings:
                    raise BackendEquivalenceError(f"Bağlı IR değeri '=' ile yeniden atanamaz: {name}")
                if name not in root_values:
                    raise BackendEquivalenceError(f"Tanımsız lexical capture: {name}")
                root_values[name] = value
                return
            local_values[name] = value

        pc = 0
        while pc < len(sequence):
            steps += 1
            if steps > step_budget:
                raise BackendEquivalenceError("Control-flow equivalence yürütme adım sınırını aştı.")

            instruction = sequence[pc]
            opcode = instruction.opcode
            operands = instruction.operands
            result = instruction.result

            if opcode == "label":
                pc += 1
                continue
            if opcode == "jump":
                try:
                    pc = labels[operands[0]]
                except KeyError as exc:
                    raise BackendEquivalenceError(f"Tanımsız IR jump hedefi: {operands[0]}") from exc
                continue
            if opcode == "branch":
                target = operands[1] if bool(temp(operands[0])) else operands[2]
                try:
                    pc = labels[target]
                except KeyError as exc:
                    raise BackendEquivalenceError(f"Tanımsız IR branch hedefi: {target}") from exc
                continue
            if opcode == "return":
                return True, temp(operands[0])
            if opcode == "const" and result is not None:
                temps[result] = _decode_literal(operands[0])
                pc += 1
                continue
            if opcode == "load" and result is not None:
                temps[result] = lookup(operands[0])
                pc += 1
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
                pc += 1
                continue
            if opcode == "binary" and result is not None:
                operator, left_name, right_name = operands
                temps[result] = _binary(operator, temp(left_name), temp(right_name))
                pc += 1
                continue
            if opcode == "predicate" and result is not None:
                predicate, operand_name = operands
                value = temp(operand_name)
                if predicate == "yok":
                    temps[result] = value is None
                elif predicate == "boş":
                    temps[result] = _empty(value)
                elif predicate == "boş_değil":
                    temps[result] = not _empty(value)
                else:
                    raise BackendEquivalenceError(f"Bilinmeyen IR yüklemi: {predicate}")
                pc += 1
                continue
            if opcode == "member" and result is not None:
                member_name, target_name = operands
                temps[result] = _member(temp(target_name), member_name)
                pc += 1
                continue
            if opcode == "call" and result is not None:
                flow_name, *argument_names = operands
                flow = flow_table.get(flow_name)
                if flow is None:
                    raise BackendEquivalenceError(f"Bilinmeyen IR call hedefi: {flow_name}")
                arguments = tuple(temp(name) for name in argument_names)
                if len(arguments) != len(flow.parameters):
                    raise BackendEquivalenceError(
                        f"IR call argüman sayısı uyuşmuyor: {flow_name} {len(flow.parameters)} bekliyor, {len(arguments)} verildi."
                    )
                frame_values = dict(zip(flow.parameters, arguments, strict=True))
                returned, value = run(
                    flow.instructions,
                    local_values=frame_values,
                    local_bindings=set(),
                    captures=frozenset(flow.captures),
                    depth=depth + 1,
                    expect_return=True,
                )
                if not returned:
                    raise BackendEquivalenceError(f"Akış dönüş üretmeden sonlandı: {flow_name}")
                temps[result] = value
                pc += 1
                continue
            if opcode == "bind":
                name, value_name = operands
                if name in local_values:
                    raise BackendEquivalenceError(f"IR binding aynı kapsamda yeniden tanımlandı: {name}")
                local_values[name] = temp(value_name)
                local_bindings.add(name)
                pc += 1
                continue
            if opcode == "store":
                name, value_name = operands
                store(name, temp(value_name))
                pc += 1
                continue
            if opcode == "write":
                output.append(_format(temp(operands[0])))
                pc += 1
                continue
            raise BackendEquivalenceError(f"Desteklenmeyen IR opcode'u: {opcode}")

        if expect_return:
            return False, None
        return False, None

    run(
        instructions,
        local_values=root_values,
        local_bindings=root_bindings,
    )
    visible_state = tuple(
        sorted((name, value) for name, value in root_values.items() if not name.startswith("$internal_"))
    )
    return BackendObservation(state=visible_state, output=tuple(output))


def compare_source(source: str) -> EquivalenceReport:
    """IR v1 kapsamındaki kaynakta referans runtime ile iki adapter planını karşılaştırır."""
    program = lower_source(source)

    reference_output: list[str] = []
    reference_runtime = Runtime(reference_output.append)
    reference_state = reference_runtime.execute(parse(tokenize(source)))
    flow_source_names = {
        flow.name.removeprefix("@akış:")
        for flow in program.flows
    }
    reference = BackendObservation(
        state=tuple(sorted((name, value) for name, value in reference_state.items() if name not in flow_source_names)),
        output=tuple(reference_output),
    )

    wasm_plan = build_wasm_plan(program)
    native_plan = build_native_plan(program)

    return EquivalenceReport(
        reference=reference,
        wasm=_execute(wasm_plan.instructions, wasm_plan.flows),
        native=_execute(native_plan.instructions, native_plan.flows),
    )
