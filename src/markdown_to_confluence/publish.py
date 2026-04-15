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

CONFIG_FILENAME = "confluence_config.json"
DEFAULT_CONFIG_LOCATIONS = (
    Path.cwd() / CONFIG_FILENAME,
    Path.home() / ".config" / "markdown-to-confluence" / CONFIG_FILENAME,
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
    for png_path in sorted(output_dir.glob("*.png")):
        print(f"Uploading: {png_path.name}")
        with png_path.open("rb") as handle:
            response = session.post(
                f"{api}/content/{page_id}/child/attachment",
                files={"file": (png_path.name, handle, "image/png")},
                data={"minorEdit": "true"},
            )

        if response.status_code == 200:
            print("  Created")
            continue

        attachment_response = session.get(
            f"{api}/content/{page_id}/child/attachment",
            params={"filename": png_path.name},
        )
        results = attachment_response.json().get("results", [])
        if not results:
            print(f"  WARNING: Could not upload {png_path.name}")
            continue

        attachment_id = results[0]["id"]
        with png_path.open("rb") as handle:
            update_response = session.post(
                f"{api}/content/{page_id}/child/attachment/{attachment_id}/data",
                files={"file": (png_path.name, handle, "image/png")},
                data={"minorEdit": "true"},
            )
        print(f"  Updated (HTTP {update_response.status_code})")


def md_to_confluence_html(md_path: Path) -> str:
    content = md_path.read_text()
    content = re.sub(r"^---\n.*?\n---\n", "", content, count=1, flags=re.DOTALL)
    content = re.sub(
        r"!\[Mermaid Diagram\]\(([^)]+\.png)\)",
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


def merge_section(current: str, section: str, new_html: str) -> str:
    heading_pattern = re.compile(r"<h1[^>]*>", re.IGNORECASE)
    positions = [match.start() for match in heading_pattern.finditer(current)]
    target_index = None
    for index, position in enumerate(positions):
        end_h1 = current.index("</h1>", position) + 5
        heading_text = re.sub(r"<[^>]+>", "", current[position:end_h1]).strip()
        if heading_text.lower() == section.lower().strip():
            target_index = index
            break

    if target_index is not None:
        start = positions[target_index]
        end = (
            positions[target_index + 1]
            if target_index + 1 < len(positions)
            else len(current)
        )
        return current[:start] + new_html + current[end:]
    if positions:
        return current + f"<h1>{section}</h1>{new_html}"
    return current + new_html


def publish(
    session: requests.Session, api: str, page_id: str, section: str, new_html: str
) -> None:
    response = session.get(
        f"{api}/content/{page_id}", params={"expand": "body.storage,version"}
    )
    response.raise_for_status()
    page = response.json()
    merged = merge_section(page["body"]["storage"]["value"], section, new_html)

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


def run(args: argparse.Namespace) -> int:
    config, config_path = load_config(args.config)
    session, api = make_session(config)
    check_auth(session, api, config_path)

    output_dir = args.output_dir.expanduser()
    markdown_files = sorted(output_dir.glob("*.md"))
    if not markdown_files:
        sys.exit(f"ERROR: No .md file in {output_dir}")

    upload_attachments(session, api, args.page_id, output_dir)
    new_html = md_to_confluence_html(markdown_files[0])
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
