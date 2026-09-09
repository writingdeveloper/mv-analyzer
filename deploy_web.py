"""Deploy the Web Research Explorer to Vercel with exact Git provenance."""
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


DEFAULT_VERCEL_SCOPE = "sihyeong-lees-projects-64e0ba83"


def deployment_command(
    commit: str, *, production: bool, scope: str = DEFAULT_VERCEL_SCOPE
) -> list[str]:
    command = [
        "vercel",
        "--yes",
        "--scope",
        scope,
        "--build-env",
        f"MV_ANALYZER_GIT_COMMIT={commit}",
    ]
    if production:
        command.append("--prod")
    return command


def _git(root: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return proc.stdout.strip()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Deploy a clean mv-analyzer HEAD to Vercel with manifest provenance."
    )
    parser.add_argument("--prod", action="store_true", help="deploy to production instead of preview")
    parser.add_argument("--root", default=".")
    parser.add_argument("--scope", default=DEFAULT_VERCEL_SCOPE)
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    dirty = _git(root, "status", "--porcelain")
    if dirty:
        raise SystemExit("refusing to deploy a dirty worktree; commit or stash changes first")

    commit = _git(root, "rev-parse", "HEAD")
    command = deployment_command(commit, production=args.prod, scope=args.scope)
    executable = shutil.which(command[0])
    if executable is None:
        raise SystemExit("Vercel CLI was not found on PATH")
    command[0] = executable
    return subprocess.run(command, cwd=root).returncode


if __name__ == "__main__":
    raise SystemExit(main())
