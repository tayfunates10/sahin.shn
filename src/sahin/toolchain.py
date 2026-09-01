from __future__ import annotations

import unicodedata

from .lexer import Lexer


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
