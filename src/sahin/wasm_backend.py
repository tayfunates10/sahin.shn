from __future__ import annotations

from dataclasses import dataclass
import json

from .adapter_source_ir import lower_source_with_adapter_metadata
from .ir import IRFlow, IRInstruction, IRProgram
from .member_source_provenance import build_member_source_provenance
from .member_store_backend_validation import validate_backend_program_with_member_store
from .pipeline_source_provenance import build_pipeline_source_provenance
from .range_source_provenance import build_range_source_provenance
from .record_adapter_metadata import (
    RecordAdapterMetadataError,
    ValidatedAdapterRecordMetadata,
    build_validated_adapter_record_metadata,
)
from .record_metadata import RecordSchemaABI
from .source_provenance import SourceProvenance, build_source_provenance
from .structural_backend_validation import (
    StructuralBackendValidationError,
    validate_structural_metadata_for_backend,
)
from .structural_declaration_abi import StructuralDeclarationMetadata


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
    record_metadata: tuple[ValidatedAdapterRecordMetadata, ...] = ()
    structural_declarations: tuple[StructuralDeclarationMetadata, ...] = ()

    @property
    def record_schemas(self) -> tuple[RecordSchemaABI, ...]:
        """Backward-compatible wire view backed by validated canonical metadata."""
        return tuple(item.wire_schema for item in self.record_metadata)

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
        if self.record_metadata:
            payload["record_schemas"] = [json.loads(item.canonical_wire()) for item in self.record_metadata]
        if self.structural_declarations:
            payload["structural_declarations"] = [
                {
                    "body_arity": item.body_arity,
                    "header_arity": item.header_arity,
                    "kind": item.kind,
                    "name": item.name,
                }
                for item in self.structural_declarations
            ]
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def build_wasm_plan(program: IRProgram) -> WasmAdapterPlan:
    """IR v1'i capability importu açmadan deterministik WASM adapter planına çevirir."""
    validate_backend_program_with_member_store(
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
    """Gerçek frontend → IR + metadata → güvenli WASM adapter planını üretir."""
    bundle = lower_source_with_adapter_metadata(source)
    program = bundle.program
    plan = build_wasm_plan(program)
    try:
        record_metadata = build_validated_adapter_record_metadata(bundle.record_schemas)
        structural_declarations = validate_structural_metadata_for_backend(
            bundle.structural_declarations
        )
    except (RecordAdapterMetadataError, StructuralBackendValidationError) as exc:
        raise WasmBackendError(f"WASM metadata doğrulaması başarısız: {exc}") from exc
    return WasmAdapterPlan(
        ir_version=plan.ir_version,
        adapter_version=plan.adapter_version,
        imports=plan.imports,
        instructions=plan.instructions,
        flows=plan.flows,
        source_provenance=(
            *build_source_provenance(source, program),
            *build_member_source_provenance(source, program),
            *build_range_source_provenance(source, program),
            *build_pipeline_source_provenance(source, program),
        ),
        record_metadata=record_metadata,
        structural_declarations=structural_declarations,
    )
