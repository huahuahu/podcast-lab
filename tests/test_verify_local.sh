#!/usr/bin/env bash
# test_verify_local.sh — verify_local: 缺音频应失败，齐了应通过
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
V4="$SCRIPT_DIR/../scripts/v4"
source "$V4/lib/meta.sh"

PROJ=$(mktemp -d)
trap 'rm -rf "$PROJ"' EXIT

meta_init "$PROJ" "fake" "https://x" "youtube"
meta_set "$PROJ" title "T"; meta_set "$PROJ" author "A"; meta_set "$PROJ" lang "zh"
meta_set_raw "$PROJ" duration_sec "10"; meta_set "$PROJ" lane "passthrough"

# 缺音频 + 缺 cover 应该失败
if "$V4/publish/verify_local.sh" "$PROJ" >/dev/null 2>&1; then
  echo "✗ verify should fail without audio/cover"; exit 1
fi
echo "  ✓ fails when audio/cover missing"

# 造一段 1s 静音 + cover
ffmpeg -loglevel error -f lavfi -i anullsrc=r=8000:cl=mono -t 2 -q:a 9 "$PROJ/source/audio.mp3"
python3 - <<PY
import struct, zlib, pathlib
def png(w,h):
    def chunk(t,d):
        crc=zlib.crc32(t+d); return struct.pack('>I',len(d))+t+d+struct.pack('>I',crc)
    sig=b'\x89PNG\r\n\x1a\n'
    ihdr=struct.pack('>IIBBBBB',w,h,8,2,0,0,0)
    raw=b''.join(b'\x00'+b'\xff\x00\x00'*w for _ in range(h))
    idat=zlib.compress(raw)
    return sig+chunk(b'IHDR',ihdr)+chunk(b'IDAT',idat)+chunk(b'IEND',b'')
pathlib.Path('$PROJ/cover.png').write_bytes(png(32,32))
PY

"$V4/publish/verify_local.sh" "$PROJ" >/dev/null
echo "  ✓ passes when audio + cover present"

echo "✅ test_verify_local: passed"
