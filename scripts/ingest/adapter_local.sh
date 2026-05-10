#!/usr/bin/env bash
# adapter_local.sh — 本地视频/音频文件 → audio.mp3 + meta.json
# 用法: adapter_local.sh <project_dir> <local_path> [lang_hint] [--title "..."] [--author "..."]
set -euo pipefail

PROJ="${1:?usage: adapter_local.sh <project_dir> <path> [lang]}"
SRC="${2:?usage: adapter_local.sh <project_dir> <path> [lang]}"
LANG_HINT="${3:-}"
shift 3 || true

TITLE=""; AUTHOR=""
while [ $# -gt 0 ]; do
  case "$1" in
    --title) TITLE="$2"; shift 2;;
    --author) AUTHOR="$2"; shift 2;;
    *) shift;;
  esac
done

[ -f "$SRC" ] || { echo "❌ 文件不存在: $SRC"; exit 2; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../lib/meta.sh
source "$SCRIPT_DIR/../lib/meta.sh"

mkdir -p "$PROJ/source"
SLUG="$(basename "$PROJ")"
meta_init "$PROJ" "$SLUG" "$SRC" "local"

# 转 mp3（如果已经是 mp3 就直接拷）
if [ ! -f "$PROJ/source/audio.mp3" ]; then
  echo "🎬 转码 → audio.mp3..."
  case "$SRC" in
    *.mp3) cp "$SRC" "$PROJ/source/audio.mp3" ;;
    *)     ffmpeg -loglevel error -y -i "$SRC" -vn -ac 1 -ar 44100 -q:a 4 "$PROJ/source/audio.mp3" ;;
  esac
fi

# 时长
DUR=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$PROJ/source/audio.mp3" | awk '{printf "%d", $1}')
meta_set_raw "$PROJ" duration_sec "$DUR"

# 标题/作者
[ -z "$TITLE" ] && TITLE="${SLUG//-/ }"
meta_set "$PROJ" title  "$TITLE"
[ -n "$AUTHOR" ] && meta_set "$PROJ" author "$AUTHOR" || meta_set "$PROJ" author "Local"

# 语言
[ -n "$LANG_HINT" ] && meta_set "$PROJ" lang "$LANG_HINT"

echo "✅ ingest done: $PROJ"
echo "   title:    $TITLE"
echo "   duration: ${DUR}s"
echo "   lang:     $(meta_get "$PROJ" lang || echo '(unset)')"
echo "⚠️  本地文件没有缩略图，cover_fetch 会要求 AI 兜底或手动提供"
