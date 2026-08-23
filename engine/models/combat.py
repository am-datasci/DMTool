"""Combat bookkeeping.

Hit points are tracked for the creatures the DM runs — monsters and NPCs
— because nobody else is holding those numbers. Player characters sit in
the initiative order without a hit point total: the player's sheet is
authoritative. What the tool does track for a PC is the death-save
sequence once they go down, which is the thing a new DM forgets.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Combatant:
    name: str
    initiative: int | None = None
    #: A player character. Hit points stay None — see the module docstring.
    is_pc: bool = False
    hp: int | None = None
    max_hp: int | None = None
    #: NPC or monster id, so the stat block can be looked up from here.
    ref: str | None = None
    conditions: set[str] = field(default_factory=set)
    #: At 0 hit points and making death saving throws.
    down: bool = False
    stable: bool = False
    dead: bool = False
    death_successes: int = 0
    death_failures: int = 0

    @property
    def tracks_hp(self) -> bool:
        return not self.is_pc and self.max_hp is not None

    def status(self) -> str:
        """A short status string for the tracker line."""
        if self.dead:
            return "dead"
        if self.stable:
            return "stable at 0"
        if self.down:
            return f"DOWN {self.death_successes}✓/{self.death_failures}✗"
        if self.tracks_hp:
            return f"{self.hp}/{self.max_hp} hp"
        if self.is_pc:
            return "pc"
        return ""

    def reset_death_saves(self) -> None:
        self.down = False
        self.stable = False
        self.death_successes = 0
        self.death_failures = 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "initiative": self.initiative,
            "is_pc": self.is_pc,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "ref": self.ref,
            "conditions": sorted(self.conditions),
            "down": self.down,
            "stable": self.stable,
            "dead": self.dead,
            "death_successes": self.death_successes,
            "death_failures": self.death_failures,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Combatant:
        return cls(
            name=str(data.get("name", "?")),
            initiative=data.get("initiative"),
            is_pc=bool(data.get("is_pc", False)),
            hp=data.get("hp"),
            max_hp=data.get("max_hp"),
            ref=data.get("ref"),
            conditions=set(data.get("conditions") or []),
            down=bool(data.get("down", False)),
            stable=bool(data.get("stable", False)),
            dead=bool(data.get("dead", False)),
            death_successes=int(data.get("death_successes", 0) or 0),
            death_failures=int(data.get("death_failures", 0) or 0),
        )


@dataclass
class Combat:
    active: bool = False
    round: int = 1
    #: Index into the initiative-sorted order, not into `combatants`.
    turn: int = 0
    combatants: list[Combatant] = field(default_factory=list)

    def order(self) -> list[Combatant]:
        """Initiative order, highest first. Unrolled combatants sort last."""
        return sorted(
            self.combatants,
            key=lambda c: (c.initiative is None, -(c.initiative or 0), c.name.lower()),
        )

    def current(self) -> Combatant | None:
        order = self.order()
        if not order or not self.active:
            return None
        return order[self.turn % len(order)]

    def find(self, name: str) -> Combatant | None:
        """Match a combatant by name, case-insensitively, then by prefix."""
        lowered = name.strip().lower()
        if not lowered:
            return None
        for combatant in self.combatants:
            if combatant.name.lower() == lowered:
                return combatant
        matches = [c for c in self.combatants if c.name.lower().startswith(lowered)]
        return matches[0] if len(matches) == 1 else None

    def advance(self, step: int = 1) -> None:
        """Move the turn marker, rolling the round counter over."""
        order = self.order()
        if not order:
            return
        position = self.turn + step
        while position < 0:
            position += len(order)
            self.round = max(1, self.round - 1)
        while position >= len(order):
            position -= len(order)
            self.round += 1
        self.turn = position

    def to_dict(self) -> dict:
        return {
            "active": self.active,
            "round": self.round,
            "turn": self.turn,
            "combatants": [c.to_dict() for c in self.combatants],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Combat:
        if not data:
            return cls()
        return cls(
            active=bool(data.get("active", False)),
            round=int(data.get("round", 1) or 1),
            turn=int(data.get("turn", 0) or 0),
            combatants=[
                Combatant.from_dict(entry) for entry in (data.get("combatants") or [])
            ],
        )
