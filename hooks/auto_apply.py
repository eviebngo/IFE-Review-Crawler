#!/usr/bin/env python3
"""Auto-apply updates from the `updates/` folder to allowed files and optionally stage/commit them.

Usage:
  python hooks/auto_apply.py --apply --stage
  python hooks/auto_apply.py --apply --stage --commit "Apply allowed updates"

This script only writes files listed in `allowed_files.json` at repository root.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ALLOWED_FILE = os.path.join(ROOT, "allowed_files.json")
UPDATES_DIR = os.path.join(ROOT, "updates")


def run(cmd):
    return subprocess.run(cmd, shell=False, cwd=ROOT, check=False)


def load_allowed():
    if not os.path.exists(ALLOWED_FILE):
        return []
    with open(ALLOWED_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def apply_updates(allowed, stage=False):
    applied = []
    for rel in allowed:
        src = os.path.join(UPDATES_DIR, rel)
        dst = os.path.join(ROOT, rel)
        if os.path.exists(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            applied.append(rel)
            if stage:
                run(["git", "add", rel])
    return applied


def commit_if_needed(message: str):
    if message:
        run(["git", "commit", "-m", message])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Apply updates from updates/ for allowed files")
    parser.add_argument("--stage", action="store_true", help="Run git add on applied files")
    parser.add_argument("--commit", nargs="?", const="Apply allowed updates", help="Commit changes with optional message")
    args = parser.parse_args()

    allowed = load_allowed()
    if not allowed:
        print("No allowed_files.json found or empty. Nothing to do.")
        return 0

    if not args.apply:
        print("--apply not set; exiting.")
        return 0

    applied = apply_updates(allowed, stage=args.stage)
    if applied:
        print(f"Applied updates to: {applied}")
        if args.commit is not None:
            commit_if_needed(args.commit)
    else:
        print("No updates found in updates/ for allowed files.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
