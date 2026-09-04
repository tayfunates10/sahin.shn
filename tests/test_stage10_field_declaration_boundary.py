import pytest

from sahin.ir import IRLoweringError, lower_source


def test_top_level_field_declaration_is_not_silently_lowered():
    with pytest.raises(IRLoweringError, match=r"FieldDeclaration düğümünü desteklemiyor"):
        lower_source("ad: yazı\n")


def test_record_declaration_is_not_silently_erased_before_metadata_abi_exists():
    source = """kayıt Kullanıcı
    ad: yazı gerekli
    eposta: eposta gerekli benzersiz
"""

    with pytest.raises(IRLoweringError, match=r"'kayıt' Declaration ABI'ını desteklemiyor"):
        lower_source(source)
