from __future__ import annotations

from dataclasses import dataclass
import json

from .ir import IRFlow, IRInstruction, IRProgram, lower_source
from .pipeline_backend_validation import validate_backend_program_with_pipeline


class WasmBackendError(ValueError):
    """Şahin IR güvenli WASM adapter sözleşmesine çevrilemediğinde oluşur."""


@dataclass(frozen=True, slots=True)
class WasmAdapterPlan:
    ir_version: int
    adapter_version: int
    imports: tuple[str, ...]
    instructions: tuple[IRInstruction, ...]
    flows: tuple[IRFlow, ...] = ()

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
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def build_wasm_plan(program: IRProgram) -> WasmAdapterPlan:
    """IR v1'i capability importu açmadan deterministik WASM adapter planına çevirir."""
    validate_backend_program_with_pipeline(
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
    """Gerçek frontend → Şahin IR → güvenli WASM adapter sınırını çalıştırır."""
    return build_wasm_plan(lower_source(source))