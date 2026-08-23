"""Rules reference, scoped per ruleset.

Content here is SRD-derived and carries its own CC-BY-4.0 attribution
(see each ruleset folder's ATTRIBUTION.md).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from engine.models.actors import Monster


@dataclass(frozen=True)
class DCTier:
    """One row of the difficulty-class guideline table."""

    label: str
    dc: int


@dataclass(frozen=True)
class Condition:
    id: str
    name: str
    effects: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DyingRules:
    """What happens at 0 hit points, as reference text.

    The tool counts the successes and failures the DM reports; it never
    rolls a death saving throw.
    """

    death_save_dc: int
    successes_to_stabilize: int
    failures_to_die: int
    stabilize_check: str | None = None
    notes: list[str] = field(default_factory=list)


@dataclass
class Ruleset:
    id: str
    dc_tiers: list[DCTier] = field(default_factory=list)
    save_dc_formula: str | None = None
    dying: DyingRules | None = None
    conditions: dict[str, Condition] = field(default_factory=dict)
    spells: dict[str, dict] = field(default_factory=dict)
    bestiary: dict[str, Monster] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
