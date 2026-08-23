# Terminal D&D One-Shot DM Tool — Project Brief

## Purpose

A terminal-based dungeon master assistant for running D&D 5e one-shot
adventures. Built first to run "The Wild Sheep Chase" for a friend's kids as
their first D&D session, then handed off so that friend can run it
themselves and eventually add new one-shots without needing the original
developer's involvement.

This is a **reference and bookkeeping tool for a human DM**, not an
automation or simulation engine. Real dice are used at the table. The tool
never rolls dice, never decides outcomes, and never generates narrative
content on its own. Its job is to keep relevant information on screen,
track state (HP, initiative, conditions, story flags), and gently support a
first-time DM with reference material and technique tips — while staying
out of the way.

## Design philosophy (read this before writing code)

1. **Content is data, engine is code — no exceptions.** Adding a new
   one-shot must never require touching engine source. If a change to
   support new content means editing Python, the schema is wrong and needs
   to be fixed, not worked around.
2. **The DM decides everything; the tool never infers.** State changes
   (scene transitions, damage, conditions) happen because the DM issued an
   explicit command, never because the tool guessed player intent.
3. **Low maintenance surface, deliberately.** The person running this
   long-term is comfortable fixing small bugs but does not want to perform
   major overhauls to add content. Simplicity and a stable schema matter
   more than feature richness. When in doubt, cut scope rather than add a
   new subsystem.
4. **Real dice, not a virtual roller.** The tool never rolls for the
   player or DM. It shows DCs, formulas, and stat blocks; the DM enters
   results from physical dice.
5. **No AI/LLM component.** Considered and deliberately rejected — the
   maintenance and reliability cost (new runtime dependency, live failure
   risk at the table) wasn't worth it against static, authored guidance,
   which is also more pedagogically useful for a new DM learning to
   improvise.

## Audience

- **Primary near-term user:** the developer, running Wild Sheep Chase for
  a friend's kids (first D&D session, all new players).
- **Primary long-term user:** the friend, a first-time DM, who will run
  this same adventure and potentially add future one-shots to the tool.
  Assume terminal fluency (Mac/Linux) — this is not a constraint that
  needs solving with a GUI or web app.
- Design for a **new DM's cognitive load** during live play: minimal
  keybindings, information surfaced proactively rather than requiring
  recall of commands, gentle rather than naggy guidance.

## Platform & tech stack

- **Python**, using **[Textual](https://textual.textualize.io/)** for the
  terminal UI (persistent, redrawing panel layout — not a scrolling
  REPL/log). Textual is cross-platform (Linux/Mac/Windows terminals) via
  `rich` underneath, so no per-OS porting work is expected beyond a
  smoke-test on Windows Terminal if ever relevant.
- **YAML** for all content and data files (adventures, rules reference,
  session/PC data) — human-readable, diffable, and approachable for a
  non-developer to eventually edit by hand.
- A single entry point, **zero arguments**: running `dm-tool` with no
  flags launches a plain-CLI (non-Textual) launcher that discovers
  available adventures, guides the user through adventure selection and
  setup, then hands off into the Textual app. See "Launch flow" below.
- The **plain-CLI setup wizard** (no Textual) that handles pre-session
  player-character entry is distinct, simpler *code* from the main
  Textual app, even though the user experiences it as one continuous
  flow. It writes a session YAML file that the main app then loads.
  Keeping the implementation separate means the simple, rarely-touched
  setup flow can't be broken by changes to the more complex play UI, and
  vice versa.
- Fuzzy matching for spell-name entry: a lightweight library
  (`rapidfuzz` or similar) — normalize input, score against the
  candidate list, confirm the match with the user rather than silently
  accepting or rejecting.

## Launch flow

Running `dm-tool` with no arguments is the only thing a user ever needs to
type. Everything else is guided, numbered-choice interaction:

1. **Adventure picker** — scan `adventures/` for folders containing a
   valid `manifest.yaml` (skip/warn on malformed entries, e.g. an
   in-progress copy, rather than crashing). List each by title + short
   summary pulled from its manifest. Last option in the list is always
   **"Create new adventure..."** (see below).
2. **Session check** — if one or more existing session files are found
   for the chosen adventure, offer to resume the most recent one or
   start fresh:
   ```
   Found an existing session for Wild Sheep Chase (2026-08-20-party.yaml).
     1. Resume this session
     2. Start a new session
   ```
3. **Setup wizard** (only if starting fresh) — the plain-CLI PC/spell
   setup flow described under Core Features, run automatically as part
   of this same launch sequence, not a separately-invoked command.
4. **Adventure begins** — the Textual app launches directly into the
   chosen adventure with the chosen or newly-created session loaded.

### Creating a new adventure

Selecting "Create new adventure..." from the picker prompts for a title,
a slug (folder name, defaulted from the title), and a ruleset (defaulted
to `srd-5.1`), then copies `adventures/_template/` into a new
`adventures/<slug>/` folder, stamping the new manifest with the entered
title/slug/ruleset. This automates what would otherwise be a manual
copy-and-rename of the template — same starter content (one example
scene, one example NPC, one example monster, all heavily commented), just
without the chance of a forgotten rename or a stale placeholder reference.

No central adventure registry is created or maintained anywhere. The new
adventure folder simply exists on disk with a valid manifest, and the
picker finds it on next scan — consistent with "content is data": adding
an adventure is "a folder with a manifest exists," nothing more.

## Licensing note (must be respected in implementation)

Rules-reference content (conditions, core mechanics, monster/spell stat
blocks) is sourced from Wizards of the Coast's **SRD 5.1**, released
under **CC-BY-4.0**. Required attribution text (must appear in an
about/credits screen or README, verbatim):

> This work includes material taken from the System Reference Document
> 5.1 ("SRD 5.1") by Wizards of the Coast LLC and available at
> https://dnd.wizards.com/resources/systems-reference-document. The SRD
> 5.1 is licensed under the Creative Commons Attribution 4.0
> International License, available at
> https://creativecommons.org/licenses/by/4.0/legalcode.

Official source PDF: https://media.dndbeyond.com/compendium-images/srd/5.1/SRD_CC_v5.1.pdf

For human browsing (not bundled in this repo — link out, don't copy):
- D&D Beyond's SRD hub, covering both 5.1 and 5.2:
  https://www.dndbeyond.com/srd
- D&D Basic Rules (2014) — the free, readable rulebook covering
  character creation, gameplay, spellcasting, and DM tools, organized
  by chapter. Good "further reading" link for the friend or players
  learning the game itself, as distinct from the SRD's licensing-
  focused document:
  https://www.dndbeyond.com/sources/dnd/basic-rules-2014

`docs/` should **link to these sources rather than bundle the full SRD
PDF or a mirrored copy**. The project's own structured rules content
(`rules/srd-5.1/*.yaml`) is the extracted, engine-usable subset; the
official SRD/D&D Beyond links are for anyone who wants the complete
rulebook or wants to verify/expand what's in the YAML against the
canonical source.

Adventure content transcribed from a purchased/downloaded third-party
module (e.g., Wild Sheep Chase) is **not** redistributable SRD content —
treat it as the user's own transcription for personal table use, not
something to publish or bundle as open content.

---

## Architecture

### Directory layout

```
dm-tool/
  engine/                    # Python source — generic, content-agnostic
    launcher.py               # entry point: adventure picker, session
                               #  check, "create new adventure", then
                               #  hands off to setup_wizard.py and app.py
    app.py                    # Textual app, launched by launcher.py
    setup_wizard.py            # plain-CLI PC/session setup, invoked by
                               #  launcher.py when starting a fresh session
    models/                   # data classes for scenes, NPCs, monsters, etc.
    loaders/                  # YAML loading + validation
    matching.py                # fuzzy-match + confirmation logic (spells, etc.)
  rules/
    srd-5.1/
      conditions.yaml
      core-mechanics.yaml    # DC guideline table, save DC formulas, etc.
      bestiary.yaml          # shared/generic monsters
      spells.yaml
      ATTRIBUTION.md
    srd-5.2/
      # v1: seeded as a working copy of srd-5.1 content.
      # Real 5.2 transcription is a planned follow-up (see Phased Plan).
      NOTES.md                # dated note: "copied from 5.1 on <date>,
                               #  needs real SRD 5.2 transcription"
      conditions.yaml
      core-mechanics.yaml
      bestiary.yaml
      spells.yaml
      ATTRIBUTION.md
  adventures/
    wild-sheep-chase/
      manifest.yaml           # title, ruleset, level range, summary
      scenes/
        01-sheep-pen.yaml
        02-village.yaml
        ...
      npcs/
        grimjaw.yaml
        ...
      monsters/
        dire-wolf.yaml        # adventure-specific; can reference shared bestiary
        ...
      maps/
        village-dm.png
        village-player.png    # cleaned, player-safe version
      sessions/
        2026-08-20-party.yaml # output of the setup wizard; gitignored/local
    _template/
      # heavily commented starter files for a new adventure —
      # this is the self-service on-ramp for adding future one-shots
      manifest.yaml
      scenes/example-scene.yaml
      npcs/example-npc.yaml
      monsters/example-monster.yaml
  docs/
    schema-reference.md       # full field-by-field schema documentation
    adding-an-adventure.md    # step-by-step guide, written for a non-developer
    adding-a-ruleset.md       # how to fill in srd-5.2 for real, later
    transcribing-a-pdf-adventure.md  # tool-agnostic guide: PDF -> schema
  README.md
```

### Key schema concepts

- **Scene** — read-aloud text, NPCs/monsters present, DC/skill-check
  guidance references (generic, not per-scene branches — see below),
  `exits` (list of possible next scenes, each optionally gated by a
  `condition` referencing a flag), and freeform `improv_notes` (what
  this NPC/situation wants, how it reacts to pressure — guidance for
  off-script moments, not scripted outcomes).
- **Flags** — a small set of DM-settable session flags
  (`flag set goat_saved`) that conditional exits can reference. This is
  how the adventure's real branching structure (as authored in the
  source module) gets represented, without trying to predict arbitrary
  player actions.
- **NPCs / Monsters** — stat blocks, personality/motivation notes, and
  (if a caster) a **preselected** short list of known spells with a
  precomputed save DC and the DC formula (for on-screen display, not
  live calculation).
- **Player characters** — entered via the setup wizard per session, not
  part of adventure content. Same preselected-spell-list pattern as
  NPCs. The tool does **not** track HP, spell slots, or inventory for
  PCs — players own their own paper sheets. The tool only helps the DM
  with fast lookup (what does this spell do, what's the DC) and combat
  bookkeeping for anything the DM needs visibility into.
- **Rules reference** — conditions, DC guideline table (Very Easy 5 ...
  Nearly Impossible 30), and spell/monster data sourced from the SRD,
  scoped per ruleset. Always-visible DC reference panel during play.

### What the engine explicitly does NOT do

- Does not roll dice or calculate check/attack results — DM enters real
  dice outcomes; the tool displays relevant numbers/formulas only.
- Does not pre-script outcomes for arbitrary off-script player actions
  (no per-scene "if they try X, roll Y at DC Z" trees). Off-script
  moments are handled via the always-visible DC guideline table plus a
  generic improv technique tip — general-purpose, not adventure-authored.
- Does not track PC spell slots, concentration, or resource attrition.
- Does not use any LLM or generative AI component.
- Does not infer scene transitions or game state from anything other
  than explicit DM commands.

---

## Core Features (v1 scope)

### 1. Scene navigation
- Full-screen Textual layout: scene text panel, NPCs/monsters present,
  always-visible DC reference panel, command input.
- `goto` shows the current scene's valid (condition-filtered) exits as a
  numbered picker, plus an **"Other..."** option that opens a full,
  unfiltered list of every scene in the adventure — the fallback for
  when actual play diverges from the authored branches.
- Scene transitions only happen via explicit DM command — never
  inferred.

### 2. Combat & bookkeeping
- Initiative tracker: add combatants, enter/sort initiative, cycle
  turns.
- HP tracking: DM reports real damage/healing rolls, tool updates and
  displays current HP.
- Condition tracking: apply/remove SRD conditions to combatants; tool
  shows what the condition does (from the SRD reference data) at the
  moment it's applied.
- Death/unconsciousness handling for PCs per SRD rules, surfaced
  automatically rather than relying on DM memory.

### 3. Spell & NPC/monster reference
- Fast lookup for any NPC/monster's stat block.
- Casters (NPC or PC) have a **preselected, short known-spell list**
  set at authoring time (NPCs) or setup time (PCs) — shown as a
  numbered menu when their stat block is displayed, not free-text
  search, to eliminate typo/ambiguity friction during play.
- Spell display shows effect text, the save DC (precomputed) and its
  formula (`8 + proficiency + spellcasting mod`) for on-screen
  reference — the DM reads it, no live calculation performed by the
  tool.
- Fallback: full SRD spell list lookup via fuzzy match + confirmation,
  for the rare case of an unplanned spell.

### 4. DM guidance
- Persistent DC guideline reference panel (Very Easy 5 → Nearly
  Impossible 30), always visible during play.
- Generic, reusable technique tips (not per-scene) — e.g., guidance on
  handling off-script player actions, when/how to call for a check,
  encouraging descriptive failure over flat "no."
- Per-scene `improv_notes` (what an NPC/situation wants, how it
  reacts) — authored guidance, not scripted branches.

### 5. Pre-session setup wizard (separate plain-CLI code, invoked by the launcher)
- Automatically run by `launcher.py` when the user starts a fresh
  session for an adventure — not a separately-invoked command.
- Sequential prompts: character name, class, spellcasting save DC
  (with formula shown), known spells.
- Known-spell entry uses fuzzy match against the ruleset's spell list
  with an explicit confirmation step (`Did you mean: Burning Hands?
  [y/n]`) before saving — prevents typos from silently producing
  unresolvable data.
- Writes a session YAML file consumed by the main app at launch.

### 6. Player-friendly maps
- Separate deliverable, not part of the Textual app: cleaned versions
  of DM maps with room numbers, monster tokens, trap/secret-door
  markers, and DM-only notes removed, exported as PDF for printing or
  sharing at the table.

### 7. Launcher & adventure creation
- `dm-tool` with no arguments is the only command a user needs. See
  "Launch flow" above for the full picker → session-check → setup →
  play sequence.
- "Create new adventure..." in the picker prompts for title/slug/
  ruleset and copies `adventures/_template/` into a new, properly
  stamped adventure folder — no manual copy-and-rename required, no
  central registry to update.

---

## Phased Plan

### Phase 1 — Engine skeleton & launcher
- Project scaffolding per the directory layout above.
- YAML loaders + data models for scenes, NPCs, monsters, adventures,
  rules-reference files.
- `launcher.py`: adventure picker (folder scan of `adventures/`,
  validating each `manifest.yaml`), session check/resume, and "Create
  new adventure..." (template copy + manifest stamping).
- Basic Textual app shell: scene panel, DC reference panel, command
  input, scene navigation (`goto`, including conditional exits and
  "Other...").
- Flags system (`flag set/unset/list`).

### Phase 2 — Combat & reference
- Initiative tracker, HP/condition bookkeeping.
- NPC/monster/spell lookup, including the fuzzy-match + confirmation
  logic (shared code path for setup wizard and in-session fallback
  lookup).
- DM tips surfacing (generic technique tips + per-scene improv notes).

### Phase 3 — SRD 5.1 rules-reference data
- Transcribe real content from the SRD 5.1 PDF into
  `rules/srd-5.1/`: conditions, core mechanics (DC table, save DC
  formula reference), a small shared bestiary of generic monsters,
  and a spell reference.
- This is real content work, not placeholder — required for v1 to be
  correct, since Wild Sheep Chase depends on it.

### Phase 4 — SRD 5.2 placeholder
- Seed `rules/srd-5.2/` as a direct copy of the Phase 3 content, same
  schema shape, with a dated `NOTES.md` flagging it as provisional.
- Purpose: prove the ruleset-selection code path is real (adventures
  declare a ruleset in their manifest; the engine loads the
  corresponding folder) without blocking v1 on a second full
  transcription. Real SRD 5.2 content is planned as a near-term
  follow-up, not urgent for the initial session.

### Phase 5 — Wild Sheep Chase content
- Transcribe the adventure into the schema: scenes (including
  conditional exits per the module's actual branching), NPCs,
  monsters, spells if any, improv notes.
- Flag `ruleset: srd-5.1` in the manifest.
- **Level decision: run at 1st level, rebalanced down from the
  module's as-written 4th-5th level.** This follows a documented,
  field-tested approach for running this specific module with new
  players (see "Newbie adaptations" below) rather than running it as
  written. Combat encounters need to be rebalanced for 1st-level
  characters during transcription — this is a real content-authoring
  step, not just a manifest label change, since monster/encounter
  stat blocks in the source PDF assume the higher level range.
- **Newbie adaptations to incorporate while transcribing** (source:
  a published "how to run this module for beginners" writeup, used as
  reference alongside the actual PDF — not a substitute for reading
  the source material directly):
  - Lower default DCs: most checks at DC 10, harder ones at DC 12,
    with the climactic Arcana check (recovering the wand) staying at
    DC 15. Encode as authored per-scene DCs, not the generic DC table.
  - An `improv_notes` beat early in scene 1 for the party to pick a
    team name together, with a fallback of an NPC assigning one if
    they can't decide.
  - An `improv_notes` beat noting that new players tend to play
    cautiously/defensively in combat (e.g., searching rather than
    fighting) — consider offering an investigation check that turns
    up a healing potion in early encounters, to offset the extra
    relative risk this caution creates rather than punishing it.
  - Consider granting DM/Inspiration early to encourage creative play
    and improve players' odds on the final Arcana check.
  - The three core NPCs (the sheep, his loyal henchman, and the rival
    archanist) each have a clear goal, attitude toward the party, and
    combat behavior worth capturing fully in their `npcs/*.yaml`
    entries — this level of NPC clarity is exactly what makes
    `improv_notes` useful at the table.

### Phase 6 — Player maps
- Extract/clean map assets from the source PDF into player-safe
  versions, export as PDF.

### Phase 6a — Pregenerated characters (prep task, not a tool feature)
- Character creation is explicitly **out of scope for the tool itself**
  — players use paper sheets, and the tool never builds or tracks a
  character from scratch (consistent with the setup wizard only
  recording an existing character's name/class/spells, not generating
  one).
- This is a one-time prep task for the session: source or build 3-4
  simple, ready-to-play **1st-level** pregenerated character sheets
  appropriate for new players (WotC publishes free pregens at various
  levels; the Basic Rules classes are also usable as a reference for
  building simple ones by hand). Not a coding task — a checklist item
  to complete before the session, worth a short note in
  `adding-an-adventure.md` for future adventures at other level ranges.

### Phase 7 — Setup wizard
- Plain-CLI flow, invoked automatically by `launcher.py` when starting
  a fresh session: PC entry, fuzzy-matched spell selection with
  confirmation, session YAML output.

### Phase 8 — Docs & handoff polish
- `docs/schema-reference.md` — field-by-field schema documentation.
- `docs/adding-an-adventure.md` — step-by-step, written for a
  non-developer, using the `_template/` folder as the worked example.
- `docs/adding-a-ruleset.md` — how to properly fill in `srd-5.2/`
  later.
- `docs/transcribing-a-pdf-adventure.md` — plain-language (tool-
  agnostic, not Claude-specific) walkthrough for converting a new
  one-shot PDF into the schema: how to read the source (including
  fallback to page-by-page visual reading if text extraction comes
  out garbled), how to identify scenes/read-aloud text/stat blocks/
  exits, how to represent the module's branching as exits + flags,
  and a review checklist.
- README covering install/run instructions, the SRD attribution
  notice, and links to the official rules sources (D&D Beyond's SRD
  hub and the free Basic Rules) for anyone wanting the full rulebook —
  not a bundled copy.

### Later / explicitly deferred (do not build unless separately requested)
- Real SRD 5.2 transcription (planned within a few weeks post-launch,
  per Phase 4 note).
- Any LLM-based improv assistance — deliberately rejected for v1; would
  need a fresh cost/benefit discussion if ever revisited.
- Any web/GUI interface — deliberately rejected in favor of terminal
  given the target users are terminal-fluent.
- Per-scene scripted skill-check branches — deliberately rejected in
  favor of the generic DC-table approach.
- Multi-adventure shared bestiary beyond what Phase 3 needs — expand
  only once a second real adventure exists and shows what actually
  repeats.
- In-tool character creation — deliberately out of scope; players use
  paper pregens (a prep task, see Phase 6a), and the setup wizard only
  ever records an existing character, never builds one.

---

## Definition of done for v1

- Running `dm-tool` with **no arguments** presents the adventure picker,
  lets the developer select Wild Sheep Chase, run setup (or resume a
  prior session), and land directly in the full one-shot: navigate
  scenes, run combat, look up NPCs/monsters/spells, see DC guidance
  throughout.
- "Create new adventure..." from the picker produces a correctly
  stamped, valid new adventure folder from the template, with no
  manual file editing required beyond filling in actual content.
- Setup wizard (auto-invoked by the launcher) produces a valid session
  file from a clean run.
- Player-friendly map PDFs exist for any maps in the module.
- `docs/adding-an-adventure.md` is good enough that a non-developer
  could plausibly follow it unassisted.
- SRD attribution is present and correct.
- No engine code references anything Wild-Sheep-Chase-specific — a
  second, equally well-formed adventure folder (whether hand-authored
  or created via "Create new adventure...") should just appear in the
  picker and run identically.
