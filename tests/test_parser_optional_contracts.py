from sahin.lexer import tokenize
from sahin.parser import parse


def test_optional_parameter_contract_is_preserved_in_ast():
    program = parse(tokenize("akış selam ad: yazı veya yok -> yazı\n    ver \"merhaba\"\n"))
    flow = program.statements[0]
    assert flow.parameters[0].type_name == "yazı veya yok"
    assert flow.return_type == "yazı"


def test_optional_return_contract_is_preserved_in_ast():
    program = parse(tokenize("akış kullanıcıBul -> yazı veya yok\n    ver yok\n"))
    flow = program.statements[0]
    assert flow.return_type == "yazı veya yok"


def test_logical_or_remains_expression_operator_outside_type_context():
    program = parse(tokenize("sonuç = evet veya hayır\n"))
    expression = program.statements[0].expression
    assert expression.operator == "veya"


def test_optional_field_contract_keeps_modifiers_separate():
    program = parse(tokenize("kayıt Kullanıcı\n    takmaAd: yazı veya yok gerekli\n"))
    field = program.statements[0].body[0]
    assert field.type_name == "yazı veya yok"
    assert field.modifiers == ("gerekli",)
