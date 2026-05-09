#!/usr/bin/env bash
# run_all.sh — 跑所有 v4 单元测试（不调外部 API）
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
chmod +x "$HERE"/test_*.sh

fail=0
for t in "$HERE"/test_*.sh; do
  echo "── $(basename "$t") ──"
  if ! bash "$t"; then fail=1; fi
  echo
done

[ "$fail" = 0 ] && echo "🎉 all tests passed" || { echo "💥 some tests failed"; exit 1; }
