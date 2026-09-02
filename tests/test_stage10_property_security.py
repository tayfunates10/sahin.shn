import pytest

from sahin.ir import IRInstruction, IRProgram, lower_source
from sahin.native_backend import NativeBackendError, build_native_plan
from sahin.wasm_backend import WasmBackendError, build_wasm_plan


BACKENDS = (
    (build_wasm_plan, WasmBackendError),
    (build_native_plan, NativeBackendError),
)


@pytest.mark.parametrize(
    "source",
    [
        'ad = "Şahin"\nyaz ad\n',
        'sayı = 1 + 2 * 3\nyaz sayı\n',
        'aktif = evet\nyaz aktif\n',
        'fiyat = 10,50₺\nyaz fiyat\n',
        'değer = -5\nyaz değer\n',
    ],
)
def test_stage10_ir_property_same_source_has_same_canonical_form(source):
    baseline = lower_source(source).canonical()

    for _ in range(10):
        assert lower_source(source).canonical() == baseline


@pytest.mark.parametrize("build,error_type", BACKENDS)
@pytest.mark.parametrize(
    "program",
    [
        IRProgram(version=2, instructions=()),
        IRProgram(version=1, instructions=(IRInstruction("unknown"),)),
        IRProgram(version=1, instructions=(IRInstruction("const", (), "%0"),)),
        IRProgram(version=1, instructions=(IRInstruction("const", ("tam:1",), "sonuç"),)),
        IRProgram(version=1, instructions=(IRInstruction("write", ("%0",)),)),
        IRProgram(
            version=1,
            instructions=(
                IRInstruction("const", ("tam:1",), "%0"),
                IRInstruction("const", ("tam:2",), "%0"),
            ),
        ),
        IRProgram(
            version=1,
            instructions=(
                IRInstruction("const", ("tam:1",), "%0"),
                IRInstruction("binary", ("+", "%0", "%9"), "%1"),
            ),
        ),
        IRProgram(
            version=1,
            instructions=(
                IRInstruction("const", ("tam:1",), "%0"),
                IRInstruction("store", ("%gizli", "%0")),
            ),
        ),
    ],
)
def test_stage10_backends_fail_closed_for_malformed_or_unsafe_ir(build, error_type, program):
    with pytest.raises(error_type):
        build(program)


@pytest.mark.parametrize("build,error_type", BACKENDS)
def test_stage10_percent_operator_is_allowed_only_in_binary_operator_role(build, error_type):
    valid = IRProgram(
        version=1,
        instructions=(
            IRInstruction("const", ("tam:5",), "%0"),
            IRInstruction("const", ("tam:2",), "%1"),
            IRInstruction("binary", ("%", "%0", "%1"), "%2"),
            IRInstruction("write", ("%2",)),
        ),
    )
    assert build(valid).instructions == valid.instructions

    invalid = IRProgram(
        version=1,
        instructions=(
            IRInstruction("const", ("tam:1",), "%0"),
            IRInstruction("store", ("%", "%0")),
        ),
    )
    with pytest.raises(error_type):
        build(invalid)


@pytest.mark.parametrize("build,error_type", BACKENDS)
def test_stage10_backend_capability_surface_remains_default_closed(build, error_type):
    program = lower_source('değer = 1\nyaz değer\n')
    plan = build(program)

    capabilities = getattr(plan, "capabilities", ())
    imports = getattr(plan, "imports", ())
    assert capabilities == ()
    assert imports == ()
