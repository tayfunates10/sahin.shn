import pytest

from sahin.capabilities import Capability, CapabilityError, CapabilitySet
from sahin.data_mutation_abi import DataMutationABI
from sahin.data_mutation_backend import (
    DataMutationBackendError,
    DataMutationBackendPlan,
    validate_data_mutation_backend,
)


@pytest.mark.parametrize("backend_name", ["native", "wasm"])
def test_sakla_backend_boundary_requires_explicit_write_capability(backend_name: str) -> None:
    abi = DataMutationABI(command="sakla", model="Urun", value_slot="urun")

    with pytest.raises(CapabilityError, match="veri:yaz"):
        validate_data_mutation_backend(
            abi,
            capabilities=CapabilitySet(),
            backend_name=backend_name,
        )


@pytest.mark.parametrize("backend_name", ["native", "wasm"])
def test_sakla_backend_boundary_carries_only_validated_metadata(backend_name: str) -> None:
    abi = DataMutationABI(command="sakla", model="Urun", value_slot="urun")
    capabilities = CapabilitySet().grant(Capability.VERI_YAZ)

    assert validate_data_mutation_backend(
        abi,
        capabilities=capabilities,
        backend_name=backend_name,
    ) == DataMutationBackendPlan(
        backend=backend_name,
        command="sakla",
        model="Urun",
        value_slot="urun",
    )


def test_sakla_backend_boundary_rejects_unknown_backend() -> None:
    abi = DataMutationABI(command="sakla", model="Urun", value_slot="urun")
    capabilities = CapabilitySet().grant(Capability.VERI_YAZ)

    with pytest.raises(DataMutationBackendError, match="unsupported"):
        validate_data_mutation_backend(
            abi,
            capabilities=capabilities,
            backend_name="javascript",
        )
