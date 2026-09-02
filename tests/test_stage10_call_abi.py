from __future__ import annotations

import pytest

from sahin.ir import IRLoweringError, lower_source


def test_call_stays_fail_closed_until_flow_declaration_abi_is_lowered():
    source = """akış iki_katı x
    ver x * 2
sonuç = iki_katı(3)
yaz sonuç
"""

    with pytest.raises(IRLoweringError, match="Declaration"):
        lower_source(source)


def test_call_is_not_silently_lowered_without_callee_abi():
    source = "değer = 1\nsonuç = değer(2)\n"

    with pytest.raises(IRLoweringError, match="Call"):
        lower_source(source)
