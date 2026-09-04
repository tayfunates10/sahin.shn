from __future__ import annotations

from dataclasses import dataclass
import json

from .ir import IRFlow, IRInstruction, IRProgram
from .member_source_provenance import build_member_source_provenance
from .pipeline_source_provenance import build_pipeline_source_provenance
from .range_source_provenance import build_range_source_provenance
from .record_ir import lower_source_with_record_metadata
from .record_metadata import RecordSchemaABI
from .source_provenance import SourceProvenance, build_source_provenance
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
    source_provenance: tuple[SourceProvenance, ...] = ()
    record_schemas: tuple[RecordSchemaABI, ...] = ()

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
        if self.source_provenance:
            payload["source_provenance"] = [json.loads(item.canonical()) for item in self.source_provenance]
        if self.record_schemas:
            payload["record_schemas"] = [json.loads(item.canonical()) for item in self.record_schemas]
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
    """Gerçek frontend → Şahin IR + kayıt metadata → güvenli native adapter planını üretir."""
    bundle = lower_source_with_record_metadata(source)
    program = bundle.program
    plan = build_native_plan(program)
    return NativeAdapterPlan(
        ir_version=plan.ir_version,
        adapter_version=plan.adapter_version,
        target=plan.target,
        capabilities=plan.capabilities,
        instructions=plan.instructions,
        flows=plan.flows,
        source_provenance=(
            *build_source_provenance(source, program),
            *build_member_source_provenance(source, program),
            *build_range_source_provenance(source, program),
            *build_pipeline_source_provenance(source, program),
        ),
        record_schemas=bundle.record_schemas,
    )
