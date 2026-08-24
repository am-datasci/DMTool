# Phase 7 plan — the pre-session setup wizard

Status: not started. Written 2026-08-23, after phases 1–5 landed.

## What it is

A plain-CLI flow that records the player characters for a fresh session
and writes them into the session YAML. The launcher runs it automatically
when someone starts a new session — the user experiences one continuous
flow, but it is separate, simpler code from the Textual app so that the
rarely-touched setup path cannot be broken by changes to the play UI.

## What it is emphatically not

It never *builds* a character. Players bring paper pregens; the wizard
only writes down what is already on the sheet. No ability score
generation, no class features, no equipment, no levelling. If a future
change starts to look like character creation, it is out of scope (design
rule 8).

It also does not compute the spell save DC. It shows the formula and asks
for the number, exactly as the tool shows DCs and formulas everywhere else
and lets a human supply the value.

## The integration seam (already clean)

`launcher.choose_session()` is the only place a fresh session is created,
and it calls `new_session(manifest)` in two branches
(`engine/launcher.py:179` and `:191`). Phase 7 replaces those calls with
the wizard, which builds the character list and then calls `new_session`
itself. Nothing else in the launcher changes.

`Session.characters` already exists as `list[dict]`
(`engine/models/session.py:20`), is already serialised, and is already
read back by `load_session`. It has been empty since phase 1. No schema
change is needed to start filling it.

## Proposed character record

```yaml
characters:
  - name: Thora Blackfell
    player: Alan            # optional, blank is fine
    character_class: Cleric
    level: 1
    spellcasting:
      ability: Wisdom
      save_dc: 13
      save_dc_formula: 8 + proficiency bonus (2) + Wisdom modifier (3)
      known:
        - Cure Wounds
        - Guiding Bolt
        - Sacred Flame
```

Non-casters simply have no `spellcasting` block. Deliberately absent: hit
points, armour class, spell slots, inventory. The paper sheet is
authoritative for all of it.

## Flow

1. **How many characters?** Then loop that many times. Offer to add
   another at the end, so a late arrival does not mean restarting.
2. **Name**, then **player name** (optional), then **class** (free text —
   see open question 1), then **level**, defaulting to the manifest's
   level range.
3. **Is this character a spellcaster?** If no, done.
4. **Spellcasting ability**, then **save DC**, with the formula printed
   above the prompt so whoever is typing can check it against the sheet.
5. **Known spells**, entered one per line until an empty line. Each goes
   through `matching.find` against the ruleset's 319 spells:
   - exact or unique-prefix match → confirm and accept
   - near misses → numbered menu, plus "none of these, keep as typed"
   - nothing → offer to keep the raw text (homebrew, or a spell outside
     the SRD) rather than refusing it
6. **Review** the whole party as a numbered list, with an option to fix
   any entry before writing.
7. Write the session and hand off to the Textual app.

`matching.find` was written in phase 2 for exactly this and is currently
used only by the in-session lookup; the confirmation rule is the same in
both places — never silently accept a near miss, never silently reject
one.

## Reusing the launcher's prompt helpers

`launcher.choose()`, `ask_text()` and `_prompt()` already handle numbered
menus, defaults, and Ctrl-C/EOF. Move them into a small shared module
(`engine/prompts.py`) rather than importing the launcher from the wizard
or duplicating them — a circular import between the two is otherwise
likely, since the launcher has to call the wizard.

## Open questions

1. **Class entry: free text, or a fixed list?** There is no class data in
   `rules/`, and hardcoding the SRD class names into `engine/` would put
   content in code (design rule 1). Free text is the simplest thing that
   respects that, at the cost of no validation and no typo protection.
   The alternative is a `rules/<ruleset>/classes.yaml` listing names only,
   which would also give the wizard something to fuzzy-match against.
   *Recommendation: free text now; add the data file only if it proves
   annoying in practice.*

2. **Should the spell list be filtered by class?** We have all 319 spells
   but no class→spell mapping — the SRD's class spell lists exist in both
   community conversions and were not transcribed. Matching against all
   319 is simpler and never wrongly rejects a valid spell; filtering would
   catch a player who names a spell their class cannot cast, which is
   arguably their sheet's problem, not the tool's.
   *Recommendation: match against all 319.*

3. **Editing a session after setup.** The review step covers typos during
   setup, but not "we added a player in week two". Simplest answer is that
   the session YAML is hand-editable and documented as such in phase 8.
   *Recommendation: no in-app editing; document the file.*

## Tests

- Wizard drives to completion from scripted stdin and produces a valid
  session that `load_session` reads back.
- A non-caster gets no `spellcasting` block.
- An exact spell name is accepted without a prompt; a typo produces a
  confirmation menu and is only recorded once confirmed; an unmatched name
  can be kept as typed.
- The review step can correct an entry before writing.
- The launcher's resume path is untouched — no wizard on resume.
- Ctrl-C partway through leaves no half-written session file.

## Definition of done

Running `dm-tool`, picking Wild Sheep Chase, and choosing a new session
walks through PC entry and lands in the play UI with those characters in
`session.characters`, without the user having typed a second command.
