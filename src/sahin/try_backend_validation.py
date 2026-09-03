from __future__ import annotations

import json

from .foreach_backend_validation import validate_backend_program_with_foreach
from .ir import IRFlow, IRInstruction, IRProgram
from .ir_control_flow import IRControlFlowError, validate_control_flow

_TRY_OPCODES = frozenset({"try_guard", "catch"})


def _contains_try(instructions: tuple[IRInstruction, ...]) -> bool:
    return any(instruction.opcode in _TRY_OPCODES for instruction in instructions)


def _validate_try_schema(
    instructions: tuple[IRInstruction, ...],
    *,
    error_type: type[ValueError],
    backend_name: str,
) -> None:
    for index, instruction in enumerate(instructions):
        if instruction.opcode == "try_guard":
            if len(instruction.operands) != 2 or instruction.result is not None:
                raise error_type(
                    f"{backend_name} adapter geçersiz try_guard şemasını reddetti (instruction {index})."
                )
            handler, protected_end = instruction.operands
            if (
                not handler
                or not protected_end
                or handler.startswith("%")
                or protected_end.startswith("%")
                or handler == protected_end
            ):
                raise error_type(
                    f"{backend_name} adapter geçersiz try_guard hedeflerini reddetti (instruction {index})."
                )
        elif instruction.opcode == "catch":
            if instruction.operands or instruction.result is None or not instruction.result.startswith("%"):
                raise error_type(
                    f"{backend_name} adapter geçersiz catch şemasını reddetti (instruction {index})."
                )


def _validate_try_cfg(
    instructions: tuple[IRInstruction, ...],
    *,
    predefined_names: tuple[str, ...],
    error_type: type[ValueError],
    backend_name: str,
) -> None:
    try:
        validate_control_flow(
            IRProgram(version=1, instructions=instructions),
            predefined_names=predefined_names,
        )
    except IRControlFlowError as exc:
        raise error_type(f"{backend_name} adapter try control-flow doğrulamasını reddetti: {exc}") from exc


def _sanitized_sequence(instructions: tuple[IRInstruction, ...]) -> tuple[IRInstruction, ...]:
    """Try-aware CFG'yi ortak backend validatorının anlayacağı eşdeğer doğrulama CFG'sine çevirir."""
    if not _contains_try(instructions):
        return instructions

    used_results = {item.result for item in instructions if item.result is not None}
    used_labels = {
        item.operands[0]
        for item in instructions
        if item.opcode == "label" and len(item.operands) == 1
    }
    rewritten: list[IRInstruction] = []
    sequence = 0

    def fresh_temp() -> str:
        nonlocal sequence
        while True:
            candidate = f"%__shn_backend_try_{sequence}"
            sequence += 1
            if candidate not in used_results:
                used_results.add(candidate)
                return candidate

    def fresh_label() -> str:
        nonlocal sequence
        while True:
            candidate = f"__shn_backend_try_{sequence}_normal"
            sequence += 1
            if candidate not in used_labels:
                used_labels.add(candidate)
                return candidate

    for instruction in instructions:
        if instruction.opcode == "try_guard":
            handler, _protected_end = instruction.operands
            condition = fresh_temp()
            normal_label = fresh_label()
            # Ortak backend validatorı try opcode'unu tanımıyor. Doğrulama kopyasında
            # guard'ı iki olası kenarı olan sıradan bir branch ile temsil ederek handler
            # yolunun ulaşılabilirliğini ve catch sonucunun definite-definition analizini koru.
            rewritten.append(IRInstruction("const", ("evet_hayır:evet",), condition))
            rewritten.append(IRInstruction("branch", (condition, normal_label, handler)))
            rewritten.append(IRInstruction("label", (normal_label,)))
            continue
        if instruction.opcode == "catch":
            assert instruction.result is not None
            rewritten.append(
                IRInstruction(
                    "const",
                    ("metin:" + json.dumps("<yakalanan-hata>", ensure_ascii=False),),
                    instruction.result,
                )
            )
            continue
        rewritten.append(instruction)
    return tuple(rewritten)


def validate_backend_program_with_try(
    program: IRProgram,
    *,
    error_type: type[ValueError],
    backend_name: str,
) -> None:
    """Mevcut backend hata sözleşmesini koruyarak try/error-region desteğini fail-closed doğrular."""
    top_has_try = _contains_try(program.instructions)
    flow_has_try = tuple(_contains_try(flow.instructions) for flow in program.flows)

    # Try içermeyen programlarda önceki validator zincirini byte-for-byte davranışla koru.
    if not top_has_try and not any(flow_has_try):
        validate_backend_program_with_foreach(
            program,
            error_type=error_type,
            backend_name=backend_name,
        )
        return

    # Yalnız try opcode'larının kendi şemasını burada kontrol et. Diğer opcode/schema
    # hatalarının mevcut backend zincirindeki hata önceliği değişmemelidir.
    if top_has_try:
        _validate_try_schema(program.instructions, error_type=error_type, backend_name=backend_name)
    for flow, has_try in zip(program.flows, flow_has_try, strict=True):
        if has_try:
            _validate_try_schema(flow.instructions, error_type=error_type, backend_name=backend_name)

    sanitized_flows = tuple(
        IRFlow(
            name=flow.name,
            parameters=flow.parameters,
            parameter_types=flow.parameter_types,
            return_type=flow.return_type,
            captures=flow.captures,
            instructions=_sanitized_sequence(flow.instructions) if has_try else flow.instructions,
        )
        for flow, has_try in zip(program.flows, flow_has_try, strict=True)
    )
    sanitized = IRProgram(
        version=program.version,
        instructions=_sanitized_sequence(program.instructions) if top_has_try else program.instructions,
        flows=sanitized_flows,
    )

    # Önce mevcut range/pipeline/foreach/base backend kalite zincirini çalıştır. Böylece
    # unrelated opcode/schema/use-before-def hata sözleşmeleri geriye dönük aynı kalır.
    validate_backend_program_with_foreach(
        sanitized,
        error_type=error_type,
        backend_name=backend_name,
    )

    # Base zincir geçtikten sonra özgün try-aware CFG üzerinde handler/catch güvenliğini doğrula.
    if top_has_try:
        _validate_try_cfg(
            program.instructions,
            predefined_names=(),
            error_type=error_type,
            backend_name=backend_name,
        )
    for flow, has_try in zip(program.flows, flow_has_try, strict=True):
        if has_try:
            _validate_try_cfg(
                flow.instructions,
                predefined_names=(*flow.parameters, *flow.captures),
                error_type=error_type,
                backend_name=backend_name,
            )
