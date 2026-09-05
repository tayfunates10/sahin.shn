import pytest

from sahin.ir import IRInstruction, IRProgram
from sahin.native_backend import NativeBackendError, build_native_plan
from sahin.wasm_backend import WasmBackendError, build_wasm_plan


def _valid_program() -> IRProgram:
    return IRProgram(
        version=1,
        instructions=(
            IRInstruction("const", ("metin:owner",), "%owner"),
            IRInstruction("const", ("tam:7",), "%value"),
            IRInstruction("member_store", ("stok", "%owner", "%value")),
        ),
    )


def test_native_and_wasm_accept_valid_member_store_without_new_capabilities():
    program = _valid_program()
    native = build_native_plan(program)
    wasm = build_wasm_plan(program)

    assert native.instructions == program.instructions
    assert native.capabilities == ()
    assert wasm.instructions == program.instructions
    assert wasm.imports == ()


@pytest.mark.parametrize(
    "builder,error_type",
    [
        (build_native_plan, NativeBackendError),
        (build_wasm_plan, WasmBackendError),
    ],
)
def test_member_store_rejects_undefined_owner_temp_on_all_backends(builder, error_type):
    program = IRProgram(
        version=1,
        instructions=(
            IRInstruction("const", ("tam:7",), "%value"),
            IRInstruction("member_store", ("stok", "%missing_owner", "%value")),
        ),
    )
    with pytest.raises(error_type, match="tanımsız geçici değer"):
        builder(program)


@pytest.mark.parametrize(
    "builder,error_type",
    [
        (build_native_plan, NativeBackendError),
        (build_wasm_plan, WasmBackendError),
    ],
)
def test_member_store_rejects_undefined_value_temp_on_all_backends(builder, error_type):
    program = IRProgram(
        version=1,
        instructions=(
            IRInstruction("const", ("metin:owner",), "%owner"),
            IRInstruction("member_store", ("stok", "%owner", "%missing_value")),
        ),
    )
    with pytest.raises(error_type, match="tanımsız geçici değer"):
        builder(program)


@pytest.mark.parametrize(
    "builder,error_type",
    [
        (build_native_plan, NativeBackendError),
        (build_wasm_plan, WasmBackendError),
    ],
)
def test_member_store_schema_stays_fail_closed_at_backend_boundary(builder, error_type):
    program = IRProgram(
        version=1,
        instructions=(IRInstruction("member_store", ("stok", "%owner")),),
    )
    with pytest.raises(error_type, match="geçersiz member_store instruction şemasını reddetti"):
        builder(program)
