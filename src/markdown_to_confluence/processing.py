#!/usr/bin/env python3
"""Convenience CLI for processing markdown before publishing."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .compat import warn_legacy_command
from .mermaid import convert_markdown


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("source_md", type=Path, help="Source markdown file")
    parser.add_argument(
        "output_dir",
        nargs="?",
        type=Path,
        default=Path.cwd() / "output",
        help="Directory for generated markdown and PNG files",
    )


def build_parser(prog: str = "kiro-publish-processing") -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=prog)
    add_arguments(parser)
    return parser


def run(args: argparse.Namespace) -> int:
    source_path = args.source_md.expanduser().resolve()
    output_path = args.output_dir.expanduser()
    result = convert_markdown(source_path, output_path)
    print(f"Converted: {result}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return run(args)


def legacy_main(argv: list[str] | None = None) -> int:
    warn_legacy_command("kiro-publish-processing", "mermaid2conf process")
    return main(argv)


if __name__ == "__main__":
    sys.exit(main())
