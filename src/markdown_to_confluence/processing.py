#!/usr/bin/env python3
"""Convenience CLI for processing markdown before publishing."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .mermaid import convert_markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kiro-publish-processing")
    parser.add_argument("source_md", type=Path, help="Source markdown file")
    parser.add_argument(
        "output_dir",
        nargs="?",
        type=Path,
        default=Path.cwd() / "output",
        help="Directory for generated markdown and PNG files",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    source_path = args.source_md.expanduser().resolve()
    output_path = args.output_dir.expanduser()
    result = convert_markdown(source_path, output_path)
    print(f"Converted: {result}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
