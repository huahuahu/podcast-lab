#!/usr/bin/env python3
"""批量改 speaker 标签。用法: rename_speakers.py file.json OLD1=NEW1 OLD2=NEW2 ..."""
import json, sys
f = sys.argv[1]
mapping = dict(kv.split("=", 1) for kv in sys.argv[2:])
data = json.load(open(f))
changed = 0
for t in data:
    if t.get("speaker") in mapping:
        t["speaker"] = mapping[t["speaker"]]
        changed += 1
json.dump(data, open(f, "w"), ensure_ascii=False, indent=2)
print(f"✅ {f}: {changed}/{len(data)} turns renamed, mapping={mapping}")
