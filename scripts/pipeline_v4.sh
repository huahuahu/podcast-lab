#!/usr/bin/env bash
# pipeline_v4.sh — v4 入口（薄壳）
# 用法: pipeline_v4.sh <slug> <url-or-path> [--lang zh|en|...] [--with-subs]
set -euo pipefail

SLUG="${1:?usage: pipeline_v4.sh <slug> <url> [--lang xx] [--with-subs]}"
URL="${2:?usage: pipeline_v4.sh <slug> <url> [--lang xx] [--with-subs]}"
shift 2

LANG_HINT=""
WITH_SUBS=""
while [ $# -gt 0 ]; do
  case "$1" in
    --lang) LANG_HINT="$2"; shift 2;;
    --with-subs) WITH_SUBS="--with-subs"; shift;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJ="$REPO/projects/$SLUG"
V4="$REPO/scripts/v4"

mkdir -p "$PROJ"

echo "═══ v4 pipeline: $SLUG ═══"

# 1) detect → ingest
ADAPTER=$("$V4/ingest/detect.sh" "$URL")
echo "🔍 adapter=$ADAPTER"
ADAPTER_SH="$V4/ingest/adapter_${ADAPTER}.sh"
[ -x "$ADAPTER_SH" ] || { echo "❌ adapter not implemented yet: $ADAPTER" >&2; exit 3; }
"$ADAPTER_SH" "$PROJ" "$URL" "$LANG_HINT"

# 2) decide lane → process
LANE=$("$V4/process/decide_lane.sh" "$PROJ")
echo "🛤  lane=$LANE"
case "$LANE" in
  passthrough) "$V4/process/lane_passthrough.sh" "$PROJ" $WITH_SUBS ;;
  translate)   "$V4/process/lane_translate.sh"   "$PROJ" ;;
esac

# 3) enrich
"$V4/enrich/cover_fetch.sh" "$PROJ" || echo "⚠️  cover 抓不到，需要手动 / AI 兜底"

# 4) verify_local（发布前最后一关，外部脚本可继续 publish）
"$V4/publish/verify_local.sh" "$PROJ"

echo ""
echo "✅ v4 ingest+process+enrich 完成。下一步:"
echo "   gh release create v0.X.0-$SLUG ..."
echo "   编辑 docs/rss.xml 加 item，引用 cover.png + audio.mp3"
echo "   git push"
echo "   $V4/publish/final_acceptance.sh $SLUG"
