#!/usr/bin/env bash
# final_acceptance.sh — 发布后最终验收
#   等 GitHub Pages 部署 → 检查 RSS 里有这条 item，关键 URL HEAD 200。
# 用法: final_acceptance.sh <slug> [rss_url]
set -euo pipefail

SLUG="${1:?usage: final_acceptance.sh <slug> [rss_url]}"
RSS_URL="${2:-https://huahuahu.github.io/podcast-lab/rss.xml}"

echo "⏳ 等 GitHub Pages 部署 + RSS 出现 slug=$SLUG ..."
deadline=$(( $(date +%s) + 120 ))
found=0
pat="<guid[^>]*>$SLUG</guid>"
while [ "$(date +%s)" -lt "$deadline" ]; do
  body=$(curl -fsSL --max-time 10 "$RSS_URL" 2>/dev/null || echo "")
  # 注意：grep -q + 大字符串会触发 SIGPIPE(141)，与 set -e/pipefail 冲突
  # 用 -c 计数避开这个问题
  if [ "$(printf '%s' "$body" | grep -c "$pat" 2>/dev/null || echo 0)" -gt 0 ]; then
    found=1; break
  fi
  sleep 6
done

[ "$found" = 1 ] || { echo "❌ RSS 在 120s 内没出现 slug=$SLUG"; exit 1; }
echo "✅ RSS 已更新"

# 抽该 item 内的 URL（itunes:image / enclosure / podcast:transcript）
ITEM=$(printf '%s\n' "$body" | awk -v s="$SLUG" '
  /<item>/{buf=""; in_item=1}
  in_item{buf=buf"\n"$0}
  /<\/item>/{
    if (buf ~ ("<guid[^>]*>"s"</guid>")) print buf
    in_item=0
  }')

urls=$(printf '%s\n' "$ITEM" | grep -oE '(href|url)="[^"]+"' | sed -E 's/.*"([^"]+)".*/\1/' | sort -u)

[ -n "$urls" ] || { echo "❌ 找到 item 但没解析出 URL"; exit 1; }

fail=0
echo "🔗 检查 URL HEAD:"
for u in $urls; do
  case "$u" in http://*|https://*) ;; *) continue;; esac
  # -L 跟 302；github release 重定向到 S3 需多调一些时间
  # 不用 -w '%{http_code}' 因为加 -L 后会拼出多个 code。
  # 用 -o 刷出 Header 到 stderr/temp，取最后一个 HTTP 状态行。
  status_line=$(curl -sIL --max-time 30 -o /dev/null -D - "$u" 2>/dev/null | grep -E '^HTTP/' | tail -1)
  code=$(printf '%s' "$status_line" | awk '{print $2}')
  if [ "$code" = "200" ]; then
    echo "  ✓ 200 $u"
  else
    echo "  ✗ ${code:-???} $u"; fail=1
  fi
done

# 强校验 itunes:image 必须有
if [ "$(printf '%s' "$ITEM" | grep -c 'itunes:image' 2>/dev/null || echo 0)" -lt 1 ]; then
  echo "  ✗ itunes:image 缺失"; fail=1
else
  echo "  ✓ itunes:image 存在"
fi

[ "$fail" = 0 ] || { echo "❌ final_acceptance FAILED"; exit 1; }
echo "✅ final_acceptance OK — 可在播客客户端订阅播放"
