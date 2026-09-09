#!/usr/bin/env python3
"""Audit a generated public-release tree for privacy/copyright hygiene blockers."""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

FORBIDDEN_PATHS = {
    "CLAUDE.md", ".claude", "docs/superpowers", "pilot",
    "docs/reports/dashboard.html", "docs/reports/mv-space.html", "docs/reports/vendor",
    "work/population.jsonl", "work/kpop/population.jsonl", "work/batch.log", "work/enumerate.log",
    "work/kpop/enumerate.log", "work/reliability_images.txt",
}
FORBIDDEN_DATA_KEYS = {"thumb_text_content", "raw_lyrics", "lyrics_lines", "lyrics_ocr", "cookies", "cookie", "request_headers", "vlm_prompt", "vlm_response", "media_url", "video_url", "local_path"}
GENERATED_DIR_NAMES = {"node_modules", "dist", "build", "coverage", "test-results", "playwright-report", ".venv", "venv", "__pycache__"}

TEXT_SUFFIXES = {".md", ".txt", ".json", ".jsonl", ".csv", ".toml", ".yml", ".yaml", ".cff", ".html", ".py", ".ts", ".tsx", ".js", ".mjs"}
PRIVATE_PATTERNS = [
    re.compile(r"C:\\Users\\(?:SIHYEONG|sihye)\\", re.I),
    re.compile(r"(?:100\.(?:6[4-9]|[78]\d|9\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3})"),
    re.compile(r"[a-z0-9-]+\.tail[a-z0-9-]*\.ts\.net", re.I),
]
SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{24,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{24,}\b"),
]


def _walk_json(value, path=""):
    if isinstance(value, dict):
        for key, child in value.items():
            yield path, key
            yield from _walk_json(child, f"{path}.{key}" if path else key)
    elif isinstance(value, list):
        for i, child in enumerate(value):
            yield from _walk_json(child, f"{path}[{i}]")


def _auditable(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    return not any(part in GENERATED_DIR_NAMES for part in rel.parts) and path.suffix.lower() != ".pyc"


def audit_public_release(root: Path) -> list[str]:
    root = root.resolve(); errors=[]
    rels={p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and _auditable(p, root)}
    for blocked in FORBIDDEN_PATHS:
        if blocked in rels or any(rel.startswith(blocked.rstrip('/') + '/') for rel in rels):
            errors.append(f"forbidden release path: {blocked}")
    required={"LICENSE","NOTICE","THIRD_PARTY_LICENSES.md","DATA_LICENSE.md","SECURITY.md","CONTRIBUTING.md","CITATION.cff","PUBLIC_RELEASE_MANIFEST.json"}
    for name in sorted(required-rels): errors.append(f"missing release file: {name}")

    for path in root.rglob("*"):
        if not path.is_file() or not _auditable(path, root): continue
        rel=path.relative_to(root).as_posix()
        if path.stat().st_size > 2_000_000:
            errors.append(f"oversized public file: {rel}")
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {"LICENSE","NOTICE"}:
            continue
        try: text=path.read_text(encoding='utf-8-sig')
        except UnicodeDecodeError: continue
        if rel not in {"scripts/audit_public_release.py", "scripts/audit_git_history.py"} and "data:image/" in text and "base64," in text:
            errors.append(f"embedded base64 media: {rel}")
        # Source/tests contain deliberate privacy-regex fixtures. Privacy literals are forbidden in docs/data/config surfaces.
        if rel.startswith(("docs/","dataset/","work/")) or rel in {"README.md","README.ko.md","PUBLIC_RELEASE_MANIFEST.json"}:
            for pattern in PRIVATE_PATTERNS:
                if pattern.search(text): errors.append(f"private path/network literal: {rel}")
        if rel not in {"scripts/audit_public_release.py", "scripts/audit_git_history.py"}:
            for pattern in SECRET_PATTERNS:
                if pattern.search(text): errors.append(f"secret-like token: {rel}")
        if path.suffix.lower()=='.csv':
            reader=csv.reader(text.splitlines()); header=next(reader,[])
            for key in FORBIDDEN_DATA_KEYS.intersection(header): errors.append(f"forbidden CSV field {key}: {rel}")
        elif path.suffix.lower() in {'.json','.jsonl'} and rel.startswith(("dataset/","work/","examples/","web/public/data/")):
            try:
                values=[json.loads(line) for line in text.splitlines() if line.strip()] if path.suffix.lower()=='.jsonl' else [json.loads(text)]
            except json.JSONDecodeError:
                values=[]
            for value in values:
                for _,key in _walk_json(value):
                    if key in FORBIDDEN_DATA_KEYS: errors.append(f"forbidden JSON field {key}: {rel}"); break
    return sorted(set(errors))


def main(argv=None):
    parser=argparse.ArgumentParser(); parser.add_argument('root',type=Path); args=parser.parse_args(argv)
    errors=audit_public_release(args.root)
    if errors:
        for error in errors: print(f"ERR {error}")
        print(f"public release audit: {len(errors)} blocker(s)")
        return 1
    print("public release audit: clean")
    return 0

if __name__=='__main__': raise SystemExit(main())
