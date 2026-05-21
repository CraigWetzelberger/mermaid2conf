"""Section-level diffing for Confluence HTML content."""

from __future__ import annotations

import html as html_mod
import re
from dataclasses import dataclass

# Matches h1, h2, h3 opening tags
_HEADING_RE = re.compile(r"<(h[123])[^>]*>", re.IGNORECASE)
_TAG_STRIP_RE = re.compile(r"<[^>]+>")


@dataclass
class Section:
    """A heading-delimited section of HTML."""

    level: int  # 1, 2, or 3
    title: str
    content: str  # full HTML including the heading tag itself


def parse_sections(html: str) -> list[Section]:
    """Split HTML into sections by h1/h2/h3 headings."""
    positions: list[tuple[int, int, str]] = []  # (start, level, title)
    for m in _HEADING_RE.finditer(html):
        level = int(m.group(1)[1])
        # Find closing tag
        close_tag = f"</{m.group(1)}>"
        close_idx = html.find(close_tag, m.end())
        if close_idx == -1:
            continue
        title = html_mod.unescape(
            _TAG_STRIP_RE.sub("", html[m.start() : close_idx + len(close_tag)]).strip()
        )
        positions.append((m.start(), level, title))

    if not positions:
        return [Section(level=0, title="", content=html)] if html.strip() else []

    sections: list[Section] = []
    # Content before first heading
    if positions[0][0] > 0:
        preamble = html[: positions[0][0]]
        if preamble.strip():
            sections.append(Section(level=0, title="", content=preamble))

    for i, (start, level, title) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(html)
        sections.append(Section(level=level, title=title, content=html[start:end]))

    return sections


def _normalize(html: str) -> str:
    """Normalize HTML for comparison: collapse whitespace, normalize image tags."""
    # Normalize ac:image blocks to just the filename
    html = re.sub(
        r"<ac:image[^>]*>\s*<ri:attachment[^>]*ri:filename=\"([^\"]+)\"[^/]*/>\s*</ac:image>",
        r"IMG[\1]",
        html,
    )
    # Normalize raw <img> tags to the same canonical form (basename only)
    def _img_to_canonical(m: re.Match[str]) -> str:
        src = re.search(r'src="([^"]+)"', m.group(0))
        if src:
            fname = src.group(1).rsplit("/", 1)[-1]
            return f"IMG[{fname}]"
        return m.group(0)

    html = re.sub(r"<img[^>]*/>|<img[^>]*>", _img_to_canonical, html)
    html = html_mod.unescape(html)
    return re.sub(r"\s+", " ", html).strip()


def preserve_image_markup(new_html: str, published_html: str) -> str:
    """Replace simple ac:image tags in new_html with the richer published versions."""
    # Build map of filename -> full published ac:image tag
    pub_images: dict[str, str] = {}
    for m in re.finditer(
        r"<ac:image[^>]*>.*?</ac:image>", published_html, re.DOTALL
    ):
        fname = re.search(r'ri:filename="([^"]+)"', m.group(0))
        if fname:
            pub_images[fname.group(1)] = m.group(0)

    def _replace(match: re.Match[str]) -> str:
        fname = re.search(r'ri:filename="([^"]+)"', match.group(0))
        if fname and fname.group(1) in pub_images:
            return pub_images[fname.group(1)]
        return match.group(0)

    return re.sub(r"<ac:image[^>]*>.*?</ac:image>", _replace, new_html, flags=re.DOTALL)


@dataclass
class DiffResult:
    """Result of comparing local vs published sections."""

    changed: list[str]  # section titles that differ
    unchanged: list[str]  # section titles that match
    is_full_replacement: bool  # True if target h1 section not found or >80% different


def diff_sections(local_html: str, published_section_html: str) -> DiffResult:
    """Compare local HTML against the published h1 section content.

    Splits both into sub-sections (h2/h3) and reports which changed.
    """
    local_secs = [s for s in parse_sections(local_html) if s.level >= 2]
    pub_secs = [s for s in parse_sections(published_section_html) if s.level >= 2]

    # Build lookup of published sections by normalized title
    pub_map: dict[str, str] = {}
    for s in pub_secs:
        if s.title:
            pub_map[s.title.lower()] = _normalize(s.content)

    changed: list[str] = []
    unchanged: list[str] = []

    for s in local_secs:
        if not s.title:
            continue
        key = s.title.lower()
        pub_content = pub_map.get(key)
        if pub_content is None:
            changed.append(s.title)
        elif _normalize(s.content) == pub_content:
            unchanged.append(s.title)
        else:
            changed.append(s.title)

    # Full replacement if no published sub-sections matched at all
    is_full = len(pub_secs) > 0 and len(unchanged) == 0 and len(local_secs) > 0

    return DiffResult(changed=changed, unchanged=unchanged, is_full_replacement=is_full)


def merge_incremental(
    published_section_html: str, local_html: str, changed_titles: list[str]
) -> str:
    """Replace only the changed sub-sections within the published section HTML."""
    local_secs = parse_sections(local_html)
    local_map: dict[str, Section] = {}
    for s in local_secs:
        if s.title:
            local_map[s.title.lower()] = s

    pub_secs = parse_sections(published_section_html)
    changed_set = {t.lower() for t in changed_titles}

    result_parts: list[str] = []
    pub_titles_seen: set[str] = set()

    for s in pub_secs:
        key = s.title.lower() if s.title else ""
        if key and key in changed_set and key in local_map:
            result_parts.append(local_map[key].content)
            pub_titles_seen.add(key)
        else:
            result_parts.append(s.content)
            if key:
                pub_titles_seen.add(key)

    # Append new sections not in published
    for s in local_secs:
        if s.title and s.title.lower() not in pub_titles_seen:
            result_parts.append(s.content)

    return "".join(result_parts)
