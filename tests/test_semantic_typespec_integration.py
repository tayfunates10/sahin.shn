from sahin.lexer import tokenize
from sahin.parser import parse
from sahin.semantics import TypeKind, analyze


def _codes(source: str) -> list[str]:
    model = analyze(parse(tokenize(source)))
    return [diagnostic.code for diagnostic in model.diagnostics]


def test_optional_contract_reaches_main_semantic_symbol():
    source = """akış selam ad: yazı veya yok -> yazı
    ver "merhaba"
"""
    model = analyze(parse(tokenize(source)))
    flow = model.global_symbols["selam"]

    assert model.ok
    assert flow.parameter_specs[0].members == frozenset({TypeKind.YAZI, TypeKind.YOK})
    assert flow.return_spec.members == frozenset({TypeKind.YAZI})


def test_optional_member_access_requires_yok_narrowing():
    source = """akış göster profil: yazı veya yok -> yazı
    yaz profil.uzunluk
    ver "tamam"
"""
    assert "SHN-T302" in _codes(source)


def test_yok_else_branch_narrows_optional_value_to_present_type():
    source = """akış göster profil: yazı veya yok -> yazı
    profil yok ise
        yaz "profil yok"
    yoksa
        yaz profil.uzunluk
    ver "tamam"
"""
    codes = _codes(source)
    assert "SHN-T302" not in codes
    assert "SHN-T301" not in codes


def test_optional_return_contract_accepts_present_and_yok_paths():
    present = """akış bul -> yazı veya yok
    ver "Tayfun"
"""
    absent = """akış bul -> yazı veya yok
    ver yok
"""

    assert analyze(parse(tokenize(present))).ok
    assert analyze(parse(tokenize(absent))).ok


def test_optional_assignment_rejects_unrelated_type_in_flow_scope():
    source = """akış değiştir değer: sayı veya yok -> sayı
    değer = "yanlış"
    ver 1
"""
    assert "SHN-T203" in _codes(source)
