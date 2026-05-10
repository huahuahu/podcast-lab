#!/usr/bin/env bash
# decide_lane.sh — 根据 meta.json 决定走哪条 lane
# 用法: decide_lane.sh <project_dir>
# 输出（stdout）: passthrough | translate
# 副作用: 把决策写回 meta.lane
set -euo pipefail

PROJ="${1:?usage: decide_lane.sh <project_dir>}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../lib/meta.sh
source "$SCRIPT_DIR/../lib/meta.sh"

LANG=$(meta_get "$PROJ" lang || echo "")
[ -z "$LANG" ] && {
  echo "❌ meta.lang is unset; ingest 必须填语言。" >&2
  exit 1
}

case "$LANG" in
  zh|zh-CN|zh-Hans|zh-Hant|zh-TW|cmn) LANE="passthrough" ;;
  *)                                  LANE="translate"   ;;
esac

meta_set "$PROJ" lane "$LANE"
echo "$LANE"
