"""Pre-session setup: record the party for a fresh session.

Run automatically by the launcher when someone starts a new session, so
the user experiences one continuous flow. Kept as separate, simpler code
from the Textual app on purpose — this path runs once per session and
should not be breakable by changes to the play UI.

It records a character; it never builds one. Players bring paper pregens,
and the sheet stays authoritative: no ability scores, no hit points, no
spell slots, no equipment. The spell save DC is asked for, not computed —
the formula is printed above the prompt so whoever is typing can check it
against the sheet.
"""

from __future__ import annotations

from engine import matching
from engine.loaders.session import new_session, save_session
from engine.models.adventure import Manifest
from engine.models.rules import Ruleset
from engine.models.session import Session
from engine.prompts import (
    ask_int,
    ask_optional_text,
    ask_text,
    ask_yes_no,
    choose,
    prompt,
)

KEEP_AS_TYPED = "Keep it exactly as I typed it"
CANCEL_SPELL = "Forget this one"


def _ask_spell(ruleset: Ruleset) -> str | None:
    """Ask for one spell name and resolve it against the ruleset.

    Never silently accepts a near miss and never silently rejects one —
    the same rule the in-session lookup follows.
    """
    typed = prompt("    Spell (blank when done): ")
    if not typed:
        return None

    names = [entry.get("name", key) for key, entry in ruleset.spells.items()]
    if not names:
        # No spell data for this ruleset — record what they typed.
        return typed

    match = matching.find(typed, names)

    if match.exact:
        # An exact typing needs no confirmation; an expansion of a partial
        # name does, because the tool chose something they did not type.
        # Spacing is not a typo — "curewounds" is the same answer as
        # "Cure Wounds", and matching.find already treats it as exact, so
        # the wizard agrees rather than asking a redundant question.
        def squash(text: str) -> str:
            return matching.normalize(text).replace(" ", "")

        if squash(typed) == squash(match.exact):
            print(f"      {match.exact}")
            return match.exact
        if ask_yes_no(f"      Did you mean {match.exact}?", default=True):
            return match.exact
        return _ask_spell(ruleset)

    if match.has_suggestions:
        options = match.suggestions + [KEEP_AS_TYPED, CANCEL_SPELL]
        index = choose(f'      No exact match for "{typed}". Did you mean:', options)
        if options[index] == CANCEL_SPELL:
            return _ask_spell(ruleset)
        if options[index] == KEEP_AS_TYPED:
            return typed
        return options[index]

    print(f'      Nothing in {ruleset.id} matches "{typed}".')
    if ask_yes_no("      Record it anyway?", default=True):
        return typed
    return _ask_spell(ruleset)


def _ask_spellcasting(ruleset: Ruleset) -> dict | None:
    if not ask_yes_no("  Does this character cast spells?", default=False):
        return None

    ability = ask_text("  Spellcasting ability", default="Intelligence")

    formula = ruleset.save_dc_formula or "8 + proficiency bonus + ability modifier"
    print(f"\n  Spell save DC is {formula}.")
    print("  It is on the character sheet — the tool does not work it out.")
    save_dc = ask_int("  Spell save DC", minimum=1, maximum=30)

    print("\n  Known spells, one at a time. Press enter on a blank line to finish.")
    known: list[str] = []
    while True:
        spell = _ask_spell(ruleset)
        if spell is None:
            break
        if spell in known:
            print(f"      {spell} is already on the list.")
            continue
        known.append(spell)

    return {
        "ability": ability,
        "save_dc": save_dc,
        "save_dc_formula": formula,
        "known": known,
    }


def _ask_character(ruleset: Ruleset, *, number: int, default_level: int) -> dict:
    print(f"\n--- Character {number} ---")
    character = {
        "name": ask_text("  Character name"),
        "player": ask_optional_text("  Player's name"),
        "character_class": ask_text("  Class"),
        "level": ask_int("  Level", default=default_level, minimum=1, maximum=20),
    }
    spellcasting = _ask_spellcasting(ruleset)
    if spellcasting is not None:
        character["spellcasting"] = spellcasting
    return character


def _describe(character: dict) -> str:
    bits = [character["name"]]
    who = character.get("player")
    if who:
        bits.append(f"({who})")
    bits.append(f"— level {character['level']} {character['character_class']}")
    casting = character.get("spellcasting")
    if casting:
        spells = ", ".join(casting["known"]) if casting["known"] else "no spells listed"
        bits.append(f", save DC {casting['save_dc']}: {spells}")
    return " ".join(bits)


def _review(characters: list[dict], ruleset: Ruleset, default_level: int) -> list[dict]:
    """Show the party and let anything be corrected before it is written."""
    while True:
        print("\nThe party:")
        for index, character in enumerate(characters, start=1):
            print(f"  {index}. {_describe(character)}")

        options = ["That's everyone — start the adventure", "Add another character"]
        if characters:
            options.append("Re-enter one of them")
        index = choose("Anything to change?", options)

        if index == 0:
            return characters
        if index == 1:
            characters.append(
                _ask_character(
                    ruleset, number=len(characters) + 1, default_level=default_level
                )
            )
            continue
        which = choose(
            "Which one?", [_describe(character) for character in characters]
        )
        characters[which] = _ask_character(
            ruleset, number=which + 1, default_level=default_level
        )


def run(manifest: Manifest, ruleset: Ruleset) -> Session:
    """Collect the party, then create and save the session."""
    print("\n" + "=" * 70)
    print(f"Setting up a new session of {manifest.title}")
    if manifest.level_range:
        print(f"Written for: {manifest.level_range}")
    print("=" * 70)
    print(
        "\nRecord each player character as it appears on their sheet. The tool\n"
        "keeps track of names, classes and spells so you can look them up mid-\n"
        "game — hit points, slots and equipment stay on paper."
    )

    count = ask_int("\nHow many player characters?", default=4, minimum=0, maximum=10)
    characters = [
        _ask_character(ruleset, number=n + 1, default_level=1) for n in range(count)
    ]
    characters = _review(characters, ruleset, default_level=1)

    session = new_session(manifest)
    session.characters = characters
    save_session(session)
    print(f"\nSaved to {session.path}")
    return session
