import pytest

from sahin.capabilities import Capability, CapabilityError, CapabilitySet
from sahin.data_mutation_abi import (
    DataMutationABI,
    DataMutationABIError,
    require_data_mutation_capability,
)


def test_sakla_data_mutation_requires_explicit_write_capability() -> None:
    abi = DataMutationABI(command="sakla", model="Urun", value_slot="urun")

    with pytest.raises(CapabilityError, match="veri:yaz"):
        require_data_mutation_capability(abi, CapabilitySet())

    granted = CapabilitySet().grant(Capability.VERI_YAZ)
    assert require_data_mutation_capability(abi, granted) is abi


def test_data_mutation_abi_rejects_unknown_command() -> None:
    with pytest.raises(DataMutationABIError, match="sakla"):
        DataMutationABI(command="sil", model="Urun", value_slot="urun")


def test_data_mutation_abi_rejects_unsafe_identifiers() -> None:
    with pytest.raises(DataMutationABIError, match="model"):
        DataMutationABI(command="sakla", model="../Urun", value_slot="urun")

    with pytest.raises(DataMutationABIError, match="value slot"):
        DataMutationABI(command="sakla", model="Urun", value_slot="")
