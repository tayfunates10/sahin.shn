from sahin.lexer import tokenize
from sahin.tokens import TokenKind


def test_comparison_operators_are_atomic_tokens():
    tokens = tokenize("a <= 1\nb >= 2\nc == 3\nd != 4\n")
    operators = [token.value for token in tokens if token.kind is TokenKind.OPERATOR]

    assert operators == ["<=", ">=", "==", "!="]
