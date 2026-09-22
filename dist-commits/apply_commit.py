#!/usr/bin/env python3
"""Apply one of the trend-research commit zips onto a target repo.

Usage:
    python3 apply_commit.py <zip_file> <target_dir>

<target_dir> is where the files land, e.g. the codigo-fonte/ folder of your
repo -- NOT necessarily the folder that contains .git. This script walks up
from <target_dir> to find the enclosing git repo automatically for staging.

What it does:
    1. Extracts every file in the zip into <target_dir>, preserving the
       relative paths recorded in the zip (e.g. app/services/research.py).
    2. Reads COMMIT_MESSAGE.txt from the zip (not written to disk) and
       prints it as the suggested commit message.
    3. If <target_dir> is inside a git work tree, stages the extracted
       files with `git add` -- it does NOT commit. You review and commit
       yourself.

Example:
    python3 apply_commit.py commit-1-vendor-trendpipe-engine.zip ~/my-tcc/codigo-fonte
    cd ~/my-tcc
    git status
    git commit -m "..."   # message printed by this script
"""
import argparse
import subprocess
import sys
import zipfile
from pathlib import Path

COMMIT_MESSAGE_ENTRY = "COMMIT_MESSAGE.txt"


def is_within_directory(directory: Path, target: Path) -> bool:
    try:
        target.resolve().relative_to(directory.resolve())
        return True
    except ValueError:
        return False


def extract_safely(zf: zipfile.ZipFile, target_root: Path) -> list[str]:
    extracted: list[str] = []
    for member in zf.infolist():
        if member.filename == COMMIT_MESSAGE_ENTRY or member.is_dir():
            continue
        dest = target_root / member.filename
        if not is_within_directory(target_root, dest):
            raise ValueError(f"refusing to extract outside target dir: {member.filename}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(member) as src, open(dest, "wb") as out:
            out.write(src.read())
        extracted.append(member.filename)
    return extracted


def find_git_root(start: Path) -> Path | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def git_add(git_root: Path, target_root: Path, files: list[str]) -> bool:
    abs_paths = [str(target_root / f) for f in files]
    try:
        subprocess.run(["git", "-C", str(git_root), "add", "--", *abs_paths], check=True)
        return True
    except subprocess.CalledProcessError as exc:
        print(f"warning: could not run 'git add' automatically ({exc})", file=sys.stderr)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("zip_file", type=Path, help="one of the commit-N-*.zip files")
    parser.add_argument("target_dir", type=Path, help="folder to extract the files into")
    parser.add_argument("--no-git-add", action="store_true", help="skip staging extracted files with git add")
    args = parser.parse_args()

    if not args.zip_file.is_file():
        parser.error(f"zip not found: {args.zip_file}")
    args.target_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(args.zip_file) as zf:
        try:
            message = zf.read(COMMIT_MESSAGE_ENTRY).decode("utf-8")
        except KeyError:
            message = ""
        extracted = extract_safely(zf, args.target_dir)

    print(f"Extracted {len(extracted)} file(s) into {args.target_dir}:")
    for f in extracted:
        print(f"  {f}")

    staged = False
    git_root = None if args.no_git_add else find_git_root(args.target_dir)
    if git_root:
        staged = git_add(git_root, args.target_dir, extracted)

    print()
    if staged:
        print(f"Files staged with 'git add' (repo root: {git_root}).")
        print("Review with 'git status' / 'git diff --cached', then commit:")
    elif args.no_git_add:
        print("Skipped staging (--no-git-add). Run 'git add' yourself, then commit with:")
    else:
        print(f"warning: {args.target_dir} is not inside a git repo -- files were written but not staged.", file=sys.stderr)
        print("Run 'git add' yourself once this is inside your repo, then commit with:")
    print()
    print(f"  git commit -m \"{message.splitlines()[0] if message else 'apply ' + args.zip_file.name}\"")
    if message:
        print()
        print("Suggested full commit message:")
        print("-" * 40)
        print(message)
        print("-" * 40)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
