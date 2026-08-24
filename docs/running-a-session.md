# Running a session

A walkthrough of using dm-tool at the table, for a DM who has not used it
before. If you want to *add* an adventure rather than run one, see
`adding-an-adventure.md`.

## What this tool is

A reference and bookkeeping assistant. It keeps the scene text, the stat
blocks, the conditions and the initiative order on screen so you are not
flipping through a PDF while five people wait.

It is deliberately not an automation engine:

- **It never rolls dice.** You roll real dice at the table and tell the
  tool what happened. It shows you DCs, formulas and modifiers.
- **It never decides anything.** Scenes change when you say so. Flags are
  set when you say so. It will not infer that a fight has started or that
  the party has moved on.
- **It does not track player characters' hit points**, spell slots or
  equipment. The paper sheet is authoritative. It *does* track monster hit
  points, because nobody else is holding those.

If it seems to be waiting for you to tell it something, that is the
design.

## Before the session

Install once:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
```

Have ready:

- Printed pregenerated characters, one per player. The tool records
  characters; it does not create them.
- Real dice.
- The adventure's own notes, if you want to read ahead. `A Wild Sheep
  Chase` is written for 4th-5th level and has been rebalanced here for
  1st — the reasoning is in each monster file if you want to check it.

## Starting

```bash
.venv/bin/dm-tool
```

No arguments, ever. It walks you through the rest:

1. **Pick an adventure.** Anything with a valid manifest in `adventures/`
   shows up here, plus an option to create a new one from the template.
2. **Resume or start fresh.** If you have played before, it offers the
   most recent session.
3. **Record the party.** On a fresh session it asks for each character's
   name, player, class and level, and for casters their spell save DC and
   known spells. Spell names are fuzzy-matched — type `curewounds` or
   `fire bo` and it will work out what you meant, asking first if it had
   to guess.
4. **Play.** The main screen opens on the adventure's first scene.

## The screen

- **Left, large.** The current scene: what to read aloud, your own notes,
  any checks the adventure calls for, guidance for when players go
  off-script, and where they can go next.
- **Right, top.** Who is present in this scene — or, once a fight starts,
  the initiative order with hit points and conditions.
- **Right, bottom.** The DC guideline table. Always there, because
  improvised checks are the thing you will need most often and the thing
  hardest to remember.
- **Bottom.** A command line, and a panel above it where answers appear.

Type `help` at any point. It is organised by topic, and `help <command>`
explains any single one with examples.

## Running a scene

Read the read-aloud text. Use the DM notes. When the party decides where
to go:

```
goto
```

That lists this scene's exits as a numbered menu — type the number. Exits
gated behind story flags only appear once the flag is set, so the menu
shows what is actually available right now.

If play goes somewhere the adventure did not anticipate, the last option
is always **Other...**, which offers every scene in the adventure. Use it
without guilt; that is what it is for.

### Flags

Flags are how the adventure branches:

```
flag set sheep_taken
flag list
flag unset sheep_taken
```

Each adventure documents its own flags in its scene files. Setting one
may open a new exit; nothing else changes them.

### When they do something unexpected

This is normal and not a failure of prep. The DC table on the right is
the main tool: most improvised checks are DC 10 if a competent person
manages it most times, DC 15 if it is genuinely hard. `tips` has general
technique advice, and each scene has its own improvisation notes in the
main panel.

## Running a fight

```
combat start
add Thora 18
add Guz 14
```

`add` with a name the adventure knows brings that creature's stat block
and hit points automatically. Any other name is treated as a player
character, tracked in the initiative order but with no hit points — the
sheet holds those.

Then:

```
next                  advance the turn
hp Guz -7             damage you have already rolled
cond add Guz prone    apply a condition, and see what it does
look Guz              full stat block
```

Applying a condition prints its rules immediately, so you do not have to
remember what *restrained* means mid-fight.

### When someone goes down

```
down Thora
```

The tool prints the death saving throw rules and starts counting. Report
each roll as you make it:

```
save Thora ok
save Thora fail
save Thora nat20
```

Three successes stabilises, three failures kills, a natural 1 counts
double and a natural 20 puts them back up. It will remind you at the
start of their turn that a save is owed — that is the thing new DMs
forget most.

## Looking things up

```
look Guz              a stat block, including what he wants and how he fights
spell Fire Bolt       any of the 319 SRD spells
spell                 what the casters in this scene know
conditions            all 15 SRD conditions
dying                 the rules at 0 hit points
tips                  general DM technique
```

Misspellings are offered as suggestions rather than guessed at.

## Finishing and resuming

```
quit
```

Or Ctrl+Q. The session saves automatically as you go — scene, flags and
the combat tracker — so a crash or a closed laptop loses nothing. Next
time you run `dm-tool`, it offers to resume.

Session files live in `adventures/<adventure>/sessions/` and are plain
YAML. They are not in version control. If you need to add a player who
turned up in week two, edit that file directly.

## Command reference

Generated from the command registry in `engine/app.py`.

### Getting around

| Command | What it does |
| --- | --- |
| `goto [scene]` | Move the party to another scene. |
| `scenes` | List every scene, and jump to one by number. |
| `scene` | Redraw the current scene and clear the panel below. |
| `flag set\|unset\|list <name>` | Set or clear a story flag. |

### Combat

| Command | What it does |
| --- | --- |
| `combat start\|end` | Begin or clear the encounter. |
| `add <name> [initiative]` | Put someone in the initiative order. |
| `init <name> <number>` | Set or correct someone's initiative. |
| `next` | Advance to the next turn, rolling the round over. |
| `back` | Step the turn marker backwards, for when a turn was missed. |
| `hp <name> <change>` | Apply damage or healing you have already rolled. |
| `down <name>` | Mark a character as at 0 hit points. |
| `save <name> ok\|fail\|nat20\|nat1` | Record a death saving throw you have rolled. |
| `stable <name>` | Mark someone stabilised, e.g. by a Medicine check. |
| `up <name> [hp]` | Put someone back on their feet, clearing death saves. |

### Reference

| Command | What it does |
| --- | --- |
| `cond add\|remove <name> <condition>` | Apply or clear a condition, and show what it does. |
| `conditions` | List all 15 SRD conditions, and read any of them. |
| `look [name]` | Show an NPC or monster's stat block. |
| `spell [name]` | Look up a spell, or list what casters here know. |
| `dying` | What happens at 0 hit points, per the SRD. |
| `tips` | General DM technique — improvising, DCs, pacing. |

### Session

| Command | What it does |
| --- | --- |
| `help [command]` | This menu, or detail on one command. |
| `quit` | Save and exit. Ctrl+Q does the same. |

## If something looks wrong

- **A command is refused.** Check `help <command>` for the exact form.
  Mistyped commands suggest the nearest match.
- **An exit you expected is missing.** It is probably gated behind a flag.
  `flag list` shows what is set; `goto` then `Other...` gets you anywhere
  regardless.
- **Warnings on startup.** The launcher reports content problems in the
  adventure — a scene referring to an NPC file that does not exist, for
  example. Play continues; the warning tells you which file to fix.
- **The tracker is cut off.** The panels scroll. A terminal of at least
  100x30 fits a full party comfortably.
