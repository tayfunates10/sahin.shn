from __future__ import annotations

from dataclasses import dataclass
import unicodedata

from .lexer import Lexer
from .parser import Parser
from .semantics import SemanticAnalyzer


@dataclass(frozen=True, slots=True)
class LintDiagnostic:
    rule: str
    message: str
    line: int | None = None
    column: int | None = None
    severity: str = "hata"

    def format(self) -> str:
        if self.line is None or self.column is None:
            return f"{self.rule}: {self.message}"
        return f"{self.rule} · Satır {self.line}, sütun {self.column}: {self.message}"


def format_source(source: str) -> str:
    """Şahin kaynak metnini anlamsal girintiyi değiştirmeden kanonikleştirir.

    İlk formatter çekirdeği bilinçli olarak konservatiftir: satır sonlarını ve
    Unicode'u normalize eder, satır sonu boşluklarını kaldırır, boş satır
    tekrarlarını tekilleştirir ve son newline'ı garanti eder. Girinti dil
    semantiğinin parçası olduğu için değiştirilmez; geçersiz girinti Lexer
    tarafından fail-closed reddedilir.
    """

    normalized = unicodedata.normalize(
        "NFC", source.replace("\r\n", "\n").replace("\r", "\n")
    )

    # Girinti kurallarını formatter'ın sessizce değiştirmesine izin verme.
    Lexer(normalized).tokenize()

    # Yalnızca satır sonundaki whitespace'i kanonikleştir; baştaki girinti
    # dil semantiğinin parçası olduğundan aynen korunur.
    lines = [line.rstrip() for line in normalized.split("\n")]
    output: list[str] = []
    previous_blank = False

    for line in lines:
        blank = line == ""
        if blank and previous_blank:
            continue
        output.append(line)
        previous_blank = blank

    while output and output[-1] == "":
        output.pop()

    return "\n".join(output) + "\n"


def lint_source(source: str) -> tuple[LintDiagnostic, ...]:
    """Kaynağı Şahin'in gerçek lexer/parser/semantic zinciriyle denetler.

    Linter ayrı bir dil semantiği üretmez. Sözdizimsel olarak geçersiz kaynak
    lexer/parser tarafından fail-closed reddedilir; geçerli AST için mevcut
    SemanticAnalyzer diagnostics'i kaynak konumu korunarak linter çıktısına
    dönüştürülür.
    """

    tokens = Lexer(source).tokenize()
    program = Parser(tokens).parse()
    model = SemanticAnalyzer().analyze(program)

    diagnostics: list[LintDiagnostic] = []
    for diagnostic in model.diagnostics:
        location = diagnostic.location
        diagnostics.append(
            LintDiagnostic(
                rule=diagnostic.code,
                message=diagnostic.message,
                line=location.line if location is not None else None,
                column=location.column if location is not None else None,
            )
        )
    return tuple(diagnostics)
