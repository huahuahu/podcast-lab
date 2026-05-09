#!/usr/bin/env bash
# adapter_youtube.sh — YouTube → audio + thumbnail + meta
# 用法: adapter_youtube.sh <project_dir> <url> [lang_hint]
#
# 产物:
#   <project_dir>/source/audio.mp3
#   <project_dir>/source/thumbnail.<ext>
#   <project_dir>/source/meta.json    (含 title/author/duration/lang/thumbnail_url)
#
# 重要: 永远不抓 YouTube 字幕（不可信）。
set -euo pipefail

PROJ="${1:?usage: adapter_youtube.sh <project_dir> <url> [lang_hint]}"
URL="${2:?usage: adapter_youtube.sh <project_dir> <url> [lang_hint]}"
LANG_HINT="${3:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../lib/meta.sh
source "$SCRIPT_DIR/../lib/meta.sh"

mkdir -p "$PROJ/source"
SLUG="$(basename "$PROJ")"

# 初始化 meta
meta_init "$PROJ" "$SLUG" "$URL" "youtube"

# 1) 拿元数据（title/uploader/duration/thumbnail）
echo "📋 fetching metadata..."
META_JSON=$(yt-dlp --dump-single-json --no-warnings "$URL" 2>/dev/null) || {
  echo "❌ yt-dlp metadata failed" >&2; exit 1;
}

TITLE=$(jq -r '.title // "Untitled"' <<<"$META_JSON")
UPLOADER=$(jq -r '.uploader // .channel // "Unknown"' <<<"$META_JSON")
DURATION=$(jq -r '.duration // 0' <<<"$META_JSON")
THUMB_URL=$(jq -r '.thumbnail // empty' <<<"$META_JSON")

meta_set     "$PROJ" title          "$TITLE"
meta_set     "$PROJ" author         "$UPLOADER"
meta_set_raw "$PROJ" duration_sec   "$DURATION"
[ -n "$THUMB_URL" ] && meta_set "$PROJ" thumbnail_url "$THUMB_URL"

# 语言：用户指定 > yt-dlp 提供 > 留 null（让后续 lane 决策处报错或默认）
DETECTED_LANG=$(jq -r '.language // empty' <<<"$META_JSON")
if [ -n "$LANG_HINT" ]; then
  meta_set "$PROJ" lang "$LANG_HINT"
elif [ -n "$DETECTED_LANG" ]; then
  meta_set "$PROJ" lang "$DETECTED_LANG"
fi

# 2) 下载音频
if [ ! -f "$PROJ/source/audio.mp3" ]; then
  echo "🎬 downloading audio..."
  yt-dlp -x --audio-format mp3 --audio-quality 0 \
    -o "$PROJ/source/audio.%(ext)s" "$URL" 2>&1 | tail -5
else
  echo "✓ audio.mp3 exists"
fi

# 3) 抓缩略图（直接 curl，比 yt-dlp 快、不二次封装）
if [ -n "$THUMB_URL" ] && ! ls "$PROJ/source/thumbnail."* >/dev/null 2>&1; then
  echo "🖼  fetching thumbnail..."
  EXT="${THUMB_URL##*.}"; EXT="${EXT%%\?*}"
  case "$EXT" in jpg|jpeg|png|webp) ;; *) EXT="jpg";; esac
  curl -sSL --max-time 30 -o "$PROJ/source/thumbnail.$EXT" "$THUMB_URL" || \
    echo "⚠️  thumbnail download failed, will fall back later"
fi

echo "✅ ingest done: $PROJ"
echo "   title:    $TITLE"
echo "   author:   $UPLOADER"
echo "   duration: ${DURATION}s"
echo "   lang:     $(meta_get "$PROJ" lang || echo '(unset)')"
