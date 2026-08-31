import pytest

from sahin.capabilities import Capability, CapabilityError, CapabilitySet
from sahin.lexer import tokenize
from sahin.parser import parse
from sahin.semantics import TypeKind, analyze


def codes(source: str) -> set[str]:
    return {item.code for item in analyze(parse(tokenize(source))).diagnostics}


def test_explicit_flow_contract_accepts_compatible_types():
    source = """akış ikiKat değer: sayı -> sayı
    ver değer * 2

sonuç = ikiKat 4
"""
    model = analyze(parse(tokenize(source)))
    assert model.ok, [d.format() for d in model.diagnostics]
    assert model.global_symbols["sonuç"].type_kind is TypeKind.SAYI


def test_flow_parameter_type_mismatch_is_rejected():
    source = """akış ikiKat değer: sayı -> sayı
    ver değer * 2

sonuç = ikiKat "dört"
"""
    assert "SHN-T102" in codes(source)


def test_flow_return_type_mismatch_is_rejected():
    source = """akış sayıVer -> sayı
    ver "yanlış"
"""
    assert "SHN-T103" in codes(source)


def test_assignment_cannot_silently_change_inferred_type():
    assert "SHN-T201" in codes('değer = 10\ndeğer = "on"\n')


def test_bound_value_remains_immutable():
    assert "SHN-S201" in codes('kaynak = 10\nbağlı <- kaynak\nbağlı = 11\n')


def test_member_access_on_yok_is_rejected_with_location():
    model = analyze(parse(tokenize("profil = yok\nyaz profil.ad\n")))
    diagnostic = next(d for d in model.diagnostics if d.code == "SHN-T301")
    assert diagnostic.location is not None
    assert "önce değerin varlığını doğrulayın" in diagnostic.message


def test_incompatible_arithmetic_is_rejected():
    assert "SHN-T407" in codes('sonuç = "metin" - 3\n')


def test_incompatible_ordered_comparison_is_rejected():
    assert "SHN-T406" in codes('"a" < 2 ise\n    yaz "olmaz"\n')


def test_numeric_widening_is_safe_and_deterministic():
    source = """akış oran değer: ondalık -> ondalık
    ver değer / 2

sonuç = oran 5
"""
    model = analyze(parse(tokenize(source)))
    assert model.ok, [d.format() for d in model.diagnostics]
    assert model.global_symbols["sonuç"].type_kind is TypeKind.ONDALIK


def test_capabilities_are_default_deny():
    capabilities = CapabilitySet()
    for capability in Capability:
        assert not capabilities.allows(capability)
        with pytest.raises(CapabilityError, match="SHN-G001"):
            capabilities.require(capability)


def test_capability_grant_is_explicit_and_revocable():
    capabilities = CapabilitySet().grant(Capability.DOSYA_OKU)
    capabilities.require(Capability.DOSYA_OKU)
    assert not capabilities.allows(Capability.DOSYA_YAZ)
    capabilities.revoke(Capability.DOSYA_OKU)
    with pytest.raises(CapabilityError):
        capabilities.require(Capability.DOSYA_OKU)


def test_many_reassignments_preserve_type_invariant():
    for number in range(100):
        source = f"değer = {number}\ndeğer = {number + 1}\n"
        assert analyze(parse(tokenize(source))).ok

    for number in range(25):
        source = f'değer = {number}\ndeğer = "{number}"\n'
        assert "SHN-T201" in codes(source)
