#!/usr/bin/env python3
"""Report whether the existing Git history can be exposed directly without rewrite."""
from __future__ import annotations
import argparse,re,subprocess
from pathlib import Path

PATTERNS={
 "private_path": re.compile(rb"C:\\\\Users\\\\(?:SIHYEONG|sihye)\\\\",re.I),
 "private_network": re.compile(rb"100\\.(?:6[4-9]|[78]\\d|9\\d|1[01]\\d|12[0-7])\\.\\d{1,3}\\.\\d{1,3}"),
 "private_key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
 "github_token": re.compile(rb"\\bgh[pousr]_[A-Za-z0-9_]{24,}\\b"),
 "openai_key": re.compile(rb"\\bsk-[A-Za-z0-9_-]{24,}\\b"),
 "embedded_base64": re.compile(rb"data:image/[^;]+;base64,",re.I),
 "thumbnail_ocr_field": re.compile(rb"thumb_text_content"),
}

def audit_history(root:Path):
    objects=subprocess.check_output(["git","-C",str(root),"rev-list","--objects","--all"],text=True,encoding='utf-8',errors='replace').splitlines()
    found={k:set() for k in PATTERNS}
    for line in objects:
        oid,_,name=line.partition(' ')
        if not name: continue
        proc=subprocess.run(["git","-C",str(root),"cat-file","-p",oid],capture_output=True)
        if proc.returncode or len(proc.stdout)>12_000_000: continue
        for key,pat in PATTERNS.items():
            if key == "embedded_base64" and not name.startswith(("docs/", "dataset/", "work/", "pilot/", "examples/", "web/public/")):
                continue
            if key == "thumbnail_ocr_field" and not (name.startswith(("dataset/", "work/", "pilot/", "examples/", "web/public/")) and name.lower().endswith((".csv", ".json", ".jsonl"))):
                continue
            if pat.search(proc.stdout):
                found[key].add(name)
    return {k:sorted(v) for k,v in found.items() if v}

def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]); ap.add_argument('--json',action='store_true'); args=ap.parse_args(argv)
    result=audit_history(args.root)
    import json
    if args.json: print(json.dumps({k:{"count":len(v),"examples":v[:5]} for k,v in result.items()},indent=2))
    else:
        for k,v in result.items(): print(f"{k}: {len(v)} blob path(s); examples={v[:3]}")
    # Any private/history-only content means direct visibility flip is not approved.
    return 1 if result else 0
if __name__=='__main__': raise SystemExit(main())
