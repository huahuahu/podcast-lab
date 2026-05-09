#!/usr/bin/env bash
# test_cover_fetch.sh — cover_fetch 优先级测试（用本地 thumbnail.jpg）
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
V4="$SCRIPT_DIR/../scripts/v4"
source "$V4/lib/meta.sh"

PROJ=$(mktemp -d)
trap 'rm -rf "$PROJ"' EXIT
meta_init "$PROJ" "fake" "https://x" "youtube"

# 造一张 8x8 红色 png 当 thumbnail
python3 - <<PY
import struct, zlib, pathlib
def png(w, h, rgb=(255,0,0)):
    def chunk(t,d):
        crc=zlib.crc32(t+d)
        return struct.pack('>I',len(d))+t+d+struct.pack('>I',crc)
    sig=b'\x89PNG\r\n\x1a\n'
    ihdr=struct.pack('>IIBBBBB',w,h,8,2,0,0,0)
    raw=b''.join(b'\x00'+bytes(rgb)*w for _ in range(h))
    idat=zlib.compress(raw)
    return sig+chunk(b'IHDR',ihdr)+chunk(b'IDAT',idat)+chunk(b'IEND',b'')
pathlib.Path('$PROJ/source/thumbnail.png').write_bytes(png(64,64))
PY

"$V4/enrich/cover_fetch.sh" "$PROJ"

[ -f "$PROJ/cover.png" ] || { echo "✗ cover.png missing"; exit 1; }
size=$(sips -g pixelWidth "$PROJ/cover.png" | awk '/pixel/{print $2}')
echo "  ✓ cover.png produced (width=${size}px)"

echo "✅ test_cover_fetch: passed"
