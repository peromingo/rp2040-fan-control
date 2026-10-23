#!/usr/bin/env python3
"""Fail-closed audit for source trees and review payloads before publication.

This deliberately checks structural privacy hazards. It does not replace a
human review of source ownership, credentials, logs, or hardware identifiers.
"""
from __future__ import annotations

import argparse
import sys
import tarfile
from pathlib import Path, PurePosixPath

FORBIDDEN_DIRS = {"__pycache__", ".git", ".venv", "node_modules", "dist", "logs"}
FORBIDDEN_SUFFIXES = {".pyc", ".pyo", ".pyd"}
FORBIDDEN_BASENAMES = {
    "site_config_local.py",
    "site_config.py",
    ".env",
    "daemon-console.log",
    "command.json",
    "status.json",
    "command-result.json",
}


def audit_tree(root: Path) -> list[str]:
    issues: list[str] = []
    if not root.is_dir():
        return [f"not a directory: {root}"]
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        # GitHub Actions checks out a repository with its own .git metadata.
        # Ignore only the root checkout metadata; nested .git directories remain
        # forbidden, and release payloads are still audited independently.
        if rel.parts and rel.parts[0] == ".git":
            continue
        if any(part in FORBIDDEN_DIRS for part in rel.parts):
            issues.append(f"forbidden directory/artifact path: {rel.as_posix()}")
            continue
        if path.is_file():
            if path.name in FORBIDDEN_BASENAMES:
                issues.append(f"host-specific/private artifact: {rel.as_posix()}")
            if path.suffix.lower() in FORBIDDEN_SUFFIXES:
                issues.append(f"compiled Python artifact: {rel.as_posix()}")
    required = [
        "LICENSE",
        "README.md",
        "src/unraid/fan_control/site_config.example.py",
        "docs/GITHUB-PUBLICATION.md",
        ".github/workflows/ci.yml",
        "plugin/rp2040-fan-control.plg.in",
        "plugin/scripts/install-from-payload.sh",
        "tools/render_unraid_plg.py",
        "tests/test_plg_template.py",
    ]
    for rel in required:
        if not (root / rel).is_file():
            issues.append(f"required publication file missing: {rel}")
    return issues


def audit_tar(archive: Path) -> list[str]:
    issues: list[str] = []
    if not archive.is_file():
        return [f"archive not found: {archive}"]
    try:
        with tarfile.open(archive, "r:gz") as tf:
            for member in tf.getmembers():
                path = PurePosixPath(member.name)
                if any(part in FORBIDDEN_DIRS for part in path.parts):
                    issues.append(f"forbidden archive path: {member.name}")
                if path.name in FORBIDDEN_BASENAMES:
                    issues.append(f"host-specific/private archive member: {member.name}")
                if path.suffix.lower() in FORBIDDEN_SUFFIXES:
                    issues.append(f"compiled Python archive member: {member.name}")
                if member.issym() or member.islnk():
                    issues.append(f"links are not allowed in release payload: {member.name}")
    except (tarfile.TarError, OSError) as exc:
        issues.append(f"cannot read payload archive: {exc}")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="source tree or payload .tar.gz")
    parser.add_argument("--payload", action="store_true", help="audit a payload TAR.GZ")
    args = parser.parse_args()
    issues = audit_tar(args.path) if args.payload else audit_tree(args.path)
    if issues:
        print("PUBLICATION AUDIT FAILED", file=sys.stderr)
        for issue in issues:
            print(f"- {issue}", file=sys.stderr)
        return 1
    print("Publication structure audit passed. Human source/license/security review is still required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
