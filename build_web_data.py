"""Build the public-safe static snapshot consumed by the Web UI."""
from __future__ import annotations

import argparse
from pathlib import Path

from mv_analyzer.web_export import build_public_snapshot


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="web/public/data")
    ap.add_argument("--require-git-commit", action="store_true")
    args = ap.parse_args(argv)
    paths = build_public_snapshot(
        Path(args.root), Path(args.out), require_git_commit=args.require_git_commit
    )
    print(f"web snapshot: {len(paths)} files -> {Path(args.out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
