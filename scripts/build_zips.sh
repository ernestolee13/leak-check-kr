#!/bin/bash
# Build release assets into dist/ (not committed; attach to a GitHub Release):
#   leak-check-kr.zip     Cowork plugin upload (plugin root at zip root)
#   leak-check-skill.zip  claude.ai skill upload (skill folder at zip root)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
python3 "$ROOT/scripts/validate_data.py"
python3 "$ROOT/scripts/render_docs.py" --check
mkdir -p "$ROOT/dist"; rm -f "$ROOT/dist/"*.zip
( cd "$ROOT/plugins/leak-check-kr" && zip -qrX "$ROOT/dist/leak-check-kr.zip" . -x '*.DS_Store' )
( cd "$ROOT/plugins/leak-check-kr/skills" && zip -qrX "$ROOT/dist/leak-check-skill.zip" leak-check -x '*.DS_Store' )
ls -l "$ROOT/dist"
