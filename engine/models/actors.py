"""NPCs and monsters.

Stat blocks are held as authored — the engine displays them, it never
computes with them. Spell save DCs are precomputed at authoring time and
stored alongside their formula so the DM can see both.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Trait:
    """A named block of stat-block text: a trait, action, or reaction."""

    name: str
    text: str


@dataclass
class StatBlock:
    ac: int | None = None
    #: What the AC comes from, e.g. "natural armor", "leather armor, shield".
    ac_note: str | None = None
    hp: int | None = None
    hit_dice: str | None = None
    speed: str | None = None
    abilities: dict[str, int] = field(default_factory=dict)
    saves: dict[str, int] = field(default_factory=dict)
    skills: dict[str, int] = field(default_factory=dict)
    senses: str | None = None
    languages: str | None = None
    cr: str | None = None
    xp: int | None = None
    #: Damage resistances/immunities/vulnerabilities and condition
    #: immunities, kept as authored label -> text.
    notes: dict[str, str] = field(default_factory=dict)
    traits: list[Trait] = field(default_factory=list)
    actions: list[Trait] = field(default_factory=list)
    reactions: list[Trait] = field(default_factory=list)
    legendary_actions: list[Trait] = field(default_factory=list)


@dataclass
class Spellcasting:
    """A preselected short spell list, not a full spellbook.

    `save_dc` is authored, not derived; `save_dc_formula` is displayed
    next to it so the DM can see where the number came from.
    """

    ability: str | None = None
    save_dc: int | None = None
    save_dc_formula: str | None = None
    attack_bonus: int | None = None
    known: list[str] = field(default_factory=list)


@dataclass
class NPC:
    id: str
    name: str
    summary: str | None = None
    motivation: str | None = None
    attitude: str | None = None
    combat_behavior: str | None = None
    improv_notes: str | None = None
    stat_block: StatBlock | None = None
    spellcasting: Spellcasting | None = None
    source_path: Path | None = None


@dataclass
class Monster:
    id: str
    name: str
    #: The size/type/alignment line, e.g. "Small humanoid (goblinoid),
    #: neutral evil".
    meta: str | None = None
    summary: str | None = None
    combat_behavior: str | None = None
    stat_block: StatBlock | None = None
    spellcasting: Spellcasting | None = None
    source_path: Path | None = None
