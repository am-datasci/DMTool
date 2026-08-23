# Transcribing a PDF Adventure into the Schema

This guide walks through converting a published one-shot PDF into this
tool's adventure schema (see `docs/schema-reference.md` for the exact
field-by-field shape). It's written to be usable by a person working
alone with the PDF open in one window and a text editor in the other —
no AI tool required, though the same steps work fine if you're using
one to help.

This is a judgment-heavy task, not a mechanical one. Two people
transcribing the same module will make slightly different calls about
where a scene boundary falls or how much detail an NPC entry needs —
that's fine. The goal is a faithful, usable representation of the
adventure, not a perfect one.

## Before you start

- Read the whole adventure once, start to finish, before transcribing
  anything. You need the overall shape of the story in your head before
  you can decide where scene boundaries and branches actually are.
- Decide your target ruleset (`srd-5.1` or `srd-5.2`) and, if the module
  is written for a different level range than you intend to run, decide
  your level approach now (see "Adjusting for your table" below) —
  this affects how you transcribe stat blocks and DCs, so it's better
  decided before transcription starts than midway through.
- If you're aware of other DMs' writeups of the same module (session
  reports, "how I ran this" blog posts), skim them first. They're not a
  substitute for the source material, but they're a useful sanity check
  and can surface pacing/NPC ideas you'd otherwise have to invent from
  scratch. Keep any such reference material in the adventure's own
  folder (e.g. `adventures/<slug>/reference/`) so it's easy to find
  again if a later scene doesn't quite make sense on review.

## Step 1: Get readable text out of the PDF

Try text extraction first. If the PDF has clean, selectable text, most
tools (including a browser's own text layer, `pdftotext`, or an AI
tool's document reading) will get you usable output quickly.

**Watch for garbled extraction.** Some PDFs — especially older or
oddly-fonted ones — extract as scrambled or nonsensical text even
though they look fine visually. If your extracted text doesn't read as
real sentences, don't try to fix it programmatically. Fall back to
**reading the PDF visually, page by page**, either on-screen or via
page-image rasterization if you're using a tool that supports it. This
is slower but far more reliable when extraction fails.

Either way, sanity-check a few pages of your extracted/read text against
the visual PDF before committing to using it for the rest of the
document — catching an extraction problem on page 2 is much cheaper
than discovering it on page 20.

## Step 2: Identify the pieces

Published one-shots vary in layout, but most contain the same
ingredients. As you read through, start marking (on paper, in a
scratch doc, however works for you) where each of these appears:

- **Scenes / encounters** — usually visually distinct sections, often
  with their own heading. A scene is a distinct location or situation
  the party moves through — not necessarily one per page, and not
  necessarily one per combat encounter (a scene can contain no combat
  at all, or more than one).
- **Read-aloud / boxed text** — usually visually set apart (a shaded
  box, italics, or an indented block) and written in second person
  ("You see...", "As you approach..."). This is text meant to be read
  or paraphrased to players verbatim when they enter a scene.
- **NPC descriptions** — personality, motivation, appearance, and how
  they behave in combat if relevant. Sometimes woven into scene text
  rather than given their own section — watch for this, since it means
  the NPC's actual personality-relevant details may be scattered across
  more than one page.
- **Stat blocks** — for NPCs and monsters, usually a boxed or
  clearly-formatted block with AC, HP, attacks, etc. If the module uses
  a standard monster with only minor reskinning, note that — the
  schema supports referencing a shared bestiary entry rather than
  duplicating a full generic stat block per adventure.
- **DCs and skill checks** — often embedded directly in scene text
  ("a DC 12 Perception check reveals...") rather than pulled out
  separately. Note these as you encounter them; don't wait to
  hunt for them later.
- **Treasure / rewards** — items, gold, or other rewards tied to
  specific scenes or outcomes.
- **Maps** — note which scenes have an associated map image and where
  it appears in the PDF, for the separate player-map-cleaning pass
  (this is a distinct task from schema transcription — see the
  project brief's Phase 6).

## Step 3: Represent the adventure's real branching

This is the part most likely to be done sloppily under time pressure,
so it's worth being deliberate about.

Most one-shots aren't perfectly linear — a choice earlier in the
adventure changes what's available or how an NPC reacts later. Capture
this using the schema's `exits` + flags mechanism, **not** by inventing
new branches the module doesn't actually contain:

- If the module says something like "if the party saved the goat, they
  arrive at the village to a warm welcome; otherwise, the villagers are
  suspicious," that's a flag (`goat_saved`) and two conditional exits
  pointing at two different next-scenes.
- If the module doesn't call out an explicit branch — most player
  choices during actual play won't be — don't manufacture one. Off-
  script moments are handled at the table via the DM's judgment and the
  tool's generic DC-guidance panel, not by scenes you write speculative
  branches for. See the project brief's design-philosophy section for
  why this is a deliberate choice, not an oversight.
- Every scene needs at least one exit, even if it just points to
  "the next scene in sequence" for a mostly-linear stretch of the
  adventure. The `_template/` adventure folder shows the minimal shape
  this takes.

## Step 4: Write it into the schema

Work scene by scene, in story order, cross-referencing
`docs/schema-reference.md` for the exact fields each file type expects.
A few practical notes:

- **Don't over-summarize read-aloud text.** If the module gives you a
  full paragraph of boxed text, transcribe it close to verbatim — this
  is text meant to be read aloud, not a summary for the DM's own use.
- **Do summarize DM-facing background/context text** in your own words
  where it's long — the schema's `improv_notes` and similar fields are
  for the DM's understanding, not something read to players, so
  concision helps more than completeness here.
- **NPC entries should capture attitude and goals, not just stats.**
  The whole point of `improv_notes` and NPC personality fields is to
  give the DM something to improvise from when players go off-script —
  a stat block alone doesn't help with that. If a source module (or a
  reference writeup you're using alongside it) gives you a clear "this
  NPC wants X and reacts to Y by doing Z," capture that fully.
- **Sanity-check stat blocks and DCs against the SRD reference data**
  you're building in parallel (see the project brief's Phase 3/4) —
  especially if you're adjusting the adventure's level range from what
  it was written for, since monster/DC numbers will need deliberate
  rebalancing, not just literal transcription.

## Adjusting for your table (optional, but common)

Published one-shots are often written for a specific level range that
may not match your actual group. If you're deliberately running the
adventure at a different level than written (as this project's own
Wild Sheep Chase transcription does — see the brief's Phase 5 notes),
this affects transcription directly:

- Combat encounters (monster stat blocks, numbers of enemies) need real
  rebalancing for the target level, not just a label change. This is
  content-authoring work, not a mechanical adjustment — use your
  judgment, existing published guidance for the adventure if available,
  and the SRD's monster/CR guidance as a sanity check.
- DCs may be worth lowering for a newer or lower-level group — decide a
  consistent policy (e.g., "most checks at DC 10, hard checks at DC
  12–15") and apply it uniformly rather than leaving the module's
  original, higher-level DCs in place inconsistently.
- Note the adjustment plainly in the adventure's `manifest.yaml`
  summary, so it's clear to anyone reading the transcribed content
  later that numbers were deliberately changed from the source, not
  transcribed incorrectly.

## Step 5: Review checklist

Before considering a transcription done, check:

- [ ] Every scene in the source PDF has a corresponding entry — nothing
      silently dropped
- [ ] Every scene has at least one valid `exits` entry pointing to a
      real scene (or is clearly marked as an ending)
- [ ] Conditional exits reference flags that are actually set
      somewhere earlier in the adventure — no dangling conditions
- [ ] Every NPC referenced in a scene has a corresponding `npcs/*.yaml`
      file
- [ ] Every monster referenced has either its own entry or a valid
      reference to a shared bestiary entry
- [ ] Stat blocks and DCs have been sanity-checked against the SRD
      reference data, especially anywhere the level range was adjusted
- [ ] Read-aloud text is transcribed close to verbatim; DM-facing notes
      are summarized in your own words
- [ ] The manifest's summary accurately reflects the adventure,
      including the ruleset and any deliberate level/DC adjustments
- [ ] Map images are accounted for and noted for the separate
      player-map-cleaning pass

## A note on copyright

The adventure content itself (text, stat blocks, plot) belongs to its
original publisher. Transcribing it into this schema for your own
table's use is the same kind of personal-use adaptation as printing out
a page of the PDF to scribble notes on — it is not something to
publish, redistribute, or bundle as open content. This is distinct from
the SRD rules-reference data elsewhere in this project, which carries
its own explicit CC-BY-4.0 permissions (see the project brief's
licensing section).
