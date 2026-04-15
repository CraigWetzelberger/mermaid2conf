---
name: mermaid2conf
description: Use this skill to publish markdown documents with mermaid diagrams to directly Confluence.
compatibility: Requires Python 3.12+, uv, and mermaid-cli
---

# Markdown To Confluence

## Pre-Requisites

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
   npm list -g @mermaid-js/mermaid-cli || echo "NOT INSTALLED" 
   ```

   If `mermaid-cli` is not installed prompt for approval to install `uv`

   ```shell
     npm install -g @mermaid-js/mermaid-cli
   ```

3. Confirm confluence configuration exists

   ```shell
   [ -f ~/.config/markdown-to-confluence/confluence_config.json ] && echo "Exists" || echo "Does not exist" 
   ```

   If Confluence Configuration file does not exist, direct user to visit [Configure Confluence Credentials](https://github.com/bholland-bh/markdown-to-confluence#configure-confluence-credentials) and terminate

## Inputs

1. Ask the user for the path to the markdown file. Wait for their response before proceeding. This value will be referred to by $SOURCE_MD
2. Read the $SOURCE_MD markdown file and check for YAML frontmatter with:

- `confluence_url` ($CONFLUENCE_URL)

3. If `confluence_url` is not present in the YAML frontmatter, prompt the user for a Confluence url ($CONFLUENCE_URL)
   1. Extract the $PAGE_ID from $CONFLUENCE_URL - it is the numeric segment after `/pages/` in the path.
   2. Extract the $SECTION_NAME from $CONFLUENCE_URL - it is the string after `#` at the end of the URL
      - If not found, use an empty string instead ""

## Execution

Substitute all variable references with their exact values

1. Process the mermaid diagram
   ```shell
   uvx mermaid2conf process "$SOURCE_MD"
   ```
2. Publish the document to confluence
   ```shell
   uvx mermaid2conf publish "$PAGE_ID" "$SECTION_NAME"
   ```
