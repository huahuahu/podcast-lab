#!/usr/bin/env bash
# test_detect.sh — 验证 URL → adapter 名映射
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DETECT="$SCRIPT_DIR/../scripts/ingest/detect.sh"

assert_eq() {
  local actual="$1" expected="$2" name="$3"
  if [ "$actual" = "$expected" ]; then
    echo "  ✓ $name → $actual"
  else
    echo "  ✗ $name → got '$actual', want '$expected'"; exit 1
  fi
}

assert_eq "$("$DETECT" "https://www.youtube.com/watch?v=abc")" "youtube" "youtube.com"
assert_eq "$("$DETECT" "https://youtu.be/abc")"               "youtube" "youtu.be"
assert_eq "$("$DETECT" "https://softskills.audio/episodes/511")" "softskills" "softskills.audio"
assert_eq "$("$DETECT" "https://www.dwarkesh.com/p/jensen")"    "dwarkesh" "dwarkesh.com"
assert_eq "$("$DETECT" "https://example.com/foo.mp3")"          "direct_mp3" ".mp3 url"
assert_eq "$("$DETECT" "https://example.com/feed.xml")"         "podcast_rss" "feed.xml"

# 本地文件
TMP=$(mktemp); assert_eq "$("$DETECT" "$TMP")" "local" "local file"; rm -f "$TMP"

echo "✅ test_detect: all passed"
