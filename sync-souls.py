#!/usr/bin/env python3
"""Propagate the canonical shared identity block into every SOUL.md.

Source of truth: $HERMES_HOME/shared/soul-baseline.md  (override: SOUL_BASELINE)
Targets:         $HERMES_HOME/SOUL.md  +  $HERMES_HOME/profiles/*/SOUL.md

The block is delimited by <!-- shared:begin --> / <!-- shared:end --> markers.
Each agent's own text outside the markers is kept. The block owns every `## `
heading in the baseline; a hand-copied duplicate of one of those sections
elsewhere in a SOUL.md is removed before insertion, so running twice is a no-op.

Modes:
  --check    report drift, exit 1 if any target is stale   (cron-safe)
  --dry-run  print a unified diff per target, write nothing
  --write    apply
  --selftest prove idempotency on temp copies, then exit
"""
from __future__ import annotations
import difflib
import glob
import os
import shutil
import sys
import tempfile

HOME = os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes"))
BASELINE = os.environ.get("SOUL_BASELINE") or os.path.join(HOME, "shared", "soul-baseline.md")
BEGIN = "<!-- shared:begin -->"
END = "<!-- shared:end -->"


BUDGET = 4000  # chars; injected into every session of every agent


def baseline_body() -> str:
    """Baseline content with the leading HTML doc comment removed.

    The comment block spans lines and ends with '-->', so drop through the
    first closing marker rather than filtering only lines that open with '<!--'.
    """
    lines = open(BASELINE, encoding="utf-8").read().splitlines()
    start = 0
    while start < len(lines) and not lines[start].strip():
        start += 1
    if start < len(lines) and lines[start].lstrip().startswith("<!--"):
        i = start
        while i < len(lines) and "-->" not in lines[i]:
            i += 1
        lines = lines[i + 1:]
    return "\n".join(lines).strip("\n")


def block() -> str:
    return f"{BEGIN}\n{baseline_body()}\n{END}"


def owned() -> set[str]:
    """Headings the block owns: every `## ` heading in the baseline."""
    return {ln.strip() for ln in baseline_body().splitlines() if ln.startswith("## ")}


def strip_owned(text: str) -> str:
    """Drop each owned heading and its body, up to the next ## heading."""
    out, skipping, own = [], False, owned()
    for line in text.splitlines():
        if line.startswith("## "):
            skipping = line.strip() in own
        if not skipping:
            out.append(line)
    return "\n".join(out)


def strip_existing_block(text: str) -> str:
    if BEGIN not in text or END not in text:
        return text
    head, _, rest = text.partition(BEGIN)
    _, _, tail = rest.partition(END)
    return head.rstrip("\n") + "\n" + tail.lstrip("\n")


def insertion_index(lines: list[str]) -> int:
    """Insert before the first ## section heading (stable section boundary).

    Preferring the heading over the first blank line keeps re-runs identical:
    stripping the block consumes the surrounding blank line, and a blank-line
    boundary would then land inside a heading/body pair and split them.
    """
    for i, line in enumerate(lines):
        if line.startswith("## "):
            return i
    for i, line in enumerate(lines[:8]):
        if i and not line.strip():
            return i
    return len(lines)


def render(text: str) -> str:
    # Remove the old block before stripping owned sections: an owned section at the
    # end of the block would otherwise swallow the end marker and the block would
    # be duplicated on every run.
    cleaned = strip_owned(strip_existing_block(text))
    lines = cleaned.splitlines()
    i = insertion_index(lines)
    head = "\n".join(lines[:i]).rstrip("\n")
    tail = "\n".join(lines[i:]).lstrip("\n")
    parts = [p for p in (head, block(), tail) if p.strip()]
    return "\n\n".join(parts).rstrip("\n") + "\n"


def targets() -> list[str]:
    found = [os.path.join(HOME, "SOUL.md")]
    found += sorted(glob.glob(os.path.join(HOME, "profiles", "*", "SOUL.md")))
    # Skip hidden/internal profile homes (.ops-*), never the Hermes home itself.
    keep = []
    for p in found:
        parent = os.path.basename(os.path.dirname(p))
        if parent == ".hermes" or not parent.startswith("."):
            if os.path.isfile(p):
                keep.append(p)
    return keep


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "--check"
    if mode not in ("--check", "--dry-run", "--write", "--selftest"):
        print(__doc__)
        return 2

    if mode == "--selftest":
        tmp = tempfile.mkdtemp()
        try:
            for src in targets():
                dst = os.path.join(tmp, os.path.basename(os.path.dirname(src)) + "-" + os.path.basename(src))
                once = render(open(src, encoding="utf-8").read())
                twice = render(once)
                if once != twice:
                    print(f"FAIL not idempotent: {src}")
                    return 1
            print(f"PASS idempotent on {len(targets())} targets")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        return 0

    b = len(baseline_body())
    print(f"baseline: {b} chars (budget {BUDGET})" + ("  ** OVER BUDGET **" if b > BUDGET else ""))

    stale, drift = 0, []
    for path in targets():
        cur = open(path, encoding="utf-8").read()
        new = render(cur)
        name = path.replace(os.path.expanduser("~"), "~")
        if new == cur:
            print(f"  ok    {name}")
            continue
        stale += 1
        delta = len(new) - len(cur)
        print(f"  STALE {name}  ({delta:+d} chars)")
        if mode == "--dry-run":
            diff = difflib.unified_diff(cur.splitlines(), new.splitlines(), name, name, lineterm="", n=2)
            drift.append("\n".join(diff))
        elif mode == "--write":
            shutil.copy2(path, path + ".bak-shared-sync")
            open(path, "w", encoding="utf-8").write(new)

    if mode == "--dry-run" and drift:
        print("\n" + "\n".join(drift))
    print(f"\n{stale}/{len(targets())} targets need sync")
    return 1 if (mode == "--check" and stale) else 0


if __name__ == "__main__":
    raise SystemExit(main())
