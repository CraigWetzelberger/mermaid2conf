# Markdown to Confluence Publisher

Tools for publishing markdown documents with mermaid diagrams to Confluence.

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
uv run --project . kiro-publish-processing docs/example.md
```

## Configure Confluence credentials

Create `confluence_config.json` in the current directory, or pass an explicit path with `--config`:

```
{
  "confluence_url": "https://example.atlassian.net/wiki",
  "username": "user@example.com",
  "api_token": "<your-api-token>"
}
```

## Scripts

| Script                       | Purpose                                                        |
| ---------------------------- | -------------------------------------------------------------- |
| `kiro-publish-processing`    | Renders mermaid diagrams to PNG and writes processed markdown  |
| `kiro-publish-to-confluence` | Uploads attachments and publishes to a Confluence page section |
| `md2conf-mermaid`            | Low-level helper for rendering Mermaid blocks to PNG           |
| `kiro-publish-processing.sh` | Repo-local compatibility wrapper around `uv run --project`     |

## Usage

### Step 1: Preprocess (render mermaid diagrams)

```bash
kiro-publish-processing <source.md>
```

Output goes to `./output/` by default and includes the processed markdown plus PNG images.

### Step 2: Publish to Confluence

```bash
kiro-publish-to-confluence <page_id> "<section_heading>" [output_dir] --config ./confluence_config.json
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
