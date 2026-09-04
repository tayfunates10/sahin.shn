import pytest

from sahin.ir import IRLoweringError, lower_source


def test_increment_command_stays_fail_closed_until_mutation_abi_exists():
    source = """stok = 3
stok artır 1
"""
    with pytest.raises(IRLoweringError, match=r"'artır' Command düğümünü"):
        lower_source(source)


def test_decrement_command_stays_fail_closed_until_mutation_abi_exists():
    source = """stok = 3
stok azalt 1
"""
    with pytest.raises(IRLoweringError, match=r"'azalt' Command düğümünü"):
        lower_source(source)


def test_host_effect_command_stays_fail_closed():
    with pytest.raises(IRLoweringError, match=r"'sakla' Command düğümünü"):
        lower_source("sakla ürün\n")


def test_return_command_is_rejected_outside_flow():
    with pytest.raises(IRLoweringError, match=r"'ver' Command düğümünü"):
        lower_source("ver 1\n")


def test_break_command_is_rejected_outside_loop():
    with pytest.raises(IRLoweringError, match=r"'bitir' Command düğümünü"):
        lower_source("bitir\n")
