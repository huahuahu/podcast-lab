#!/usr/bin/env bash
# detect.sh — URL → adapter 名
# 用法: detect.sh <url>
# 输出:  youtube | softskills | dwarkesh | podcast_rss | direct_mp3 | local
set -euo pipefail

URL="${1:?usage: detect.sh <url-or-path>}"

# 本地文件
if [ -f "$URL" ]; then
  echo "local"; exit 0
fi

case "$URL" in
  *softskills.audio*|*softskills.engineer*) echo "softskills"; exit 0;;
  *dwarkesh.com*|*dwarkeshpatel.com*)        echo "dwarkesh"; exit 0;;
  *youtube.com*|*youtu.be*)                  echo "youtube"; exit 0;;
  *bilibili.com*|*b23.tv*)                   echo "youtube"; exit 0;;
  *.mp3|*.m4a|*.wav)                         echo "direct_mp3"; exit 0;;
  *.xml|*/rss*|*/feed*)                      echo "podcast_rss"; exit 0;;
esac

# 兜底：HEAD 探测 content-type
ct=$(curl -sIL --max-time 8 "$URL" 2>/dev/null | awk -F': ' 'tolower($1)=="content-type"{print tolower($2)}' | tail -1 | tr -d '\r')
case "$ct" in
  audio/*)  echo "direct_mp3"; exit 0;;
  *xml*|*rss*) echo "podcast_rss"; exit 0;;
esac

# 默认按播客网页处理（让 podcast_rss adapter 去找 enclosure / og:audio）
echo "podcast_rss"
