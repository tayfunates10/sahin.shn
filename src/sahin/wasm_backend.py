from __future__ import annotations

from dataclasses import dataclass
import json

from .ir import IRFlow, IRInstruction, IRProgram, lower_source
from .source_provenance import SourceProvenance, build_source_provenance
from .try_backend_validation import validate_backend_program_with_try


class WasmBackendError(ValueError):
    """Şahin IR güvenli WASM adapter sözleşmesine çevrilemediğinde oluşur."""


@dataclass(frozen=True, slots=True)
class WasmAdapterPlan:
    ir_version: int
    adapter_version: int
    imports: tuple[str, ...]
    instructions: tuple[IRInstruction, ...]
    flows: tuple[IRFlow, ...] = ()
    source_provenance: tuple[SourceProvenance, ...] = ()

    def canonical(self) -> str:
        payload = {
            "adapter_version": self.adapter_version,
            "imports": list(self.imports),
            "instructions": [json.loads(item.canonical()) for item in self.instructions],
            "ir_version": self.ir_version,
            "target": "wasm32-sahin-safe",
        }
        if self.flows:
            payload["flows"] = [json.loads(flow.canonical()) for flow in self.flows]
        if self.source_provenance:
            payload["source_provenance"] = [json.loads(item.canonical()) for item in self.source_provenance]
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def build_wasm_plan(program: IRProgram) -> WasmAdapterPlan:
    """IR v1'i capability importu açmadan deterministik WASM adapter planına çevirir."""
    validate_backend_program_with_try(
        program,
        error_type=WasmBackendError,
        backend_name="WASM",
    )
    return WasmAdapterPlan(
        ir_version=program.version,
        adapter_version=1,
        imports=(),
        instructions=program.instructions,
        flows=program.flows,
    )


def build_wasm_plan_from_source(source: str) -> WasmAdapterPlan:
    """Gerçek frontend → Şahin IR → güvenli WASM adapter + kaynak provenance planını üretir."""
    program = lower_source(source)
    plan = build_wasm_plan(program)
    return WasmAdapterPlan(
        ir_version=plan.ir_version,
        adapter_version=plan.adapter_version,
        imports=plan.imports,
        instructions=plan.instructions,
        flows=plan.flows,
        source_provenance=build_source_provenance(source, program),
    )
