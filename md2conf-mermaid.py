#!/usr/bin/env python3
"""Backward-compatible wrapper for the packaged Mermaid CLI."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from markdown_to_confluence.mermaid import main


if __name__ == "__main__":
    raise SystemExit(main())
