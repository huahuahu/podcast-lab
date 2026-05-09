#!/usr/bin/env bash
# lane_passthrough.sh — 中文源：不动音频，按需用 faster-whisper 出字幕
# 用法: lane_passthrough.sh <project_dir> [--with-subs]
set -euo pipefail

PROJ="${1:?usage: lane_passthrough.sh <project_dir> [--with-subs]}"
WITH_SUBS=0
[ "${2:-}" = "--with-subs" ] && WITH_SUBS=1

[ -f "$PROJ/source/audio.mp3" ] || { echo "❌ missing $PROJ/source/audio.mp3"; exit 2; }

echo "✅ passthrough: 音频原样发布 ($PROJ/source/audio.mp3)"

if [ "$WITH_SUBS" = 1 ]; then
  if ! command -v faster-whisper-cli >/dev/null 2>&1 && ! command -v whisper >/dev/null 2>&1; then
    echo "⚠️  --with-subs 要求 faster-whisper 或 whisper 安装；跳过字幕生成。"
    exit 0
  fi
  mkdir -p "$PROJ/transcript/subtitles"
  echo "📝 (TODO) faster-whisper 生成中文字幕到 $PROJ/transcript/subtitles/"
  # 留空：等用户真的要时再实现
fi
