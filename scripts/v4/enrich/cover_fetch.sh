#!/usr/bin/env bash
# cover_fetch.sh — 准备 cover.png（1400×1400）
# 优先级: source/thumbnail.* > meta.thumbnail_url > og:image > AI 兜底
# 用法: cover_fetch.sh <project_dir>
set -euo pipefail

PROJ="${1:?usage: cover_fetch.sh <project_dir>}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../lib/meta.sh
source "$SCRIPT_DIR/../lib/meta.sh"

OUT="$PROJ/cover.png"
SLUG="$(basename "$PROJ")"
REPO="$(cd "$SCRIPT_DIR/../../.." && pwd)"
DOCS_OUT="$REPO/docs/assets/covers/$SLUG.png"

# 镜像到 docs/（调用处不用再手动 cp）
mirror_to_docs() {
  mkdir -p "$REPO/docs/assets/covers"
  cp "$OUT" "$DOCS_OUT"
  echo "→ mirrored to docs/assets/covers/$SLUG.png"
}

if [ -f "$OUT" ]; then
  echo "✓ cover.png 已存在"
  [ -f "$DOCS_OUT" ] || mirror_to_docs
  exit 0
fi

# 1) 本地 source/thumbnail.*
LOCAL=$(ls "$PROJ"/source/thumbnail.* 2>/dev/null | head -1 || true)
if [ -n "$LOCAL" ]; then
  echo "🖼  using local $LOCAL"
  sips -s format png -Z 1400 "$LOCAL" --out "$OUT" >/dev/null
  mirror_to_docs
  exit 0
fi

# 2) meta.thumbnail_url
URL=$(meta_get "$PROJ" thumbnail_url || echo "")
if [ -n "$URL" ]; then
  echo "🌐 fetching $URL"
  TMP=$(mktemp); curl -sSL --max-time 30 -o "$TMP" "$URL" || TMP=""
  if [ -n "$TMP" ] && [ -s "$TMP" ]; then
    sips -s format png -Z 1400 "$TMP" --out "$OUT" >/dev/null
    rm -f "$TMP"; mirror_to_docs; exit 0
  fi
fi

# 3) og:image fallback (从 source_url 抓)
SRC_URL=$(meta_get "$PROJ" source_url || echo "")
if [ -n "$SRC_URL" ]; then
  OG=$(curl -sSL --max-time 15 "$SRC_URL" 2>/dev/null \
    | grep -oE '<meta[^>]+og:image[^>]+content="[^"]+"' \
    | head -1 \
    | sed -E 's/.*content="([^"]+)".*/\1/' || true)
  if [ -n "$OG" ]; then
    echo "🌐 og:image $OG"
    TMP=$(mktemp); curl -sSL --max-time 30 -o "$TMP" "$OG" || TMP=""
    if [ -n "$TMP" ] && [ -s "$TMP" ]; then
      sips -s format png -Z 1400 "$TMP" --out "$OUT" >/dev/null
      rm -f "$TMP"; mirror_to_docs; exit 0
    fi
  fi
fi

echo "❌ 没找到原始缩略图。AI 兜底由上层 pipeline 主动调（image_generate 工具）。" >&2
exit 1
