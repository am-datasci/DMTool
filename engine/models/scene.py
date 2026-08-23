"""Scenes: what the DM reads, who is present, and where play can go next."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Exit:
    """A route from one scene to another, optionally gated on a flag.

    Gating is deliberately limited to "this flag is set" (`condition`)
    and "this flag is not set" (`unless`), AND-ed when both are given.
    There is no boolean expression language — see the project brief.
    """

    to: str
    label: str
    condition: str | None = None
    unless: str | None = None

    def is_available(self, flags: set[str]) -> bool:
        if self.condition is not None and self.condition not in flags:
            return False
        if self.unless is not None and self.unless in flags:
            return False
        return True


@dataclass(frozen=True)
class Check:
    """A named check the source module calls for, with its DC.

    This is a flat reference list, not a decision tree: the tool shows
    the DC and the DM decides what a success or failure means. Anything
    resembling "if they try X, roll Y, then Z happens" belongs in
    `improv_notes` as guidance, not here as data.
    """

    name: str
    ability: str
    dc: int
    notes: str | None = None


@dataclass
class Scene:
    id: str
    title: str
    read_aloud: str | None = None
    dm_notes: str | None = None
    improv_notes: str | None = None
    npcs: list[str] = field(default_factory=list)
    monsters: list[str] = field(default_factory=list)
    checks: list[Check] = field(default_factory=list)
    exits: list[Exit] = field(default_factory=list)
    source_path: Path | None = None

    def available_exits(self, flags: set[str]) -> list[Exit]:
        return [exit_ for exit_ in self.exits if exit_.is_available(flags)]
