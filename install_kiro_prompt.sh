#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROMPT_DIR="$HOME/.kiro/prompts"
PROMPT_FILE="$PROMPT_DIR/publish-design.md"
CONFIG_FILE="$SCRIPT_DIR/confluence_config.json"

cat << EOF

=== Markdown-to-Confluence: Kiro Prompt Installer ===

Scripts installed at:
  $SCRIPT_DIR

EOF

# Remind about config
if [ ! -f "$CONFIG_FILE" ] || python3 -c "import json,sys; c=json.load(open('$CONFIG_FILE')); sys.exit(0 if all(c.get(k) for k in ('confluence_url','username','api_token')) else 1)" 2>/dev/null; then
  : # config exists and is filled in
else
  cat << EOF
⚠️  Confluence credentials not configured yet.
Edit $CONFIG_FILE with:
{
  "confluence_url": "https://example.atlassian.net/wiki",
  "username": "user@example.com",
  "api_token": "<your-api-token>"
}

EOF
fi

# Generate the prompt file
mkdir -p "$PROMPT_DIR"

cat > "$PROMPT_FILE" << EOF
Publish a markdown document to a specific section of a Confluence page, rendering any mermaid diagrams as images.

## Steps

1. Ask the user for the path to the markdown file. Optionally ask if they have a Confluence URL override. Wait for their response before proceeding.

2. Read the source markdown file and check for YAML frontmatter with \`confluence_url\` and \`confluence_section\`. A Confluence URL provided by the user overrides frontmatter. If no URL or section is available from either source, ask the user.

3. Parse the page ID from the Confluence URL — it is the numeric segment after \`/pages/\` in the path.

4. Run the preprocessing script to render mermaid diagrams:
   \`\`\`
   bash $SCRIPT_DIR/kiro-publish-processing.sh <file_path>
   \`\`\`

5. Run the publish script with the page ID and section heading:
   \`\`\`
   uv run --project "$SCRIPT_DIR" kiro-publish-to-confluence <page_id> "<confluence_section>" "$SCRIPT_DIR/output" --config "$CONFIG_FILE"
   \`\`\`

6. Report the page URL printed by the publish script when done.
EOF

cat << EOF
✅ Kiro prompt written to:
  $PROMPT_FILE

This file is used by Kiro as a slash-command prompt.
Run it in Kiro with:  @publish-design

EOF
