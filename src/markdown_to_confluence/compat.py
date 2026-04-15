"""Compatibility helpers for legacy command aliases."""

from __future__ import annotations

import sys


def warn_legacy_command(command_name: str, replacement: str) -> None:
    print(
        f"WARNING: `{command_name}` is deprecated; use `{replacement}` instead.",
        file=sys.stderr,
    )
