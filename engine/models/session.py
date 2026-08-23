"""Per-table session state.

The tool tracks story flags and where the party is. It does not track
PC hit points, spell slots, or inventory — players own their own sheets.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Session:
    adventure: str
    current_scene: str
    created: str
    flags: set[str] = field(default_factory=set)
    #: Filled in by the setup wizard (phase 7).
    characters: list[dict] = field(default_factory=list)
    #: Filled in by the combat tracker (phase 2).
    combat: dict = field(default_factory=dict)
    path: Path | None = None

    def set_flag(self, name: str) -> bool:
        """Returns True if this changed anything."""
        if name in self.flags:
            return False
        self.flags.add(name)
        return True

    def unset_flag(self, name: str) -> bool:
        if name not in self.flags:
            return False
        self.flags.discard(name)
        return True

    def to_dict(self) -> dict:
        return {
            "adventure": self.adventure,
            "created": self.created,
            "current_scene": self.current_scene,
            "flags": sorted(self.flags),
            "characters": self.characters,
            "combat": self.combat,
        }
