from __future__ import annotations

import re
from collections.abc import Callable

from .ir import IRFlow, IRInstruction, IRProgram
from .ir_control_flow import IRControlFlowError, validate_control_flow

_ALLOWED_OPCODES = frozenset({
    "const", "load", "unary", "binary", "predicate", "member", "call",
    "store", "bind", "write", "label", "jump", "branch", "return",
})
_ALLOWED_PREDICATES = frozenset({"yok", "boş", "boş_değil"})


def validate_backend_program(
    program: IRProgram,
    *,
    error_type: type[ValueError],
    backend_name: str,
) -> None:
    """IR v1'i adapter sınırında flow/call ABI dahil fail-closed doğrular."""
    if program.version != 1:
        raise error_type(f"Desteklenmeyen Şahin IR sürümü: {program.version}")

    flows: dict[str, IRFlow] = {}
    for flow in program.flows:
        if not flow.name or flow.name.startswith("%"):
            raise error_type(f"{backend_name} adapter geçersiz akış adını reddetti: {flow.name!r}")
        if flow.name in flows:
            raise error_type(f"{backend_name} adapter yinelenen akış adını reddetti: {flow.name}")
        if len(flow.parameters) != len(flow.parameter_types):
            raise error_type(f"{backend_name} adapter akış parametre/type ABI uzunluk uyuşmazlığını reddetti: {flow.name}")
        names = (*flow.parameters, *flow.captures)
        if any(not name or name.startswith("%") for name in names):
            raise error_type(f"{backend_name} adapter geçersiz akış parametre/capture adını reddetti: {flow.name}")
        if len(set(flow.parameters)) != len(flow.parameters):
            raise error_type(f"{backend_name} adapter yinelenen akış parametresini reddetti: {flow.name}")
        if len(set(flow.captures)) != len(flow.captures):
            raise error_type(f"{backend_name} adapter yinelenen lexical capture'ı reddetti: {flow.name}")
        if set(flow.parameters) & set(flow.captures):
            raise error_type(f"{backend_name} adapter parametre/capture çakışmasını reddetti: {flow.name}")
        flows[flow.name] = flow

    _validate_instruction_sequence(
        program.instructions,
        flows=flows,
        error_type=error_type,
        backend_name=backend_name,
        in_flow=False,
    )
    _validate_cfg(
        IRProgram(version=1, instructions=program.instructions),
        predefined_names=(),
        error_type=error_type,
        backend_name=backend_name,
    )

    for flow in program.flows:
        _validate_instruction_sequence(
            flow.instructions,
            flows=flows,
            error_type=error_type,
            backend_name=backend_name,
            in_flow=True,
        )
        _validate_cfg(
            IRProgram(version=1, instructions=flow.instructions),
            predefined_names=(*flow.parameters, *flow.captures),
            error_type=error_type,
            backend_name=backend_name,
        )


def _schema_error(
    instruction: IRInstruction,
    index: int,
    detail: str,
    *,
    error_type: type[ValueError],
    backend_name: str,
) -> None:
    raise error_type(
        f"{backend_name} adapter geçersiz {instruction.opcode} instruction şemasını reddetti "
        f"(instruction {index}): {detail}"
    )


def _non_temp(
    instruction: IRInstruction,
    operand: str,
    index: int,
    role: str,
    *,
    error_type: type[ValueError],
    backend_name: str,
    allow_percent_operator: bool = False,
) -> None:
    reserved = operand.startswith("%") and not (allow_percent_operator and operand == "%")
    if not operand or reserved:
        _schema_error(
            instruction,
            index,
            f"{role} geçici değer olamaz ve boş bırakılamaz",
            error_type=error_type,
            backend_name=backend_name,
        )


def _temp(
    operand: str,
    index: int,
    *,
    error_type: type[ValueError],
    backend_name: str,
) -> None:
    if not operand.startswith("%"):
        raise error_type(
            f"{backend_name} adapter geçici değer beklenen operandı reddetti: {operand} (instruction {index})."
        )


def _validate_instruction_sequence(
    instructions: tuple[IRInstruction, ...],
    *,
    flows: dict[str, IRFlow],
    error_type: type[ValueError],
    backend_name: str,
    in_flow: bool,
) -> None:
    results: set[str] = set()
    for index, instruction in enumerate(instructions):
        opcode = instruction.opcode
        operands = instruction.operands
        result = instruction.result
        if opcode not in _ALLOWED_OPCODES:
            raise error_type(f"{backend_name} adapter desteklenmeyen opcode'u reddetti: {opcode}")

        if opcode == "const":
            if len(operands) != 1 or result is None:
                _schema_error(instruction, index, "const tam olarak 1 literal operand ve sonuç üretmelidir", error_type=error_type, backend_name=backend_name)
            _non_temp(instruction, operands[0], index, "literal operand", error_type=error_type, backend_name=backend_name)
        elif opcode == "load":
            if len(operands) != 1 or result is None:
                _schema_error(instruction, index, "load tam olarak 1 isim operandı ve sonuç üretmelidir", error_type=error_type, backend_name=backend_name)
            _non_temp(instruction, operands[0], index, "isim operandı", error_type=error_type, backend_name=backend_name)
        elif opcode == "unary":
            if len(operands) != 2 or result is None:
                _schema_error(instruction, index, "unary operatör + 1 geçici operand ve sonuç üretmelidir", error_type=error_type, backend_name=backend_name)
            _non_temp(instruction, operands[0], index, "operatör", error_type=error_type, backend_name=backend_name)
            _temp(operands[1], index, error_type=error_type, backend_name=backend_name)
        elif opcode == "binary":
            if len(operands) != 3 or result is None:
                _schema_error(instruction, index, "binary operatör + 2 geçici operand ve sonuç üretmelidir", error_type=error_type, backend_name=backend_name)
            _non_temp(instruction, operands[0], index, "operatör", error_type=error_type, backend_name=backend_name, allow_percent_operator=True)
            _temp(operands[1], index, error_type=error_type, backend_name=backend_name)
            _temp(operands[2], index, error_type=error_type, backend_name=backend_name)
        elif opcode == "predicate":
            if len(operands) != 2 or result is None:
                _schema_error(instruction, index, "predicate yüklem + 1 geçici operand ve sonuç üretmelidir", error_type=error_type, backend_name=backend_name)
            if operands[0] not in _ALLOWED_PREDICATES:
                _schema_error(instruction, index, f"bilinmeyen yüklem: {operands[0]}", error_type=error_type, backend_name=backend_name)
            _temp(operands[1], index, error_type=error_type, backend_name=backend_name)
        elif opcode == "member":
            if len(operands) != 2 or result is None:
                _schema_error(instruction, index, "member üye adı + 1 hedef geçici operand ve sonuç üretmelidir", error_type=error_type, backend_name=backend_name)
            _non_temp(instruction, operands[0], index, "üye adı", error_type=error_type, backend_name=backend_name)
            _temp(operands[1], index, error_type=error_type, backend_name=backend_name)
        elif opcode == "call":
            if len(operands) < 1 or result is None:
                _schema_error(instruction, index, "call akış adı + argüman geçicileri almalı ve sonuç üretmelidir", error_type=error_type, backend_name=backend_name)
            target = operands[0]
            _non_temp(instruction, target, index, "akış adı", error_type=error_type, backend_name=backend_name)
            flow = flows.get(target)
            if flow is None:
                raise error_type(f"{backend_name} adapter bilinmeyen call hedefini reddetti: {target} (instruction {index}).")
            if len(operands) - 1 != len(flow.parameters):
                raise error_type(
                    f"{backend_name} adapter call argüman sayısını reddetti: {target} "
                    f"{len(flow.parameters)} bekliyor, {len(operands) - 1} verildi (instruction {index})."
                )
            for operand in operands[1:]:
                _temp(operand, index, error_type=error_type, backend_name=backend_name)
        elif opcode in {"store", "bind"}:
            if len(operands) != 2 or result is not None:
                _schema_error(instruction, index, f"{opcode} isim + 1 geçici operand almalı ve sonuç üretmemelidir", error_type=error_type, backend_name=backend_name)
            _non_temp(instruction, operands[0], index, "isim operandı", error_type=error_type, backend_name=backend_name)
            _temp(operands[1], index, error_type=error_type, backend_name=backend_name)
        elif opcode == "write":
            if len(operands) != 1 or result is not None:
                _schema_error(instruction, index, "write tam olarak 1 geçici operand almalı ve sonuç üretmemelidir", error_type=error_type, backend_name=backend_name)
            _temp(operands[0], index, error_type=error_type, backend_name=backend_name)
        elif opcode == "label":
            if len(operands) != 1 or result is not None:
                _schema_error(instruction, index, "label tam olarak 1 etiket almalı ve sonuç üretmemelidir", error_type=error_type, backend_name=backend_name)
            _non_temp(instruction, operands[0], index, "etiket", error_type=error_type, backend_name=backend_name)
        elif opcode == "jump":
            if len(operands) != 1 or result is not None:
                _schema_error(instruction, index, "jump tam olarak 1 hedef etiket almalı ve sonuç üretmemelidir", error_type=error_type, backend_name=backend_name)
            _non_temp(instruction, operands[0], index, "hedef etiket", error_type=error_type, backend_name=backend_name)
        elif opcode == "branch":
            if len(operands) != 3 or result is not None:
                _schema_error(instruction, index, "branch koşul + doğru/yanlış hedefleri almalı ve sonuç üretmemelidir", error_type=error_type, backend_name=backend_name)
            _temp(operands[0], index, error_type=error_type, backend_name=backend_name)
            _non_temp(instruction, operands[1], index, "doğru hedef", error_type=error_type, backend_name=backend_name)
            _non_temp(instruction, operands[2], index, "yanlış hedef", error_type=error_type, backend_name=backend_name)
        elif opcode == "return":
            if not in_flow:
                raise error_type(f"{backend_name} adapter top-level return instruction'ını reddetti (instruction {index}).")
            if len(operands) != 1 or result is not None:
                _schema_error(instruction, index, "return tam olarak 1 geçici değer almalı ve sonuç üretmemelidir", error_type=error_type, backend_name=backend_name)
            _temp(operands[0], index, error_type=error_type, backend_name=backend_name)

        if result is not None:
            if not result.startswith("%"):
                raise error_type(f"{backend_name} adapter geçersiz geçici sonuç adını reddetti: {result}")
            if result in results:
                raise error_type(f"{backend_name} adapter yeniden tanımlanan geçici sonucu reddetti: {result}")
            results.add(result)


def _validate_cfg(
    program: IRProgram,
    *,
    predefined_names: tuple[str, ...],
    error_type: type[ValueError],
    backend_name: str,
) -> None:
    try:
        validate_control_flow(program, predefined_names=predefined_names)
    except IRControlFlowError as exc:
        message = str(exc)
        temp_match = re.search(r"Geçici değer tüm ulaşılabilir giriş yollarında tanımlı olmalıdır: (\S+) \(instruction (\d+)\)\.", message)
        if temp_match:
            operand, index = temp_match.groups()
            raise error_type(
                f"{backend_name} adapter tanımsız geçici değer kullanımı reddetti: {operand} (instruction {index})."
            ) from exc
        name_match = re.search(r"İsim tüm ulaşılabilir giriş yollarında tanımlı olmalıdır: (.+) \(instruction (\d+)\)\.", message)
        if name_match:
            name, index = name_match.groups()
            raise error_type(
                f"{backend_name} adapter tanımsız isim yüklemesini reddetti: {name} (instruction {index})."
            ) from exc
        raise error_type(f"{backend_name} adapter control-flow sözleşmesini reddetti: {exc}") from exc
