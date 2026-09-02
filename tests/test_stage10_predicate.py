from __future__ import annotations

import pytest

from sahin.backend_equivalence import compare_source
from sahin.ir import IRInstruction, IRProgram, lower_source
from sahin.native_backend import NativeBackendError, build_native_plan
from sahin.wasm_backend import WasmBackendError, build_wasm_plan


@pytest.mark.parametrize(
    ("source", "expected_output"),
    [
        ("değer = yok\ndeğer yok ise\n    yaz \"yok\"\n", ("yok",)),
        ("değer = \"\"\ndeğer boş ise\n    yaz \"boş\"\n", ("boş",)),
        ("değer = \"şahin\"\ndeğer boş değil ise\n    yaz \"dolu\"\n", ("dolu",)),
    ],
)
def test_predicates_lower_and_preserve_backend_equivalence(source: str, expected_output: tuple[str, ...]):
    program = lower_source(source)

    predicate_instructions = [item for item in program.instructions if item.opcode == "predicate"]
    assert len(predicate_instructions) == 1

    report = compare_source(source)
    assert report.equivalent
    assert report.reference.output == expected_output


@pytest.mark.parametrize("builder,error_type", [(build_wasm_plan, WasmBackendError), (build_native_plan, NativeBackendError)])
def test_predicate_schema_rejects_unknown_predicate(builder, error_type):
    program = IRProgram(
        version=1,
        instructions=(
            IRInstruction("const", ("yok:null",), "%0"),
            IRInstruction("predicate", ("bilinmeyen", "%0"), "%1"),
        ),
    )

    with pytest.raises(error_type, match="bilinmeyen yüklem"):
        builder(program)


@pytest.mark.parametrize("builder,error_type", [(build_wasm_plan, WasmBackendError), (build_native_plan, NativeBackendError)])
def test_predicate_requires_definitely_defined_temp(builder, error_type):
    program = IRProgram(
        version=1,
        instructions=(IRInstruction("predicate", ("yok", "%missing"), "%0"),),
    )

    with pytest.raises(error_type, match="tanımsız geçici değer"):
        builder(program)
