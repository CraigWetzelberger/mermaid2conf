"""Resolve local spec-path markdown links to Confluence URLs."""

from __future__ import annotations

import re
from pathlib import Path

# Files to check (in order) when a link points to a spec directory
_CANDIDATES = ("design.md", "requirements.md")


def _extract_confluence_url(path: Path) -> str | None:
    """Return the confluence_url from a markdown file's YAML frontmatter."""
    try:
        text = path.read_text()
    except OSError:
        return None
    fm = re.match(r"^---\n(.*?\n)---\n", text, re.DOTALL)
    if not fm:
        return None
    for line in fm.group(1).splitlines():
        if line.startswith("confluence_url:"):
            return line.split(":", 1)[1].strip()
    return None


def _resolve_spec_path(target: Path) -> str | None:
    """Resolve a spec path (file or directory) to a Confluence URL."""
    if target.is_file():
        return _extract_confluence_url(target)
    if target.is_dir():
        for candidate in _CANDIDATES:
            url = _extract_confluence_url(target / candidate)
            if url:
                return url
    return None


_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}


def _find_specs_dir(source_file: Path) -> Path | None:
    """Walk up from source_file to find the .kiro/specs/ directory."""
    current = source_file.parent.resolve()
    while current != current.parent:
        if current.name == "specs" and current.parent.name == ".kiro":
            return current
        current = current.parent
    return None


def _resolve_inline_spec_names(content: str, source_file: Path) -> str:
    """Convert backtick-quoted spec directory names to Confluence links."""
    specs_dir = _find_specs_dir(source_file)
    if not specs_dir:
        return content

    # Build map of spec directory names to Confluence URLs
    spec_urls: dict[str, str] = {}
    for d in specs_dir.iterdir():
        if d.is_dir():
            url = _resolve_spec_path(d)
            if url:
                spec_urls[d.name] = url

    if not spec_urls:
        return content

    def _replace_inline(match: re.Match[str]) -> str:
        name = match.group(1)
        if name in spec_urls:
            return f"[{name}]({spec_urls[name]})"
        return match.group(0)

    # Match `spec-name` that corresponds to a known spec directory
    pattern = r"`(" + "|".join(re.escape(k) for k in spec_urls) + r")`"
    return re.sub(pattern, _replace_inline, content)


def resolve_spec_links(content: str, source_file: Path) -> str:
    """Replace markdown links and inline spec names with Confluence URLs."""

    # First resolve inline backtick spec names
    content = _resolve_inline_spec_names(content, source_file)

    def _replace(match: re.Match[str]) -> str:
        label, target = match.group(1), match.group(2)
        # Skip URLs and anchors
        if re.match(r"(https?://|#)", target):
            return match.group(0)
        # Skip image file extensions
        if Path(target).suffix.lower() in _IMAGE_EXTS:
            return match.group(0)
        path = Path(target).expanduser()
        if not path.is_absolute():
            path = (source_file.parent / path).resolve()
        url = _resolve_spec_path(path)
        if url:
            return f"[{label}]({url})"
        return match.group(0)

    # Match [text](target) but NOT ![alt](target) (image syntax)
    return re.sub(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)", _replace, content)
