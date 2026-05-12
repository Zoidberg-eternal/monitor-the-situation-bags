#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "==> Exporting simulation data to markdown..."
python3 scripts/export-to-quartz.py quartz-site/content

echo "==> Building Quartz site..."
cd quartz-site
npx quartz build

echo "==> Done! Run 'npx quartz serve' from quartz-site/ to preview."
