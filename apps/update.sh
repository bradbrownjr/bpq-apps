#!/bin/bash
# Update BPQ apps from GitHub
# Run this on the node: bash /home/ect/apps/update.sh

set -e

BASE="https://raw.githubusercontent.com/bradbrownjr/bpq-apps/main/apps"
APPS_DIR="$(dirname "$(realpath "$0")")"
FORMS_DIR="$APPS_DIR/forms"

echo "Updating BPQ apps from GitHub..."

# Update main scripts
for script in apps.py forms.py; do
    echo "  $script"
    curl -fsSL "$BASE/$script" -o "$APPS_DIR/$script.tmp" && \
        mv "$APPS_DIR/$script.tmp" "$APPS_DIR/$script" && \
        chmod +x "$APPS_DIR/$script"
done

# Update form templates and data files
mkdir -p "$FORMS_DIR"
for file in $(curl -fsSL "https://api.github.com/repos/bradbrownjr/bpq-apps/contents/apps/forms" \
    | grep '"name"' | grep -oP '(?<="name": ")[^"]+\.(frm|json)'); do
    echo "  forms/$file"
    curl -fsSL "$BASE/forms/$file" -o "$FORMS_DIR/$file.tmp" && \
        mv "$FORMS_DIR/$file.tmp" "$FORMS_DIR/$file"
done

echo ""
echo "Update complete."
