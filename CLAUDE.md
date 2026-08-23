# Project context for Claude Code

This is a terminal-based D&D 5e one-shot DM assistant tool. Full spec,
architecture, schema design, and phased build plan live in
**`dm-tool-project-brief.md`** at the repo root — read that file in full
before doing any work here. This file is a short pointer, not a
replacement for it.

## Repo info

- **Repository:** git@github.com:am-datasci/DMTool.git
- **Default branch:** `main`
- **Code license:** GPL-3.0 — applies to the project's own source code.
- **SRD content license:** CC-BY-4.0 — applies separately to the
  rules-reference content under `rules/srd-5.1/` and `rules/srd-5.2/`,
  sourced from Wizards of the Coast's SRD. This is independent of the
  repo's GPL-3.0 code license; both apply simultaneously to their
  respective parts of the codebase. Required SRD attribution text (see
  the brief's licensing section) must stay intact in any file derived
  from or containing SRD content — don't strip it during refactors.

## Before writing any code

Read `dm-tool-project-brief.md` in full. It contains the actual
requirements, the directory layout, the schema design, and the phase-by-
phase build order. Do not start from assumptions about what a "D&D DM
tool" should look like — this project has specific, deliberate design
choices that differ from what might seem like the obvious default. The
brief explains *why*, not just *what* — that reasoning matters when you
hit an edge case the brief doesn't explicitly cover.

## Non-negotiable design rules

These were arrived at deliberately, after considering and rejecting
alternatives. Don't reintroduce the rejected alternatives without the
user explicitly asking:

1. **Content is data, engine is code — no exceptions.** Adding a new
   adventure must never require touching engine source. If you find
   yourself writing an `if adventure == "..."` branch anywhere in
   `engine/`, stop — that means the schema is missing something, not
   that a special case is fine.
2. **The DM decides everything; the tool never infers.** No automatic
   scene transitions, no guessing player intent. State changes only
   happen from explicit DM commands.
3. **Real dice, not a virtual roller.** Never implement dice-rolling.
   The tool displays DCs, formulas, and stat blocks; the DM enters
   results from physical dice they've already rolled.
4. **No LLM / generative AI component.** This was explicitly considered
   and rejected for this project (see brief for reasoning). Don't add
   one, including for "helpful" features like dialogue generation or
   rules Q&A, without being asked.
5. **No per-scene scripted skill-check trees.** Off-script player
   actions are handled by a generic, always-visible DC guideline table
   plus general DM technique tips — not by pre-authoring "if they try X,
   roll Y at DC Z" branches per scene. This was deliberately rejected as
   unscalable.
6. **Low maintenance surface, deliberately.** The user maintaining this
   long-term is comfortable with small bug fixes but does not want to
   perform major overhauls to add content. When a design choice could go
   either toward "more powerful" or "simpler and more stable," prefer
   simpler. If you're about to propose a new subsystem (a database, a
   web layer, a plugin architecture, etc.), pause and check it's
   actually justified by the brief rather than general best practice.
7. **Terminal-based, not web or GUI.** Deliberately chosen — the target
   users are terminal-comfortable. Uses Textual for the main play UI
   (persistent, redrawing panels) and plain CLI prompts for the setup
   wizard and launcher. Don't propose a web or GUI rebuild.
8. **In-tool character creation is out of scope.** Players use paper
   pregens. The setup wizard only ever *records* an existing character's
   name/class/spells — it never builds one from scratch.

## Working style for this project

- Follow the phased plan in the brief in order. Don't jump ahead to
  later phases or add features from the "explicitly deferred" list
  without being asked first.
- When the brief is ambiguous or silent on something, prefer the
  simplest option consistent with the design rules above, and say
  plainly what assumption you made rather than silently picking one.
- Schema changes are expensive once adventure content exists (they
  cascade into every adventure folder). Get the schema right before
  transcribing content, and flag clearly if a requested change would
  mean reshaping already-written adventure files.
- SRD content (`rules/srd-5.1/`, `rules/srd-5.2/`) must carry correct
  CC-BY-4.0 attribution per the brief's licensing section. Adventure
  content transcribed from purchased/downloaded modules (e.g., Wild
  Sheep Chase) is not SRD content and is not for redistribution.
- `rules/srd-5.2/` starts as a placeholder copy of `srd-5.1/` content
  (per the brief) — this is intentional, not a bug to silently "fix" by
  inventing 5.2-specific content.
- A full copy of the `BTMorton/dnd-5e-srd` project (community SRD
  content converted to Markdown/JSON/YAML) has been placed in this repo
  as raw material for building out `rules/srd-5.1/` and `rules/srd-5.2/`.
  **This is an unofficial, third-party conversion, not an authoritative
  source** — a known discrepancy check on a similar community 5.2
  conversion (different project, same category of risk) turned up real
  errors (wrong proficiency bonuses, wrong initiatives, missing items).
  Treat it as a time-saving starting point, not ground truth: when
  building the actual `rules/*.yaml` files, cross-check whatever is
  pulled from it against the official SRD PDFs linked in the brief's
  licensing section, especially for anything mechanically load-bearing
  (DCs, save formulas, monster stats the adventure actually uses).
  Don't bulk-copy it wholesale without this verification step.

## If something seems off

If a request from the user seems to contradict a rule above, or the
brief itself seems internally inconsistent, say so directly rather than
picking a side silently. These rules reflect deliberate tradeoffs made
after weighing alternatives — flagging a tension is more useful than
resolving it invisibly.
