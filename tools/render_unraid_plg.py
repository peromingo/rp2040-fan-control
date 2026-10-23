#!/usr/bin/env python3
"""Render a release .plg only when real, verifiable HTTPS URLs are supplied.

This tool does not publish files or create a repository. A rendered plugin must
still be reviewed and tested in an isolated Unraid VM before release.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "plugin" / "rp2040-fan-control.plg.in"
TOKEN_NAMES = (
    "VERSION", "PLUGIN_URL", "PAYLOAD_URL", "PAYLOAD_SHA256", "SUPPORT_URL"
)


def validate_https_url(value: str, field: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or any(ch.isspace() for ch in value):
        raise ValueError(f"{field} must be an absolute HTTPS URL with a hostname")
    if parsed.username or parsed.password:
        raise ValueError(f"{field} must not contain embedded credentials")
    host = (parsed.hostname or "").lower().rstrip(".")
    reserved = (".invalid", ".example", ".test", ".localhost", "example.com", "example.org", "example.net")
    if host == "localhost" or any(host == suffix.lstrip(".") or host.endswith(suffix) for suffix in reserved):
        raise ValueError(f"{field} uses a reserved placeholder hostname")
    if any(token in value.lower() for token in ("replace_with", "your-user", "your-repo", "example-owner")):
        raise ValueError(f"{field} contains a placeholder")
    return value


def render_plg(version: str, plugin_url: str, payload_url: str,
               payload_sha256: str, support_url: str) -> str:
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9.-]+)?", version):
        raise ValueError("version must be SemVer-like, e.g. 0.6.0-dev.1")
    validate_https_url(plugin_url, "plugin_url")
    validate_https_url(payload_url, "payload_url")
    validate_https_url(support_url, "support_url")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", payload_sha256):
        raise ValueError("payload_sha256 must contain exactly 64 hexadecimal characters")

    source = TEMPLATE.read_text(encoding="utf-8")
    replacements = {
        "__VERSION__": escape(version),
        "__PLUGIN_URL__": escape(plugin_url, {'"': '&quot;'}),
        "__PAYLOAD_URL__": escape(payload_url),
        "__PAYLOAD_SHA256__": payload_sha256.lower(),
        "__SUPPORT_URL__": escape(support_url, {'"': '&quot;'}),
    }
    for token, value in replacements.items():
        source = source.replace(token, value)
    unresolved = [token for token in TOKEN_NAMES if f"__{token}__" in source]
    if unresolved or re.search(r"__[A-Z][A-Z0-9_]*__", source):
        raise ValueError("template contains unresolved placeholders")
    if "example.invalid" in source or "REPLACE_WITH_" in source:
        raise ValueError("rendered plugin contains a placeholder value")
    # Parse as XML so a bad entity or escaping change fails before writing output.
    import xml.etree.ElementTree as ET
    try:
        ET.fromstring(source)
    except ET.ParseError as exc:
        raise ValueError(f"rendered .plg is not well-formed XML: {exc}") from exc
    return source


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--plugin-url", required=True, help="real HTTPS URL of the published .plg")
    parser.add_argument("--payload-url", required=True, help="real HTTPS URL of the versioned payload")
    parser.add_argument("--payload-sha256", required=True)
    parser.add_argument("--support-url", required=True, help="real HTTPS support/documentation URL")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--force", action="store_true", help="allow replacing an existing output file")
    args = parser.parse_args()
    try:
        rendered = render_plg(args.version, args.plugin_url, args.payload_url,
                              args.payload_sha256, args.support_url)
        if args.output.exists() and not args.force:
            raise ValueError(f"output already exists (use --force to replace): {args.output}")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    except (OSError, ValueError) as exc:
        print(f"PLG NOT GENERATED: {exc}", file=sys.stderr)
        return 2
    print(f"Rendered pre-release .plg: {args.output}")
    print("Not published. Validate installer lifecycle in an isolated Unraid VM before release.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
