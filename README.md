# dm-tool

A terminal-based D&D 5e one-shot DM assistant: a reference and
bookkeeping tool for a human DM, not an automation or simulation
engine. It never rolls dice, never decides outcomes, and never
generates narrative content — real dice are used at the table.

Full spec, architecture, schema design, and the phased build plan live
in [`dm-tool-project-brief.md`](dm-tool-project-brief.md).

> **Status:** phase 1 complete — content loading, the launcher, and the
> play UI's scene navigation and flags. Combat, lookup, the full SRD
> rules data, and the Wild Sheep Chase content are still to come. This
> README gets its proper install/run section in phase 8.

## Running it

    python3.13 -m venv .venv
    .venv/bin/python -m pip install -e .
    .venv/bin/dm-tool

`dm-tool` takes no arguments — it lists the adventures it finds, offers
to resume or start a session, and hands off into the play UI.

Tests need no plugins beyond pytest:

    .venv/bin/python -m pytest tests/ -q

## Licence

The project's own source code is licensed under **GPL-3.0** (see
[`LICENSE`](LICENSE)).

Rules-reference content under `rules/srd-5.1/` and `rules/srd-5.2/` is
derived from Wizards of the Coast's System Reference Document and is
licensed separately under **CC-BY-4.0**. Both licences apply
simultaneously, to their respective parts of the repo.

> This work includes material taken from the System Reference Document
> 5.1 ("SRD 5.1") by Wizards of the Coast LLC and available at
> https://dnd.wizards.com/resources/systems-reference-document. The SRD
> 5.1 is licensed under the Creative Commons Attribution 4.0
> International License, available at
> https://creativecommons.org/licenses/by/4.0/legalcode.

Adventure content under `adventures/` transcribed from purchased or
downloaded third-party modules is **not** open content and is not for
redistribution — it is a personal transcription for one table's use.

### Full rules, for players and DMs

This repo contains only the structured subset of the rules the tool
needs. For the complete rulebook:

- D&D Beyond's SRD hub (5.1 and 5.2): https://www.dndbeyond.com/srd
- D&D Basic Rules (2014), free and readable:
  https://www.dndbeyond.com/sources/dnd/basic-rules-2014
