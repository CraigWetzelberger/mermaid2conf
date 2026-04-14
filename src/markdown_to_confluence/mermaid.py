#!/usr/bin/env python3
"""Render Mermaid blocks in markdown files to PNG attachments."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower().strip())
    return re.sub(r"[\s-]+", "_", text)[:60]


def extract_mermaid_blocks(content: str) -> list[tuple[str, str | None]]:
    results: list[tuple[str, str | None]] = []
    for match in re.finditer(r"```mermaid\n(.*?)```", content, re.DOTALL):
        preceding = content[: match.start()]
        heading = re.findall(r"^#+\s+(.+)$", preceding, re.MULTILINE)
        title = slugify(heading[-1]) if heading else None
        results.append((match.group(1), title))
    return results


def render_mermaid(code: str, output_path: Path) -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".mmd", delete=False) as handle:
        handle.write(code)
        mmd_path = Path(handle.name)

    try:
        subprocess.run(
            [
                "mmdc",
                "-i",
                str(mmd_path),
                "-o",
                str(output_path),
                "-s",
                "1.5",
                "-w",
                "1536",
            ],
            check=True,
        )
    finally:
        mmd_path.unlink(missing_ok=True)


def convert_markdown(input_file: Path, output_dir: Path) -> Path:
    content = input_file.read_text()
    blocks = extract_mermaid_blocks(content)

    output_dir.mkdir(parents=True, exist_ok=True)

    for index, (block, title) in enumerate(blocks):
        image_name = f"{title}_{index}.png" if title else f"mermaid_{index}.png"
        image_path = output_dir / image_name
        render_mermaid(block, image_path)
        content = content.replace(
            f"```mermaid\n{block}```", f"![Mermaid Diagram]({image_name})", 1
        )

    output_file = output_dir / input_file.name
    output_file.write_text(content)
    return output_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="md2conf-mermaid")
    parser.add_argument("input_file", type=Path, help="Markdown file to process")
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
    result = convert_markdown(args.input_file, args.output_dir)
    print(f"Converted: {result}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
