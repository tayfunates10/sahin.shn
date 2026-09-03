from __future__ import annotations

from dataclasses import dataclass
import json

from .ir import IRFlow, IRInstruction, IRProgram, lower_source
from .try_backend_validation import validate_backend_program_with_try


class NativeBackendError(ValueError):
    """Şahin IR güvenli native adapter sözleşmesine çevrilemediğinde oluşur."""


@dataclass(frozen=True, slots=True)
class NativeAdapterPlan:
    ir_version: int
    adapter_version: int
    target: str
    capabilities: tuple[str, ...]
    instructions: tuple[IRInstruction, ...]
    flows: tuple[IRFlow, ...] = ()

    def canonical(self) -> str:
        payload = {
            "adapter_version": self.adapter_version,
            "capabilities": list(self.capabilities),
            "instructions": [json.loads(item.canonical()) for item in self.instructions],
            "ir_version": self.ir_version,
            "target": self.target,
        }
        if self.flows:
            payload["flows"] = [json.loads(flow.canonical()) for flow in self.flows]
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def build_native_plan(program: IRProgram, *, target: str = "native-sahin-safe") -> NativeAdapterPlan:
    """IR v1'i capability açmadan deterministik native adapter planına çevirir."""
    if target != "native-sahin-safe":
        raise NativeBackendError(f"Desteklenmeyen native hedefi: {target}")
    validate_backend_program_with_try(
        program,
        error_type=NativeBackendError,
        backend_name="Native",
    )
    return NativeAdapterPlan(
        ir_version=program.version,
        adapter_version=1,
        target=target,
        capabilities=(),
        instructions=program.instructions,
        flows=program.flows,
    )


def build_native_plan_from_source(source: str) -> NativeAdapterPlan:
    """Gerçek frontend → Şahin IR → güvenli native adapter sınırını çalıştırır."""
    return build_native_plan(lower_source(source))
