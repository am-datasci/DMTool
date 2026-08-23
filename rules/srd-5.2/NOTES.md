# SRD 5.2 — provisional content

**The YAML data files in this folder are a verbatim copy of
`rules/srd-5.1/`, taken on 2026-08-23. They are SRD 5.1 content, not
SRD 5.2 content.**

## Why this exists

Adventures declare a ruleset in their manifest and the engine loads the
matching folder under `rules/`. Seeding this folder makes that selection
path real and exercised, rather than a branch that has only ever run one
way — without blocking v1 on a second full transcription.

An adventure whose manifest says `ruleset: srd-5.2` will run today. It
will simply be running 5.1 rules under a 5.2 label.

## What is actually different in SRD 5.2

Enough to matter. 5.2 revises conditions (Exhaustion in particular),
changes a number of spells, and reworks stat blocks. Do not assume any
value in these files is correct for 5.2 — assume none of them are until
the file has been re-transcribed and this notice removed from it.

## Replacing this with real content

See `docs/adding-a-ruleset.md`. The source is
`reference/SRD_CC_v5.2.1.pdf`, and the same verification rule applies as
for 5.1: the community conversions in `reference/` are unofficial and
were found to contain real errors — 15 spells missing outright from one
of them — so cross-check against the official PDF rather than
bulk-copying. The provenance header in `rules/srd-5.1/spells.yaml`
records what went wrong and how it was caught.

Each file carries the SRD 5.1 attribution because that is what its
content is. When a file is genuinely re-transcribed from 5.2, its
attribution must be replaced with the notice SRD 5.2 specifies — it is a
different string, and leaving the 5.1 notice on 5.2 content would be an
incorrect attribution.

## Checking whether this is still a copy

    diff -r rules/srd-5.1 rules/srd-5.2

Any file that still matches its 5.1 counterpart has not been transcribed
yet.
