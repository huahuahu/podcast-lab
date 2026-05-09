#!/usr/bin/env bash
# meta.sh — 读写 projects/<slug>/source/meta.json 的小工具。
# 用法：
#   meta_get  <project_dir> <key>           # 输出值，找不到退出 1
#   meta_set  <project_dir> <key> <value>   # 设字符串
#   meta_set_raw <project_dir> <key> <json> # 设原始 JSON（数字/bool/对象）
#   meta_init <project_dir> <slug> <source_url> <source_kind>
set -euo pipefail

_meta_path() { echo "$1/source/meta.json"; }

meta_get() {
  local f; f=$(_meta_path "$1")
  jq -er ".$2 // empty" "$f"
}

meta_set() {
  local f; f=$(_meta_path "$1")
  local k="$2" v="$3"
  local tmp; tmp=$(mktemp)
  jq --arg k "$k" --arg v "$v" '.[$k] = $v' "$f" > "$tmp" && mv "$tmp" "$f"
}

meta_set_raw() {
  local f; f=$(_meta_path "$1")
  local k="$2" v="$3"
  local tmp; tmp=$(mktemp)
  jq --arg k "$k" --argjson v "$v" '.[$k] = $v' "$f" > "$tmp" && mv "$tmp" "$f"
}

meta_init() {
  local proj="$1" slug="$2" url="$3" kind="$4"
  mkdir -p "$proj/source"
  local f; f=$(_meta_path "$proj")
  if [ ! -f "$f" ]; then
    jq -n --arg slug "$slug" --arg url "$url" --arg kind "$kind" '{
      slug: $slug,
      source_url: $url,
      source_kind: $kind,
      title: null,
      author: null,
      lang: null,
      duration_sec: null,
      thumbnail_url: null,
      has_official_transcript: false,
      transcript_kind: "none",
      series: null,
      needs_chapters: false,
      lane: null
    }' > "$f"
  fi
}

# 当作 source 库使用时不执行任何东西
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  cmd="${1:?meta.sh <command> ...}"; shift
  "meta_${cmd}" "$@"
fi
