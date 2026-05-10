#!/usr/bin/env bash
# pipeline.sh — 多源播客制作管线入口（薄壳）
# 用法: pipeline.sh <slug> <url-or-path> [--lang zh|en|...] [--with-subs]
set -euo pipefail

SLUG="${1:?usage: pipeline.sh <slug> <url> [--lang xx] [--with-subs]}"
URL="${2:?usage: pipeline.sh <slug> <url> [--lang xx] [--with-subs]}"
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
STEPS="$REPO/scripts"

mkdir -p "$PROJ"

echo "═══ pipeline: $SLUG ═══"

# 1) detect → ingest
ADAPTER=$("$STEPS/ingest/detect.sh" "$URL")
echo "🔍 adapter=$ADAPTER"
ADAPTER_SH="$STEPS/ingest/adapter_${ADAPTER}.sh"
[ -x "$ADAPTER_SH" ] || { echo "❌ adapter not implemented yet: $ADAPTER" >&2; exit 3; }
"$ADAPTER_SH" "$PROJ" "$URL" "$LANG_HINT"

# 2) decide lane → process
LANE=$("$STEPS/process/decide_lane.sh" "$PROJ")
echo "🛤  lane=$LANE"
case "$LANE" in
  passthrough) "$STEPS/process/lane_passthrough.sh" "$PROJ" $WITH_SUBS ;;
  translate)   "$STEPS/process/lane_translate.sh"   "$PROJ" ;;
esac

# 3) enrich
"$STEPS/enrich/cover_fetch.sh" "$PROJ" || echo "⚠️  cover 抓不到，需要手动 / AI 兜底"

# 4) verify_local（发布前最后一关，外部脚本可继续 publish）
"$STEPS/publish/verify_local.sh" "$PROJ"

echo ""
echo "✅ ingest+process+enrich 完成。下一步:"
echo "   gh release create v0.X.0-$SLUG ..."
echo "   编辑 docs/rss.xml 加 item，引用 cover.png + audio.mp3"
echo "   git push"
echo "   $STEPS/publish/final_acceptance.sh $SLUG"
