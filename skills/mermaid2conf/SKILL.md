---
name: mermaid2conf
description: Use this skill to publish markdown documents with mermaid diagrams to directly Confluence.
compatibility: Requires Python 3.12+, uv, and mermaid-cli
---

# Converts Markdown To Confluence with Mermaid documents automatically converting to an image. 

## Pre-Requisites

Run this single check. If it prints "READY", skip to the Inputs section immediately — do NOT run the individual checks below.

```shell
command -v uv >/dev/null && command -v mmdc >/dev/null && [ -f ~/.config/mermaid2conf/confluence_config.json ] && echo "READY" || echo "SETUP NEEDED"
```

Only if the output is "SETUP NEEDED", run these individual checks:

1. Confirm `uv` is installed

   ```shell
   command -v "uv" || echo "NOT INSTALLED"
   ```

   If `uv` is not installed prompt for approval to install `uv`

   ```shell
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. Confirm `mermaid-cli` is installed

   ```shell
   command -v "mmdc" || echo "NOT INSTALLED"
   ```

   If `mmdc` is not installed prompt for approval to install mermaid-cli

   ```shell
   npm install -g @mermaid-js/mermaid-cli
   ```

3. Confirm confluence configuration exists

   ```shell
   [ -f ~/.config/mermaid2conf/confluence_config.json ] && echo "Exists" || echo "Does not exist"
   ```

   If Confluence Configuration file does not exist, direct user to visit [Configure Confluence Credentials](https://github.com/CraigWetzelberger/mermaid2conf#configure-confluence-credentials) and terminate

## Inputs

1. The first parameter in the skill invocation is a path to markdown file. This value will be referred to by $SOURCE_MD
   - If the skill is invoked without input, ask the user for the path to the markdown file. Wait for their response before proceeding.
2. Read the $SOURCE_MD markdown file and check for YAML frontmatter with:

- `confluence_url` ($CONFLUENCE_URL)

3. If `confluence_url` is not present in the YAML frontmatter, prompt the user for a Confluence url ($CONFLUENCE_URL)
   1. Extract the $PAGE_ID from $CONFLUENCE_URL - it is the numeric segment after `/pages/` in the path.
   2. Extract the $SECTION_NAME from $CONFLUENCE_URL - it is the string after `#` at the end of the URL
      - If not found, use an empty string instead ""

## Execution

Substitute all variable references with their exact values

Resolve `./scripts` relative to this skill directory.

1. Process the mermaid diagram
   ```shell
   uv tool run --from ./scripts mermaid2conf process "$SOURCE_MD"
   ```
2. Publish the document to confluence
   ```shell
   uv tool run --from ./scripts mermaid2conf publish "$PAGE_ID" "$SECTION_NAME"
   ```
