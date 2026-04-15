# Markdown to Confluence Publisher

Tools for publishing markdown documents with mermaid diagrams to Confluence.

## Skill

```shell
npx skills add bholland-bh/mermaid2conf --global --skill '*' --agent kiro-cli --agent codex
```

## Prerequisites

- Python 3.12+
- Node.js / npm
- [uv](https://docs.astral.sh/uv/)
  - `curl -LsSf https://astral.sh/uv/install.sh | sh` OR `brew install uv`
- [Mermaid CLI](https://github.com/mermaid-js/mermaid-cli):
  ```
  npm install -g @mermaid-js/mermaid-cli
  ```

## Install

Install the tool globally with `uv`:

```bash
uv tool install .
```

For local development, install it in editable mode:

```bash
uv tool install --editable .
```

Or run it directly from the checkout without installing:

```bash
uv run --project . mermaid2conf process docs/example.md
```

To execute it ephemerally with `uvx` from this checkout:

```bash
uvx --from . mermaid2conf process docs/example.md
```

## Publish

This repo includes a GitHub Actions workflow at [`/.github/workflows/publish.yml`](./.github/workflows/publish.yml) that builds and publishes the package to PyPI using Trusted Publishing.

One-time PyPI setup:

1. Create the `mermaid2conf` project on PyPI, or configure a pending publisher that is allowed to create it.
2. In PyPI, add a Trusted Publisher for this GitHub repo and workflow:
   - owner/repo: `bholland-bh/markdown-to-confluence`
   - workflow: `publish.yml`
   - environment: `pypi`

Release flow:

1. Bump `version` in [pyproject.toml](./pyproject.toml).
2. Commit and push.
3. Create a GitHub Release.
4. The `Publish` workflow will build `dist/*` and upload it to PyPI.

You can also trigger the workflow manually from GitHub Actions with `workflow_dispatch`.

## Configure Confluence credentials

Visit [https://id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens) to create api-token

Create `confluence_config.json` in the current directory, or pass an explicit path with `--config`:

```
{
  "confluence_url": "https://example.atlassian.net/wiki",
  "username": "user@example.com",
  "api_token": "<your-api-token>"
}
```

## Scripts

| Command                      | Purpose                                                        |
| ---------------------------- | -------------------------------------------------------------- |
| `mermaid2conf process`       | Renders mermaid diagrams to PNG and writes processed markdown  |
| `mermaid2conf publish`       | Uploads attachments and publishes to a Confluence page section |
| `mermaid2conf mermaid`       | Low-level helper for rendering Mermaid blocks to PNG           |
| `kiro-publish-processing.sh` | Repo-local compatibility wrapper around `uv run --project`     |

Legacy aliases are still available for compatibility:

- `kiro-publish-processing`
- `kiro-publish-to-confluence`
- `md2conf-mermaid`

## Usage

### Step 1: Preprocess (render mermaid diagrams)

```bash
mermaid2conf process <source.md>
```

Output goes to `./output/` by default and includes the processed markdown plus PNG images.

### Step 2: Publish to Confluence

```bash
mermaid2conf publish <page_id> "<section_heading>" [output_dir] --config ./confluence_config.json
```

The publish script:

- Uploads all PNG files as attachments (creates new or updates existing)
- Strips YAML frontmatter from the processed markdown
- Replaces `![Mermaid Diagram](file.png)` with Confluence `<ac:image>` attachment markup
- Does a section-level update: finds the `<h1>` matching `<section_heading>` and replaces that section, preserving all other sections
- If the section doesn't exist, appends it at the end

## Step 3 Install Kiro Prompt Integration

```
./install_kiro_prompt.sh
```

Once installed run the prompt

```
@publish-design
```
