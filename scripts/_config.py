"""Resolve the effective config for a project by merging:
  1. series defaults from configs/series.json (first regex match on slug)
  2. project-level meta.json (overrides series)

Returns a dict with at least: show, host, guest, voices, chapters.
"""
import json, os, re

def _repo_root(start):
    p = os.path.abspath(start)
    while p != "/":
        if os.path.exists(os.path.join(p, ".git")) or \
           os.path.exists(os.path.join(p, "configs", "series.json")):
            return p
        p = os.path.dirname(p)
    return os.path.abspath(start)

def _deep_merge(a, b):
    """b overrides a (recursive for dicts)."""
    if not isinstance(a, dict) or not isinstance(b, dict):
        return b if b is not None else a
    out = dict(a)
    for k, v in b.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out

def resolve(project_dir):
    project_dir = os.path.abspath(project_dir)
    slug = os.path.basename(project_dir)
    repo = _repo_root(project_dir)

    series_path = os.path.join(repo, "configs", "series.json")
    series_cfg = {}
    matched = None
    if os.path.exists(series_path):
        try:
            data = json.load(open(series_path))
            for s in data.get("series", []):
                pat = s.get("match")
                if pat and re.search(pat, slug):
                    series_cfg = {k: v for k, v in s.items() if k not in ("id", "match")}
                    matched = s.get("id")
                    break
        except Exception as e:
            print(f"⚠️  series.json 读失败: {e}")

    proj_meta = {}
    meta_path = os.path.join(project_dir, "meta.json")
    if os.path.exists(meta_path):
        try:
            proj_meta = json.load(open(meta_path))
        except Exception as e:
            print(f"⚠️  {meta_path} 读失败: {e}")

    merged = _deep_merge(series_cfg, proj_meta)
    if matched:
        merged.setdefault("_series", matched)
    return merged
