#!/usr/bin/env bash
# verify_local.sh — 本地 sanity check（发布前）
#   - meta.json 必填字段齐
#   - source/audio.mp3 存在 & ffprobe 能读
#   - cover.png 存在 & docs/assets/covers/<slug>.png 镜像也在
# 用法: verify_local.sh <project_dir>
set -euo pipefail

PROJ="${1:?usage: verify_local.sh <project_dir>}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../lib/meta.sh
source "$SCRIPT_DIR/../lib/meta.sh"

fail=0
chk() { if "$@"; then echo "  ✓ $*"; else echo "  ✗ $*"; fail=1; fi }

echo "🔎 verify_local: $PROJ"

# meta required
for k in slug source_url source_kind title author lang duration_sec lane; do
  v=$(meta_get "$PROJ" "$k" 2>/dev/null || echo "")
  if [ -n "$v" ] && [ "$v" != "null" ]; then echo "  ✓ meta.$k=$v"
  else echo "  ✗ meta.$k missing"; fail=1; fi
done

# audio
if [ -f "$PROJ/source/audio.mp3" ]; then
  dur=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$PROJ/source/audio.mp3" 2>/dev/null || echo 0)
  if awk "BEGIN{exit !($dur>1)}"; then
    echo "  ✓ audio.mp3 duration=${dur}s"
  else
    echo "  ✗ audio.mp3 unreadable or empty"; fail=1
  fi
else
  echo "  ✗ audio.mp3 missing"; fail=1
fi

# cover
if [ -f "$PROJ/cover.png" ]; then
  size=$(sips -g pixelWidth -g pixelHeight "$PROJ/cover.png" 2>/dev/null | awk '/pixel/{print $2}' | xargs)
  echo "  ✓ cover.png ${size}"
else
  echo "  ✗ cover.png missing"; fail=1
fi

# docs mirror (RSS 会引用这份，必须存在并 git 跟踪)
SLUG="$(basename "$PROJ")"
REPO="$(cd "$SCRIPT_DIR/../../.." && pwd)"
DOCS_COVER="$REPO/docs/assets/covers/$SLUG.png"
if [ -f "$DOCS_COVER" ]; then
  echo "  ✓ docs/assets/covers/$SLUG.png"
else
  echo "  ✗ docs/assets/covers/$SLUG.png missing (跳 enrich/cover_fetch.sh 会自动镜像)"; fail=1
fi

[ "$fail" = 0 ] || { echo "❌ verify_local FAILED"; exit 1; }
echo "✅ verify_local OK"
