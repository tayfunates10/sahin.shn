from __future__ import annotations

from decimal import Decimal

from .ast_nodes import (
    Assignment,
    Binary,
    Call,
    Command,
    Declaration,
    FieldDeclaration,
    ForEach,
    IfStatement,
    Literal,
    MatchCase,
    MatchStatement,
    Member,
    Name,
    Parameter,
    Pipeline,
    PipelineStage,
    Predicate,
    Program,
    RangeExpression,
    SourceLocation,
    TryStatement,
    Unary,
    Write,
)
from .tokens import Token, TokenKind


class ParserError(ValueError):
    pass


_DECLARATIONS = {"uygulama", "ekran", "görünüm", "akış", "kayıt", "uç", "iş", "olay"}
_BINARY_PRECEDENCE = {
    "veya": 1,
    "ve": 2,
    "==": 3,
    "!=": 3,
    "<": 3,
    "<=": 3,
    ">": 3,
    ">=": 3,
    "..": 4,
    "+": 5,
    "-": 5,
    "*": 6,
    "/": 6,
    "%": 6,
}
_IMPLICIT_CALL_STOP = {"ise", "yoksa", "içinden", "göre", "yok", "boş", "değil"}


class Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.index = 0

    def parse(self) -> Program:
        statements = []
        while not self._at(TokenKind.EOF):
            if self._match(TokenKind.NEWLINE):
                continue
            if self._at(TokenKind.DEDENT):
                raise self._error(self._current(), "beklenmeyen blok kapanışı.")
            if self._at(TokenKind.INDENT):
                raise self._error(
                    self._current(), "bu satırdan önce blok açan bir ifade bekleniyordu."
                )
            statements.append(self._statement())
        return Program(tuple(statements))

    def _statement(self):
        if self._line_contains_keyword("ise"):
            return self._if_statement()

        first = self._expect(TokenKind.IDENTIFIER, "Bir Şahin ifadesi bekleniyordu.")

        if first.value in _DECLARATIONS:
            return self._declaration(first)
        if first.value == "her":
            return self._for_each(first)
        if first.value == "duruma":
            return self._match_statement(first)
        if first.value == "dene":
            return self._try_statement(first)
        if first.value == "yaz":
            expression = self._finish_expression_line(self._expression())
            return Write(expression, self._loc(first))

        if self._at(TokenKind.ASSIGN) or self._at(TokenKind.BIND):
            operator = self._advance()
            expression = self._finish_expression_line(self._expression())
            return Assignment(
                first.value,
                expression,
                binding=operator.kind is TokenKind.BIND,
                location=self._loc(first),
            )

        if self._match(TokenKind.COLON):
            return self._field_declaration(first)

        return self._command(first)

    def _declaration(self, keyword: Token) -> Declaration:
        kind = keyword.value
        name: str | None = None
        parameters: list[Parameter] = []
        header = []
        return_type: str | None = None

        if kind in {"uygulama", "ekran", "görünüm", "kayıt"}:
            name = self._expect(
                TokenKind.IDENTIFIER, f"{kind!r} sonrasında bir ad bekleniyordu."
            ).value

        elif kind == "akış":
            name = self._expect(
                TokenKind.IDENTIFIER, "'akış' sonrasında bir akış adı bekleniyordu."
            ).value
            parameters = self._flow_parameters()

            if self._match(TokenKind.FAT_ARROW):
                inline = self._expression()
                self._line_end()
                return Declaration(
                    kind=kind,
                    name=name,
                    parameters=tuple(parameters),
                    inline_expression=inline,
                    location=self._loc(keyword),
                )

            if self._match(TokenKind.ARROW):
                return_type = self._expect(
                    TokenKind.IDENTIFIER, "'->' sonrasında dönüş tipi bekleniyordu."
                ).value

        elif kind == "uç":
            name = self._expect(
                TokenKind.IDENTIFIER, "'uç' sonrasında yöntem adı bekleniyordu."
            ).value
            header = self._loose_header()

        elif kind == "iş":
            name = self._expect(
                TokenKind.IDENTIFIER, "'iş' sonrasında iş adı bekleniyordu."
            ).value
            header = self._loose_header()

        elif kind == "olay":
            header = self._loose_header()
            if header:
                name = self._expression_name(header[0])

        body = self._required_block()
        return Declaration(
            kind=kind,
            name=name,
            parameters=tuple(parameters),
            header=tuple(header),
            return_type=return_type,
            body=body,
            location=self._loc(keyword),
        )

    def _flow_parameters(self) -> list[Parameter]:
        result: list[Parameter] = []
        while not self._at_any(
            TokenKind.NEWLINE, TokenKind.ARROW, TokenKind.FAT_ARROW, TokenKind.EOF
        ):
            if self._match(TokenKind.COMMA):
                continue
            token = self._expect(
                TokenKind.IDENTIFIER, "Akış parametresi için bir ad bekleniyordu."
            )
            type_name = None
            if self._match(TokenKind.COLON):
                type_name = self._expect(
                    TokenKind.IDENTIFIER, "':' sonrasında parametre tipi bekleniyordu."
                ).value
            result.append(Parameter(token.value, type_name, self._loc(token)))
        return result

    def _loose_header(self) -> list:
        values = []
        while not self._at_any(TokenKind.NEWLINE, TokenKind.EOF):
            if self._match(TokenKind.COMMA):
                continue
            values.append(
                self._expression(
                    allow_pipeline=False,
                    allow_implicit_call=False,
                    stop_kinds={TokenKind.COMMA, TokenKind.NEWLINE},
                )
            )
        return values

    def _field_declaration(self, first: Token) -> FieldDeclaration:
        type_token = self._expect(
            TokenKind.IDENTIFIER, "Alan için bir tip adı bekleniyordu."
        )
        modifiers: list[str] = []
        while self._at(TokenKind.IDENTIFIER):
            modifiers.append(self._advance().value)
        self._line_end()
        return FieldDeclaration(
            first.value, type_token.value, tuple(modifiers), self._loc(first)
        )

    def _if_statement(self) -> IfStatement:
        start = self._current()
        condition = self._expression(
            stop_words={"ise", "yok", "boş", "değil"}, allow_implicit_call=True
        )

        if self._match_keyword("yok"):
            condition = Predicate(condition, "yok", self._loc(start))
        elif self._match_keyword("boş"):
            predicate = "boş_değil" if self._match_keyword("değil") else "boş"
            condition = Predicate(condition, predicate, self._loc(start))

        self._expect_keyword("ise", "Koşulun sonunda 'ise' bekleniyordu.")
        body = self._required_block()

        else_body = ()
        if self._match_keyword("yoksa"):
            else_body = self._required_block()

        return IfStatement(condition, body, else_body, self._loc(start))

    def _for_each(self, first: Token) -> ForEach:
        variable = self._expect(
            TokenKind.IDENTIFIER, "'her' sonrasında yineleme adı bekleniyordu."
        )
        self._match_keyword("içinden")
        iterable = self._expression()
        body = self._required_block()
        return ForEach(variable.value, iterable, body, self._loc(first))

    def _match_statement(self, first: Token) -> MatchStatement:
        self._expect_keyword("göre", "'duruma' sonrasında 'göre' bekleniyordu.")
        subject = self._expression()
        self._line_end()
        self._expect(
            TokenKind.INDENT,
            "'duruma göre' sonrasında girintili eşleşme bloğu bekleniyordu.",
        )

        cases: list[MatchCase] = []
        while not self._at_any(TokenKind.DEDENT, TokenKind.EOF):
            if self._match(TokenKind.NEWLINE):
                continue
            pattern_start = self._current()
            pattern = self._expression(
                allow_pipeline=False,
                allow_implicit_call=False,
                stop_kinds={TokenKind.ARROW},
            )
            self._expect(TokenKind.ARROW, "Eşleşme kolunda '->' bekleniyordu.")
            command_first = self._expect(
                TokenKind.IDENTIFIER,
                "'->' sonrasında çalıştırılacak komut bekleniyordu.",
            )
            statement = self._command(command_first, allow_block=False)
            cases.append(MatchCase(pattern, statement, self._loc(pattern_start)))

        self._expect(TokenKind.DEDENT, "Eşleşme bloğu düzgün kapanmadı.")
        return MatchStatement(subject, tuple(cases), self._loc(first))

    def _try_statement(self, first: Token) -> TryStatement:
        body = self._required_block()
        self._expect_keyword(
            "olmazsa", "'dene' bloğundan sonra 'olmazsa' bekleniyordu."
        )
        error_name = self._advance().value if self._at(TokenKind.IDENTIFIER) else None
        except_body = self._required_block()
        return TryStatement(body, error_name, except_body, self._loc(first))

    def _command(self, first: Token, *, allow_block: bool = True) -> Command:
        subject = None
        name = first.value

        if self._at(TokenKind.DOT):
            subject = self._member_tail(Name(first.value, self._loc(first)))
            verb = self._expect(
                TokenKind.IDENTIFIER,
                "Nesne ifadesinden sonra uygulanacak Şahin eylemi bekleniyordu.",
            )
            name = verb.value

        arguments = []
        while not self._at_any(
            TokenKind.NEWLINE, TokenKind.EOF, TokenKind.ARROW, TokenKind.DEDENT
        ):
            if self._match(TokenKind.COMMA):
                continue
            arguments.append(
                self._expression(
                    allow_pipeline=True,
                    allow_implicit_call=False,
                    stop_kinds={
                        TokenKind.COMMA,
                        TokenKind.NEWLINE,
                        TokenKind.ARROW,
                        TokenKind.DEDENT,
                    },
                )
            )

        arrow = None
        if self._match(TokenKind.ARROW):
            arrow = self._expression(allow_implicit_call=True)

        self._line_end()
        body = self._indented_body() if allow_block and self._at(TokenKind.INDENT) else ()

        return Command(
            name=name,
            arguments=tuple(arguments),
            subject=subject,
            arrow=arrow,
            body=body,
            location=self._loc(first),
        )

    def _expression(
        self,
        min_precedence: int = 0,
        *,
        allow_pipeline: bool = True,
        allow_implicit_call: bool = True,
        stop_words: set[str] | None = None,
        stop_kinds: set[TokenKind] | None = None,
    ):
        stop_words = stop_words or set()
        stop_kinds = stop_kinds or set()

        left = self._unary(
            allow_implicit_call=allow_implicit_call,
            stop_words=stop_words,
            stop_kinds=stop_kinds,
        )

        while True:
            if self._current().kind in stop_kinds:
                break
            if self._at(TokenKind.IDENTIFIER) and self._current().value in stop_words:
                break

            operator = None
            precedence = None
            if self._at(TokenKind.OPERATOR):
                operator = self._current().value
                precedence = _BINARY_PRECEDENCE.get(operator)
            elif self._at(TokenKind.RANGE):
                operator = ".."
                precedence = _BINARY_PRECEDENCE[".."]
            elif self._at(TokenKind.IDENTIFIER) and self._current().value in {"ve", "veya"}:
                operator = self._current().value
                precedence = _BINARY_PRECEDENCE[operator]

            if operator is not None and precedence is not None:
                if precedence < min_precedence:
                    break
                op_token = self._advance()
                right = self._expression(
                    precedence + 1,
                    allow_pipeline=False,
                    allow_implicit_call=allow_implicit_call,
                    stop_words=stop_words,
                    stop_kinds=stop_kinds,
                )
                left = (
                    RangeExpression(left, right, self._loc(op_token))
                    if operator == ".."
                    else Binary(left, operator, right, self._loc(op_token))
                )
                continue

            if allow_pipeline and self._match(TokenKind.PIPE):
                stage = self._pipeline_stage()
                if isinstance(left, Pipeline):
                    left = Pipeline(left.source, (*left.stages, stage), left.location)
                else:
                    left = Pipeline(left, (stage,), self._loc_from_expression(left))
                continue

            break

        return left

    def _unary(
        self,
        *,
        allow_implicit_call: bool,
        stop_words: set[str],
        stop_kinds: set[TokenKind],
    ):
        if self._at(TokenKind.OPERATOR) and self._current().value in {"-", "+", "!"}:
            token = self._advance()
            return Unary(
                token.value,
                self._unary(
                    allow_implicit_call=allow_implicit_call,
                    stop_words=stop_words,
                    stop_kinds=stop_kinds,
                ),
                self._loc(token),
            )

        if self._match_keyword("değil"):
            token = self.tokens[self.index - 1]
            return Unary(
                "değil",
                self._unary(
                    allow_implicit_call=allow_implicit_call,
                    stop_words=stop_words,
                    stop_kinds=stop_kinds,
                ),
                self._loc(token),
            )

        return self._postfix(
            allow_implicit_call=allow_implicit_call,
            stop_words=stop_words,
            stop_kinds=stop_kinds,
        )

    def _postfix(
        self,
        *,
        allow_implicit_call: bool,
        stop_words: set[str],
        stop_kinds: set[TokenKind],
    ):
        expression = self._primary(stop_words=stop_words, stop_kinds=stop_kinds)

        while True:
            if self._match(TokenKind.DOT):
                member = self._expect(
                    TokenKind.IDENTIFIER, "'.' sonrasında üye adı bekleniyordu."
                )
                expression = Member(expression, member.value, self._loc(member))
                continue

            if self._match(TokenKind.LPAREN):
                arguments = []
                while not self._at_any(TokenKind.RPAREN, TokenKind.EOF):
                    if self._match(TokenKind.COMMA):
                        continue
                    arguments.append(
                        self._expression(
                            stop_kinds={TokenKind.COMMA, TokenKind.RPAREN}
                        )
                    )
                self._expect(TokenKind.RPAREN, "Çağrı için ')' bekleniyordu.")
                expression = Call(
                    expression, tuple(arguments), self._loc_from_expression(expression)
                )
                continue

            if (
                allow_implicit_call
                and self._can_start_primary()
                and not (
                    self._at(TokenKind.IDENTIFIER)
                    and self._current().value in (_IMPLICIT_CALL_STOP | stop_words)
                )
            ):
                argument = self._postfix(
                    allow_implicit_call=False,
                    stop_words=stop_words,
                    stop_kinds=stop_kinds,
                )
                if isinstance(expression, Call):
                    expression = Call(
                        expression.callee,
                        (*expression.arguments, argument),
                        expression.location,
                    )
                else:
                    expression = Call(
                        expression, (argument,), self._loc_from_expression(expression)
                    )
                continue
            break

        return expression

    def _primary(self, *, stop_words: set[str], stop_kinds: set[TokenKind]):
        token = self._current()
        if token.kind in stop_kinds:
            raise self._error(token, "ifade bekleniyordu.")

        if token.kind is TokenKind.STRING:
            self._advance()
            return Literal(token.value, self._loc(token))
        if token.kind is TokenKind.NUMBER:
            self._advance()
            raw = token.value
            if raw.endswith("₺"):
                value = Decimal(raw[:-1])
            elif "." in raw:
                value = Decimal(raw)
            else:
                value = int(raw)
            return Literal(value, self._loc(token))
        if token.kind is TokenKind.IDENTIFIER:
            if token.value in stop_words:
                raise self._error(token, "ifade bekleniyordu.")
            self._advance()
            constants = {"evet": True, "hayır": False, "yok": None}
            if token.value in constants:
                return Literal(constants[token.value], self._loc(token))
            return Name(token.value, self._loc(token))
        if token.kind is TokenKind.LPAREN:
            self._advance()
            expression = self._expression()
            self._expect(TokenKind.RPAREN, "Gruplanmış ifade için ')' bekleniyordu.")
            return expression

        raise self._error(token, "değer, isim veya gruplanmış ifade bekleniyordu.")

    def _pipeline_stage(self) -> PipelineStage:
        name = self._expect(
            TokenKind.IDENTIFIER, "'|' sonrasında veri hattı aşaması bekleniyordu."
        )
        arguments = []
        while not self._at_any(
            TokenKind.PIPE, TokenKind.NEWLINE, TokenKind.DEDENT, TokenKind.EOF
        ):
            if self._match(TokenKind.COMMA):
                continue
            arguments.append(
                self._expression(
                    allow_pipeline=False,
                    allow_implicit_call=False,
                    stop_kinds={
                        TokenKind.COMMA,
                        TokenKind.PIPE,
                        TokenKind.NEWLINE,
                        TokenKind.DEDENT,
                    },
                )
            )
        return PipelineStage(name.value, tuple(arguments), self._loc(name))

    def _finish_expression_line(self, expression):
        self._line_end()
        if self._at(TokenKind.INDENT) and self._peek_kind(1) is TokenKind.PIPE:
            self._advance()
            stages = list(expression.stages) if isinstance(expression, Pipeline) else []
            source = expression.source if isinstance(expression, Pipeline) else expression
            while self._at(TokenKind.PIPE):
                self._advance()
                stages.append(self._pipeline_stage())
                self._line_end()
            self._expect(
                TokenKind.DEDENT, "Çok satırlı veri hattı girintisi düzgün kapanmadı."
            )
            return Pipeline(source, tuple(stages), self._loc_from_expression(source))
        return expression

    def _required_block(self) -> tuple:
        self._line_end()
        self._expect(
            TokenKind.INDENT, "Bu ifade için 4 boşluk girintili bir blok bekleniyordu."
        )
        return self._indented_body(already_open=True)

    def _indented_body(self, *, already_open: bool = False) -> tuple:
        if not already_open:
            self._expect(TokenKind.INDENT, "Girintili blok bekleniyordu.")
        statements = []
        while not self._at_any(TokenKind.DEDENT, TokenKind.EOF):
            if self._match(TokenKind.NEWLINE):
                continue
            statements.append(self._statement())
        self._expect(TokenKind.DEDENT, "Blok düzgün kapanmadı.")
        return tuple(statements)

    def _line_end(self) -> None:
        if self._match(TokenKind.NEWLINE) or self._at(TokenKind.EOF):
            return
        raise self._error(self._current(), "ifade sonunda yeni satır bekleniyordu.")

    def _member_tail(self, expression):
        while self._match(TokenKind.DOT):
            member = self._expect(
                TokenKind.IDENTIFIER, "'.' sonrasında üye adı bekleniyordu."
            )
            expression = Member(expression, member.value, self._loc(member))
        return expression

    def _line_contains_keyword(self, value: str) -> bool:
        i = self.index
        while i < len(self.tokens):
            token = self.tokens[i]
            if token.kind in {TokenKind.NEWLINE, TokenKind.EOF}:
                return False
            if token.kind is TokenKind.IDENTIFIER and token.value == value:
                return True
            i += 1
        return False

    def _expression_name(self, expression) -> str | None:
        if isinstance(expression, Name):
            return expression.value
        if isinstance(expression, Member):
            prefix = self._expression_name(expression.target)
            return f"{prefix}.{expression.name}" if prefix else expression.name
        return None

    @staticmethod
    def _loc_from_expression(expression) -> SourceLocation | None:
        return getattr(expression, "location", None)

    @staticmethod
    def _loc(token: Token) -> SourceLocation:
        return SourceLocation(token.line, token.column)

    def _current(self) -> Token:
        return self.tokens[self.index]

    def _peek_kind(self, offset: int) -> TokenKind:
        position = min(self.index + offset, len(self.tokens) - 1)
        return self.tokens[position].kind

    def _advance(self) -> Token:
        token = self._current()
        if token.kind is not TokenKind.EOF:
            self.index += 1
        return token

    def _at(self, kind: TokenKind) -> bool:
        return self._current().kind is kind

    def _at_any(self, *kinds: TokenKind) -> bool:
        return self._current().kind in kinds

    def _match(self, kind: TokenKind) -> bool:
        if self._at(kind):
            self._advance()
            return True
        return False

    def _at_keyword(self, value: str) -> bool:
        return self._at(TokenKind.IDENTIFIER) and self._current().value == value

    def _match_keyword(self, value: str) -> bool:
        if self._at_keyword(value):
            self._advance()
            return True
        return False

    def _expect_keyword(self, value: str, message: str) -> Token:
        if self._at_keyword(value):
            return self._advance()
        raise self._error(self._current(), message)

    def _expect(self, kind: TokenKind, message: str) -> Token:
        if self._at(kind):
            return self._advance()
        raise self._error(self._current(), message)

    def _can_start_primary(self) -> bool:
        return self._current().kind in {
            TokenKind.IDENTIFIER,
            TokenKind.NUMBER,
            TokenKind.STRING,
            TokenKind.LPAREN,
        }

    @staticmethod
    def _error(token: Token, message: str) -> ParserError:
        return ParserError(f"Satır {token.line}, sütun {token.column}: {message}")


def parse(tokens: list[Token]) -> Program:
    return Parser(tokens).parse()
