"""
MTHANDIZI — language pack lint.

Walks chichewa_pack.json and flags every entry that is structurally broken.
This is what stands between "we translated the app" and "we hope we did".

Checks, per leaf entry that has a "chi" field:
  MISSING_CHI       - "chi" key absent
  EMPTY_CHI         - "chi" is blank or whitespace only
  IDENTICAL_TO_EN   - "chi" == "en" (a strong sign of an untranslated placeholder)
  UNREVIEWED        - "reviewed" is not true (only enforced with --strict)
  BAD_PLACEHOLDER   - "{...}" tokens in "chi" don't match those in "en"
                       (dynamic strings whose substitutions have drifted apart)
  NO_AUDIO_NO_NOTE  - "audio" is null with no "note" explaining why
                       (a static prompt with no recording and no excuse is a gap)

Exit code 0 = clean. Exit code 1 = problems found (or, with --strict, anything
still unreviewed). CI / a pre-release build should run this with --strict.

USAGE
-----
    python lint_pack.py                    # dev mode: structural issues only
    python lint_pack.py --strict           # release mode: also requires reviewed=true
    python lint_pack.py --pack path.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")

DEFAULT_PACK = Path(__file__).parent.parent / "pack" / "chichewa_pack.json"


def walk_leaves(node, path: str = ""):
    """Yield (dotted_path, dict) for every leaf dict that looks like a string entry."""
    if isinstance(node, dict):
        # A leaf is a translation entry: it has 'chi' and/or 'en'. Checking BOTH
        # keys (not just 'chi') matters — an entry missing 'chi' entirely must
        # still be visited so MISSING_CHI can fire, rather than silently recursing
        # past it because the trigger key wasn't there.
        if "chi" in node or "en" in node:
            yield path, node
        else:
            for key, value in node.items():
                yield from walk_leaves(value, f"{path}.{key}" if path else key)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from walk_leaves(value, f"{path}[{index}]")


def lint(pack: dict, strict: bool) -> list[str]:
    problems: list[str] = []

    for path, entry in walk_leaves(pack):
        chi = entry.get("chi")
        en = entry.get("en", "")

        if chi is None:
            problems.append(f"MISSING_CHI       {path}")
            continue
        if not str(chi).strip():
            problems.append(f"EMPTY_CHI         {path}")
            continue
        identical = en and str(chi).strip().lower() == str(en).strip().lower()
        if identical and not entry.get("exempt_identical"):
            problems.append(
                f"IDENTICAL_TO_EN   {path}  ({chi!r}) "
                f"— if this is intentional (a proper noun), add \"exempt_identical\": true"
            )

        chi_tokens = set(PLACEHOLDER_RE.findall(str(chi)))
        en_tokens = set(PLACEHOLDER_RE.findall(str(en)))
        if chi_tokens != en_tokens:
            problems.append(
                f"BAD_PLACEHOLDER   {path}  chi has {chi_tokens or '{}'}, "
                f"en has {en_tokens or '{}'}"
            )

        if "audio" in entry and entry["audio"] is None and not entry.get("note"):
            problems.append(f"NO_AUDIO_NO_NOTE  {path}")

        if strict and entry.get("reviewed") is not True:
            problems.append(f"UNREVIEWED        {path}")

    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description="MTHANDIZI language pack lint")
    parser.add_argument("--pack", default=str(DEFAULT_PACK))
    parser.add_argument("--strict", action="store_true",
                        help="also fail on anything not yet reviewed=true (release mode)")
    args = parser.parse_args()

    pack_path = Path(args.pack)
    if not pack_path.exists():
        sys.exit(f"No pack at {pack_path}")

    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    problems = lint(pack, args.strict)

    leaf_count = sum(1 for _ in walk_leaves(pack))
    reviewed_count = sum(1 for _, e in walk_leaves(pack) if e.get("reviewed") is True)

    print(f"MTHANDIZI language pack lint — {pack_path}")
    print(f"  {leaf_count} entries, {reviewed_count}/{leaf_count} reviewed")
    print(f"  mode: {'STRICT (release)' if args.strict else 'dev (structural only)'}")
    print()

    if not problems:
        print("Clean." if not args.strict or reviewed_count == leaf_count else "")
        sys.exit(0)

    by_kind: dict[str, int] = {}
    for problem in problems:
        kind = problem.split()[0]
        by_kind[kind] = by_kind.get(kind, 0) + 1
        print(problem)

    print(f"\n{len(problems)} problem(s):")
    for kind, count in sorted(by_kind.items()):
        print(f"  {kind}: {count}")

    sys.exit(1)


if __name__ == "__main__":
    main()
