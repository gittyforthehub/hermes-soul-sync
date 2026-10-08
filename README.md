# hermes-soul-sync

Give every [Hermes Agent](https://hermes-agent.nousresearch.com) profile the same shared foundation (how it talks to you, how it works, what it must ask before doing) while each agent keeps its own identity and instructions.

## The problem

Each Hermes profile reads its own `SOUL.md`, and Hermes has no include or inheritance for it. So rules you want everywhere get pasted into every profile by hand, and the copies drift apart.

Symlinking one file into every profile doesn't work: `SOUL.md` is also the agent's identity, so every agent would become the same agent.

## How it works

1. You write the shared rules once, in `$HERMES_HOME/shared/soul-baseline.md`.
2. `sync-souls.py` writes that text into every profile's `SOUL.md`, between `<!-- shared:begin -->` and `<!-- shared:end -->`.
3. Everything outside the markers (the agent's own identity and instructions) is kept.
4. `--check` reports which profiles are out of date, so drift is visible instead of silent.

```text
SOUL.md
├── agent's own intro
├── <!-- shared:begin -->   ← generated from soul-baseline.md
│   shared rules
├── <!-- shared:end -->
└── agent's own instructions
```

## Usage

```bash
mkdir -p ~/.hermes/shared
cp soul-baseline.example.md ~/.hermes/shared/soul-baseline.md   # then edit it

python3 sync-souls.py --check      # list stale profiles; exit 1 if any (cron-safe)
python3 sync-souls.py --dry-run    # show the diff for each profile, write nothing
python3 sync-souls.py --write      # apply; backs up each changed file to SOUL.md.bak-shared-sync
python3 sync-souls.py --selftest   # confirm a second run changes nothing
```

Targets: `$HERMES_HOME/SOUL.md` and `$HERMES_HOME/profiles/*/SOUL.md`. Set `SOUL_BASELINE` to use a different baseline file. Start a new session after syncing; Hermes reads `SOUL.md` at session start.

**Notes**
- Every `## ` heading in the baseline belongs to the shared block. If a profile has its own hand-copied section under one of those headings, it is removed so the rule exists once.
- The shared rules are prompt text. Nothing enforces them; they are followed the way the rest of `SOUL.md` is.
- No dependencies beyond Python 3.9+.

## Background

Built on 2026-09-27 for my own Hermes setup. The same pattern later went into my [Bot Forge fork](https://github.com/gittyforthehub/hermes-bot-forge) as its shared operating policy, with a fingerprint-based drift check ([docs](https://github.com/gittyforthehub/hermes-bot-forge/blob/main/docs/shared-policy.md)). The underlying technique, generated text between markers plus a staleness check, is old and well proven; see [Cog](https://nedbatchelder.com/code/cog/). Designed by me, written by my AI agents.

MIT licensed.
