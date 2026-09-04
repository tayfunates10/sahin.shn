from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import json
from typing import Sequence

from .ast_nodes import SourceLocation
from .ir import IRFlow, IRInstruction
from .lexer import tokenize
from .native_backend import build_native_plan_from_source
from .parser import parse
from .runtime import Runtime, RuntimeErrorSHN
from .source_provenance import SourceProvenance
from .wasm_backend import build_wasm_plan_from_source


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
    if isinstance(value, RuntimeErrorSHN):
        return str(value)
    if isinstance(value, BaseException):
        raise TryBackendEquivalenceError(
            "Yakalanan hata payload'ı doğrulanmış kaynak provenance olmadan gözlemlenemez."
        )
    if value is True:
        return "evet"
    if value is False:
        return "hayır"
    if value is None:
        return "yok"
    if isinstance(value, Decimal):
        return format(value, "f")
    return str(value)


def _regions(instructions: Sequence[IRInstruction], labels: dict[str, int]) -> tuple[tuple[int, int, int], ...]:
    result: list[tuple[int, int, int]] = []
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
        result.append((index + 1, protected_end_index, handler_index))
    return tuple(result)


def _execute(
    instructions: Sequence[IRInstruction],
    source_provenance: Sequence[SourceProvenance] = (),
    flows: Sequence[IRFlow] = (),
) -> tuple[str, ...]:
    flow_table = {flow.name: flow for flow in flows}
    if len(flow_table) != len(flows):
        raise TryBackendEquivalenceError("Yinelenen flow adı equivalence yürütücüsünde reddedildi.")

    provenance_by_scope: dict[tuple[str | None, int], SourceProvenance] = {}
    for item in source_provenance:
        key = (item.flow_name, item.instruction_index)
        if key in provenance_by_scope:
            raise TryBackendEquivalenceError(
                "Yinelenen source provenance instruction indeksi aynı kapsamda reddedildi."
            )
        provenance_by_scope[key] = item

    global_values: dict[str, object] = {}
    output: list[str] = []
    step_budget = max(4096, (len(instructions) + sum(len(flow.instructions) for flow in flows)) * 256)
    steps = 0

    def runtime_error_for(
        pc: int,
        scope: str | None,
        opcode: str,
        operands: Sequence[str],
        exc: BaseException,
    ) -> RuntimeErrorSHN:
        provenance = provenance_by_scope.get((scope, pc))
        if provenance is None or provenance.kind != opcode:
            scope_name = scope or "<ana>"
            raise TryBackendEquivalenceError(
                f"Yakalanan {opcode} hatası için doğrulanmış source provenance bulunamadı "
                f"(kapsam {scope_name}, instruction {pc})."
            ) from exc
        location = SourceLocation(provenance.line, provenance.column)
        if opcode in {"binary", "unary"}:
            operator = operands[0]
            return RuntimeErrorSHN(
                f"{operator!r} işlemi uygulanamadı: {exc}",
                location=location,
            )
        raise TryBackendEquivalenceError(
            f"Source provenance mevcut olsa da {opcode!r} hata payload ABI'ı henüz desteklenmiyor."
        ) from exc

    def call_frame_for(
        pc: int,
        scope: str | None,
        flow: IRFlow,
        exc: RuntimeErrorSHN,
    ) -> RuntimeErrorSHN:
        provenance = provenance_by_scope.get((scope, pc))
        if provenance is None or provenance.kind != "call":
            scope_name = scope or "<ana>"
            raise TryBackendEquivalenceError(
                "Flow dışına taşan RuntimeErrorSHN için doğrulanmış call-site provenance bulunamadı "
                f"(kapsam {scope_name}, instruction {pc})."
            ) from exc
        location = SourceLocation(provenance.line, provenance.column)
        frame_name = flow.name.removeprefix("@akış:") or "<akış>"
        return exc.with_frame(frame_name, location)

    def run(
        sequence: Sequence[IRInstruction],
        *,
        scope: str | None,
        local_values: dict[str, object],
        local_bindings: set[str],
        captures: frozenset[str] = frozenset(),
        depth: int = 0,
        expect_return: bool = False,
    ) -> tuple[bool, object | None]:
        nonlocal steps
        if depth > 128:
            raise TryBackendEquivalenceError("Flow try equivalence çağrı derinliği sınırını aştı.")

        labels = {
            item.operands[0]: index
            for index, item in enumerate(sequence)
            if item.opcode == "label" and len(item.operands) == 1
        }
        regions = _regions(sequence, labels)
        temps: dict[str, object] = {}
        pending_error: RuntimeErrorSHN | None = None

        def temp(name: str) -> object:
            if name not in temps:
                raise TryBackendEquivalenceError(f"Tanımsız geçici değer: {name}")
            return temps[name]

        def lookup(name: str) -> object:
            if name in local_values:
                return local_values[name]
            if name in captures and name in global_values:
                return global_values[name]
            raise TryBackendEquivalenceError(f"Tanımsız IR isim yüklemesi: {name}")

        def store(name: str, value: object) -> None:
            if name in local_bindings:
                raise TryBackendEquivalenceError(f"Bağlı IR değeri '=' ile yeniden atanamaz: {name}")
            if name in captures:
                if name not in global_values:
                    raise TryBackendEquivalenceError(f"Tanımsız lexical capture: {name}")
                global_values[name] = value
                return
            local_values[name] = value

        def exceptional_target(pc: int) -> int | None:
            candidates = [region for region in regions if region[0] <= pc < region[1]]
            if not candidates:
                return None
            return max(candidates, key=lambda item: item[0])[2]

        pc = 0
        while pc < len(sequence):
            steps += 1
            if steps > step_budget:
                raise TryBackendEquivalenceError("Try equivalence adım sınırını aştı.")

            item = sequence[pc]
            opcode = item.opcode
            operands = item.operands
            result = item.result

            if opcode in {"label", "try_guard"}:
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
            if opcode == "return":
                return True, temp(operands[0])

            try:
                if opcode == "const" and result is not None:
                    temps[result] = _decode_literal(operands[0])
                elif opcode == "load" and result is not None:
                    temps[result] = lookup(operands[0])
                elif opcode == "store":
                    store(operands[0], temp(operands[1]))
                elif opcode == "bind":
                    name = operands[0]
                    if name in local_values:
                        raise TryBackendEquivalenceError(f"Yinelenen binding: {name}")
                    local_values[name] = temp(operands[1])
                    local_bindings.add(name)
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
                elif opcode == "call" and result is not None:
                    flow_name, *argument_names = operands
                    flow = flow_table.get(flow_name)
                    if flow is None:
                        raise TryBackendEquivalenceError(f"Bilinmeyen IR call hedefi: {flow_name}")
                    arguments = tuple(temp(name) for name in argument_names)
                    if len(arguments) != len(flow.parameters):
                        raise TryBackendEquivalenceError(f"IR call argüman sayısı uyuşmuyor: {flow_name}")
                    frame_values = dict(zip(flow.parameters, arguments, strict=True))
                    try:
                        returned, value = run(
                            flow.instructions,
                            scope=flow.name,
                            local_values=frame_values,
                            local_bindings=set(),
                            captures=frozenset(flow.captures),
                            depth=depth + 1,
                            expect_return=True,
                        )
                    except RuntimeErrorSHN as exc:
                        escaped = call_frame_for(pc, scope, flow, exc)
                        target = exceptional_target(pc)
                        if target is None:
                            raise escaped from exc
                        pending_error = escaped
                        pc = target
                        continue
                    if not returned:
                        raise TryBackendEquivalenceError(f"Akış dönüş üretmeden sonlandı: {flow_name}")
                    temps[result] = value
                else:
                    raise TryBackendEquivalenceError(f"Try equivalence diliminde desteklenmeyen opcode: {opcode}")
            except (ArithmeticError, TypeError) as exc:
                target = exceptional_target(pc)
                error = runtime_error_for(pc, scope, opcode, operands, exc)
                if target is None:
                    raise error from exc
                pending_error = error
                pc = target
                continue
            except (KeyError, TryBackendEquivalenceError) as exc:
                target = exceptional_target(pc)
                if target is None:
                    if isinstance(exc, TryBackendEquivalenceError):
                        raise
                    raise TryBackendEquivalenceError(f"Korunmayan IR hatası: {exc}") from exc
                raise TryBackendEquivalenceError(
                    f"Yakalanan backend yürütme hatası kullanıcı hata payload'ına güvenle dönüştürülemedi: {exc}"
                ) from exc

            pc += 1

        if pending_error is not None:
            raise TryBackendEquivalenceError("Yakalanmamış pending error ile yürütme sonlandı.")
        if expect_return:
            return False, None
        return False, None

    run(instructions, scope=None, local_values=global_values, local_bindings=set())
    return tuple(output)


def compare_try_source(source: str) -> TryEquivalenceReport:
    reference_output: list[str] = []
    Runtime(reference_output.append).execute(parse(tokenize(source)))

    wasm = build_wasm_plan_from_source(source)
    native = build_native_plan_from_source(source)
    return TryEquivalenceReport(
        reference_output=tuple(reference_output),
        wasm_output=_execute(wasm.instructions, wasm.source_provenance, wasm.flows),
        native_output=_execute(native.instructions, native.source_provenance, native.flows),
    )