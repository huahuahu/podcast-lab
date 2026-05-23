#!/usr/bin/env bash
# next_ep.sh — 算下一集的 EP 号 + release tag，避免手算撞号
# 用法:
#   scripts/publish/next_ep.sh <slug>          # 人类可读
#   eval "$(scripts/publish/next_ep.sh -e <slug>)"   # 导出 EP / EP_NUM / TAG 三个变量
set -euo pipefail

EVAL_MODE=0
if [ "${1:-}" = "-e" ]; then EVAL_MODE=1; shift; fi
SLUG="${1:?usage: next_ep.sh [-e] <slug>}"

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RSS="$REPO/docs/rss.xml"
[ -f "$RSS" ] || { echo "❌ no $RSS" >&2; exit 1; }

LAST=$(grep -oE 'EP[0-9]+' "$RSS" | sort -u | tail -n 1 | sed 's/EP//')
[ -n "$LAST" ] || { echo "❌ no EP* found in rss.xml" >&2; exit 1; }

NEXT=$(( 10#$LAST + 1 ))
EP=$(printf 'EP%02d' "$NEXT")
# 规律：EP{n} → v0.{n+1}.0-<slug>
TAG="v0.$((NEXT + 1)).0-$SLUG"

if [ "$EVAL_MODE" = 1 ]; then
  printf 'EP=%s\nEP_NUM=%d\nTAG=%s\n' "$EP" "$NEXT" "$TAG"
else
  echo "last  : EP$LAST"
  echo "next  : $EP"
  echo "tag   : $TAG"
fi
