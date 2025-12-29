#!/usr/bin/env python3
import json, os, pathlib, sys

EXTRACT_ENV = os.environ.get("WARP_OPEN_EXTRACT_DIR")
EXTRACT = pathlib.Path(os.path.expanduser(EXTRACT_ENV)) if EXTRACT_ENV else pathlib.Path(os.path.expanduser("~/ReverseLab/Warp_Archive/Extract"))
OUTDIR_ENV = os.environ.get("WARP_OPEN_OUTDIR")
OUTDIR  = pathlib.Path(os.path.expanduser(OUTDIR_ENV)) if OUTDIR_ENV else pathlib.Path(os.path.expanduser("~/.warp_open"))
OUT     = OUTDIR/"workflows.json"

SOURCES = [
    "mined_workflow.json",
    "mined_block.json",
    "mined_segments_normalized.json"
]

def load_many():
    merged = []
    for name in SOURCES:
        p = EXTRACT / name
        if not p.exists():
            continue
        try:
            txt = p.read_text(encoding='utf-8')
            if not txt.strip():
                continue
            data = json.loads(txt)
            if isinstance(data, list):
                merged.extend(data)
        except Exception:
            pass
    return merged


def normalize(items):
    out = []
    for it in items:
        if not isinstance(it, dict):
            continue
        cmd = it.get("command") or it.get("cmd") or it.get("shell")
        if not isinstance(cmd, str) or not cmd.strip():
            continue
        base = it.get("base_cwd") or os.environ.get("SHORTCUTS_CWD") or "~"
        name = it.get("name") or it.get("title") or cmd.strip().split(" ")[0]
        tags = it.get("tags") if isinstance(it.get("tags"), list) else []
        src  = it.get("source_path") or it.get("source") or "mined"
        out.append({
            "name": name,
            "command": cmd.strip(),
            "kind": it.get("kind") or "workflow",
            "base_cwd": base,
            "tags": tags,
            "source": src
        })
    # de-dup by (name, command)
    seen = set()
    dedup = []
    for r in out:
        k = (r["name"], r["command"])
        if k in seen:
            continue
        seen.add(k)
        dedup.append(r)
    return dedup


def main():
    merged = load_many()
    nw = normalize(merged)
    OUTDIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(nw, indent=2), encoding='utf-8')
    print(f"Wrote {len(nw)} workflows → {OUT}")

if __name__ == "__main__":
    main()
