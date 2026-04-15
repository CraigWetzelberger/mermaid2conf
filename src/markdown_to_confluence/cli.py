"""Canonical command-line interface for Markdown to Confluence tooling."""

from __future__ import annotations

import argparse
import sys

from . import mermaid, processing, publish


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mermaid2conf",
        description="Process Markdown with Mermaid diagrams and publish it to Confluence.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    process_parser = subparsers.add_parser(
        "process",
        help="Render Mermaid diagrams and write processed Markdown output",
    )
    processing.add_arguments(process_parser)
    process_parser.set_defaults(handler=processing.run)

    publish_parser = subparsers.add_parser(
        "publish",
        help="Publish processed Markdown output to a Confluence page section",
    )
    publish.add_arguments(publish_parser)
    publish_parser.set_defaults(handler=publish.run)

    mermaid_parser = subparsers.add_parser(
        "mermaid",
        help="Render Mermaid blocks in a Markdown file to PNG attachments",
    )
    mermaid.add_arguments(mermaid_parser)
    mermaid_parser.set_defaults(handler=mermaid.run)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
