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

## Installing

Needs Python 3.10 or newer (developed on 3.13). From the repo root:

    python3 -m venv .venv
    .venv/bin/python -m pip install -e .

The virtual environment is deliberately not in version control — it
contains absolute paths and platform-specific binaries, so it cannot be
shared. `pyproject.toml` is the portable part: the command above rebuilds
an equivalent environment on any machine.

If that install misbehaves — most likely a dependency released something
broken since this was last tested — fall back to the exact versions known
to work:

    .venv/bin/python -m pip install -r requirements-lock.txt
    .venv/bin/python -m pip install -e . --no-deps

`requirements-lock.txt` records one known-good resolution, transitive
dependencies included. `pyproject.toml` stays the source of truth for
what the project actually requires; the lock file is a safety net for
getting a second machine to match a working one.

If `python3 -m venv` reports that `ensurepip` is unavailable, your
distribution ships venv support separately — on Debian/Ubuntu that is
`sudo apt install python3-venv`. On macOS the python.org and Homebrew
builds both include it.

## Running it

    .venv/bin/dm-tool

`dm-tool` takes no arguments — it lists the adventures it finds, offers
to resume or start a session, and hands off into the play UI. Activate
the environment (`source .venv/bin/activate`) if you would rather just
type `dm-tool`.

## Documentation

- [`docs/running-a-session.md`](docs/running-a-session.md) — how to use
  the tool at the table, with a full command reference. Start here.
- [`docs/transcribing-a-pdf-adventure.md`](docs/transcribing-a-pdf-adventure.md)
  — converting a new one-shot into the schema.
- [`docs/phase-7-plan.md`](docs/phase-7-plan.md) — design notes for the
  setup wizard.

## Tests

    .venv/bin/python -m pip install -e ".[dev]"
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
