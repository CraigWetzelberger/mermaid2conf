#!/usr/bin/env python3
"""Publish processed markdown to a Confluence page section."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import mistune
import requests

from .compat import warn_legacy_command
from .diff_sections import diff_sections, merge_incremental, preserve_image_markup

CONFIG_FILENAME = "confluence_config.json"
DEFAULT_CONFIG_LOCATIONS = (
    Path.cwd() / CONFIG_FILENAME,
    Path.home() / ".config" / "mermaid2conf" / CONFIG_FILENAME,
)


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("page_id", help="Confluence page ID")
    parser.add_argument("section_heading", help="Section heading to replace or append")
    parser.add_argument(
        "output_dir",
        nargs="?",
        type=Path,
        default=Path.cwd() / "output",
        help="Directory containing processed markdown and PNG files",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to the Confluence config file",
    )


def build_parser(prog: str = "kiro-publish-to-confluence") -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=prog)
    add_arguments(parser)
    return parser


def find_config_path(explicit_path: Path | None) -> Path:
    if explicit_path is not None:
        return explicit_path.expanduser()

    env_path = os.environ.get("MARKDOWN_TO_CONFLUENCE_CONFIG")
    if env_path:
        return Path(env_path).expanduser()

    for candidate in DEFAULT_CONFIG_LOCATIONS:
        if candidate.exists():
            return candidate

    return DEFAULT_CONFIG_LOCATIONS[0]


def load_config(config_path: Path | None) -> tuple[dict[str, str], Path]:
    resolved_path = find_config_path(config_path)
    if not resolved_path.exists():
        default_locations = "\n".join(
            f"  - {path}" for path in DEFAULT_CONFIG_LOCATIONS
        )
        sys.exit(
            "ERROR: Config file not found.\n"
            f"Checked:\n{default_locations}\n"
            "Use --config to point to a config file containing:\n"
            '{\n  "confluence_url": "https://example.atlassian.net/wiki",\n'
            '  "username": "user@example.com",\n'
            '  "api_token": "<your-api-token>"\n}'
        )

    cfg = json.loads(resolved_path.read_text())
    missing = [
        key for key in ("confluence_url", "username", "api_token") if not cfg.get(key)
    ]
    if missing:
        sys.exit(
            f"ERROR: Missing config values: {', '.join(missing)}\n"
            f"Update {resolved_path} with your Confluence credentials."
        )
    return cfg, resolved_path


def make_session(cfg: dict[str, str]) -> tuple[requests.Session, str]:
    session = requests.Session()
    session.auth = (cfg["username"], cfg["api_token"])
    session.headers["X-Atlassian-Token"] = "nocheck"
    return session, cfg["confluence_url"].rstrip("/") + "/rest/api"


def check_auth(session: requests.Session, api: str, config_path: Path) -> None:
    response = session.get(f"{api}/user/current")
    if response.status_code in (401, 403):
        sys.exit(
            f"ERROR: Authentication failed (HTTP {response.status_code}).\n"
            f"Check your username and api_token in:\n  {config_path}"
        )
    response.raise_for_status()


def upload_attachments(
    session: requests.Session, api: str, page_id: str, output_dir: Path
) -> None:
    mime_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
    }
    # Fetch existing attachments with their sizes
    existing: dict[str, tuple[str, int]] = {}  # filename -> (id, size)
    resp = session.get(f"{api}/content/{page_id}/child/attachment", params={"limit": 200})
    if resp.status_code == 200:
        for att in resp.json().get("results", []):
            ext = att.get("extensions", {})
            existing[att["title"]] = (att["id"], ext.get("fileSize", -1))

    for img_path in sorted(
        p for ext in ("*.png", "*.jpg", "*.jpeg", "*.gif") for p in output_dir.glob(ext)
    ):
        local_size = img_path.stat().st_size
        mime = mime_types.get(img_path.suffix.lower(), "application/octet-stream")

        if img_path.name in existing:
            att_id, remote_size = existing[img_path.name]
            if local_size == remote_size:
                print(f"  Skipped (unchanged, {local_size} bytes): {img_path.name}")
                continue
            print(
                f"  Updating ({local_size} vs {remote_size} bytes): {img_path.name}"
            )
            with img_path.open("rb") as handle:
                session.post(
                    f"{api}/content/{page_id}/child/attachment/{att_id}/data",
                    files={"file": (img_path.name, handle, mime)},
                    data={"minorEdit": "true"},
                )
        else:
            print(f"  Uploading (new): {img_path.name}")
            with img_path.open("rb") as handle:
                session.post(
                    f"{api}/content/{page_id}/child/attachment",
                    files={"file": (img_path.name, handle, mime)},
                    data={"minorEdit": "true"},
                )


def md_to_confluence_html(md_path: Path) -> str:
    content = md_path.read_text()
    content = re.sub(r"^---\n.*?\n---\n", "", content, count=1, flags=re.DOTALL)
    content = re.sub(
        r"!\[[^\]]*\]\(([^)]+\.(?:png|jpe?g|gif))\)",
        lambda match: f"ACIMG|||{match.group(1)}|||ENDACIMG",
        content,
    )
    html = mistune.html(content)
    html = re.sub(
        r"ACIMG\|\|\|(.+?)\|\|\|ENDACIMG",
        r'<ac:image ac:width="760"><ri:attachment ri:filename="\1"/></ac:image>',
        html,
    )

    def pre_to_macro(match: re.Match[str]) -> str:
        lang_match = re.search(r'class="language-(\w+)"', match.group(1) or "")
        language = lang_match.group(1) if lang_match else ""
        code = (
            match.group(2)
            .replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", '"')
        )
        language_param = (
            f'<ac:parameter ac:name="language">{language}</ac:parameter>'
            if language
            else ""
        )
        return (
            '<ac:structured-macro ac:name="code" ac:schema-version="1">'
            f"{language_param}"
            f"<ac:plain-text-body><![CDATA[{code}]]></ac:plain-text-body>"
            "</ac:structured-macro>"
        )

    return re.sub(
        r"<pre><code([^>]*)>(.*?)</code></pre>", pre_to_macro, html, flags=re.DOTALL
    )


def _extract_h1_section(page_html: str, section: str) -> tuple[str | None, int, int]:
    """Extract the content of a specific h1 section. Returns (content, start, end)."""
    heading_pattern = re.compile(r"<h1[^>]*>", re.IGNORECASE)
    positions = [m.start() for m in heading_pattern.finditer(page_html)]
    for i, pos in enumerate(positions):
        end_h1 = page_html.index("</h1>", pos) + 5
        heading_text = re.sub(r"<[^>]+>", "", page_html[pos:end_h1]).strip()
        if heading_text.lower() == section.lower().strip():
            start = pos
            end = positions[i + 1] if i + 1 < len(positions) else len(page_html)
            return page_html[start:end], start, end
    return None, 0, 0


def publish(
    session: requests.Session, api: str, page_id: str, section: str, new_html: str
) -> None:
    response = session.get(
        f"{api}/content/{page_id}", params={"expand": "body.storage,version"}
    )
    response.raise_for_status()
    page = response.json()
    page_html = page["body"]["storage"]["value"]

    pub_section, sec_start, sec_end = _extract_h1_section(page_html, section)

    if pub_section is None:
        print(f"\n⚠️  Section '{section}' not found on the page.")
        print("This will be a COMPLETE NEW SECTION appended to the page.")
        answer = input("Proceed? [y/N] ").strip().lower()
        if answer != "y":
            print("Aborted.")
            return
        merged = page_html + new_html
    else:
        diff = diff_sections(new_html, pub_section)

        if diff.is_full_replacement:
            print(f"\n⚠️  Complete replacement of section '{section}'.")
            print("No matching sub-sections found between local and published.")
            answer = input("Proceed with full replacement? [y/N] ").strip().lower()
            if answer != "y":
                print("Aborted.")
                return
            new_html = preserve_image_markup(new_html, pub_section)
            merged = page_html[:sec_start] + new_html + page_html[sec_end:]
        else:
            # Check if published section has raw <img> tags that need fixing
            has_broken_images = bool(re.search(r"<img\s", pub_section))

            if not diff.changed and not has_broken_images:
                print("\n✓ No changes detected — page is up to date.")
                return
            if not diff.changed and has_broken_images:
                print("\n🔧 Fixing broken image markup (no content changes).")
                merged = page_html[:sec_start] + new_html + page_html[sec_end:]
            else:
                print("\n📝 Incremental update:")
                for title in diff.changed:
                    print(f"  ↻ Updated: {title}")
                for title in diff.unchanged:
                    print(f"  ✓ Unchanged: {title}")
                updated_section = merge_incremental(
                    pub_section, new_html, diff.changed
                )
                updated_section = preserve_image_markup(updated_section, pub_section)
                merged = page_html[:sec_start] + updated_section + page_html[sec_end:]

    update_response = session.put(
        f"{api}/content/{page_id}",
        json={
            "version": {"number": page["version"]["number"] + 1},
            "title": page["title"],
            "type": "page",
            "body": {"storage": {"value": merged, "representation": "storage"}},
        },
    )
    update_response.raise_for_status()
    result = update_response.json()
    print("Published:", result["_links"]["base"] + result["_links"]["webui"])


def _frontmatter_section(md_path: Path) -> str | None:
    """Return the confluence_section value from YAML frontmatter, or None."""
    fm_match = re.match(r"^---\n(.*?\n)---\n", md_path.read_text(), re.DOTALL)
    if not fm_match:
        return None
    for line in fm_match.group(1).splitlines():
        if line.startswith("confluence_section:"):
            return line.split(":", 1)[1].strip()
    return None


def _find_md_for_section(markdown_files: list[Path], section: str) -> Path:
    """Pick the markdown file whose confluence_section matches, or the first file."""
    if len(markdown_files) == 1:
        return markdown_files[0]
    for candidate in markdown_files:
        val = _frontmatter_section(candidate)
        if val and val.lower() == section.lower():
            return candidate
    return markdown_files[0]


def run(args: argparse.Namespace) -> int:
    config, config_path = load_config(args.config)
    session, api = make_session(config)
    check_auth(session, api, config_path)

    output_dir = args.output_dir.expanduser()
    markdown_files = sorted(output_dir.glob("*.md"))
    if not markdown_files:
        sys.exit(f"ERROR: No .md file in {output_dir}")

    md_path = _find_md_for_section(markdown_files, args.section_heading)

    upload_attachments(session, api, args.page_id, output_dir)
    new_html = md_to_confluence_html(md_path)
    print(f"Converted markdown to HTML ({len(new_html)} bytes)")
    publish(session, api, args.page_id, args.section_heading, new_html)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return run(args)


def legacy_main(argv: list[str] | None = None) -> int:
    warn_legacy_command("kiro-publish-to-confluence", "mermaid2conf publish")
    return main(argv)


if __name__ == "__main__":
    sys.exit(main())
