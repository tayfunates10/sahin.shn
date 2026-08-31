from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .lexer import LexerError, tokenize
from .parser import ParserError, parse
from .runtime import Runtime, RuntimeErrorSHN


def _run(path: Path) -> int:
    try:
        source = path.read_text(encoding="utf-8")
        program = parse(tokenize(source))
        Runtime().execute(program)
        return 0
    except FileNotFoundError:
        print(f"Dosya bulunamadı: {path}", file=sys.stderr)
    except (LexerError, ParserError, RuntimeErrorSHN) as exc:
        print(f"Şahin hatası: {exc}", file=sys.stderr)
    return 1


def _scan(path: Path) -> int:
    try:
        source = path.read_text(encoding="utf-8")
        for token in tokenize(source):
            print(token)
        return 0
    except (FileNotFoundError, LexerError) as exc:
        print(f"Şahin hatası: {exc}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="şahin", description="Şahin programlama dili araç zinciri")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("çalıştır", aliases=["calistir"], help="Bir .shn dosyasını çalıştır")
    run.add_argument("dosya", type=Path)

    scan = sub.add_parser("tara", help="Kaynak kodun token akışını göster")
    scan.add_argument("dosya", type=Path)

    args = parser.parse_args(argv)
    if args.command in {"çalıştır", "calistir"}:
        return _run(args.dosya)
    if args.command == "tara":
        return _scan(args.dosya)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
