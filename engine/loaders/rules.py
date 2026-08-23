"""Loading a ruleset's reference data.

Adventures declare a ruleset in their manifest and the engine loads the
matching folder under `rules/`. Only the DC guideline table is required
— conditions, spells, and the bestiary arrive in a later phase, and a
missing one is reported rather than fatal.
"""

from __future__ import annotations

import re

from pathlib import Path

from engine import paths
from engine.errors import ContentError, warning
from engine.loaders.yaml_loader import (
    as_list,
    as_mapping,
    optional_str,
    read_yaml,
    require_int,
    require_str,
)
from engine.loaders.adventure import monster_from_mapping
from engine.models.actors import Monster
from engine.models.rules import Condition, DCTier, DyingRules, Ruleset

CORE_MECHANICS = "core-mechanics.yaml"
DM_TIPS = "dm-tips.yaml"
CONDITIONS = "conditions.yaml"
SPELLS = "spells.yaml"
BESTIARY = "bestiary.yaml"


def _load_core_mechanics(path: Path) -> tuple[list[DCTier], str | None, DyingRules | None]:
    data = read_yaml(path)
    tiers = []
    for index, raw in enumerate(as_list(data, "dc_table", path)):
        entry = as_mapping(raw, path, f"dc_table[{index + 1}]")
        tiers.append(
            DCTier(
                label=require_str(entry, "label", path),
                dc=require_int(entry, "dc", path),
            )
        )
    if not tiers:
        raise ContentError(
            "has no dc_table entries — the DC reference panel would be empty",
            path=path,
        )
    return tiers, optional_str(data, "save_dc_formula", path), _load_dying(data, path)


def _load_dying(data: dict, path: Path) -> DyingRules | None:
    raw = data.get("dying")
    if raw is None:
        return None
    entry = as_mapping(raw, path, "dying")
    return DyingRules(
        death_save_dc=require_int(entry, "death_save_dc", path),
        successes_to_stabilize=require_int(entry, "successes_to_stabilize", path),
        failures_to_die=require_int(entry, "failures_to_die", path),
        stabilize_check=optional_str(entry, "stabilize_check", path),
        notes=[str(note).strip() for note in as_list(entry, "notes", path)],
    )


def _load_conditions(path: Path) -> dict[str, Condition]:
    data = read_yaml(path)
    conditions: dict[str, Condition] = {}
    for index, raw in enumerate(as_list(data, "conditions", path)):
        entry = as_mapping(raw, path, f"conditions[{index + 1}]")
        name = require_str(entry, "name", path)
        condition_id = optional_str(entry, "id", path) or name.lower().replace(" ", "-")
        effects = [
            str(effect).strip()
            for effect in as_list(entry, "effects", path)
            if str(effect).strip()
        ]
        conditions[condition_id] = Condition(
            id=condition_id, name=name, effects=effects
        )
    return conditions


def _load_keyed(path: Path, key: str) -> dict[str, dict]:
    """Load a list of named entries into a dict keyed by lowercased name.

    Used for spells and the shared bestiary, whose full schemas land in
    the phase that transcribes them.
    """
    data = read_yaml(path)
    entries: dict[str, dict] = {}
    for index, raw in enumerate(as_list(data, key, path)):
        entry = as_mapping(raw, path, f"{key}[{index + 1}]")
        name = require_str(entry, "name", path)
        entries[name.lower()] = entry
    return entries


def slugify(name: str) -> str:
    """Bestiary entries share one file, so their id comes from the name."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _load_bestiary(path: Path, warnings: list[str]) -> dict[str, Monster]:
    data = read_yaml(path)
    monsters: dict[str, Monster] = {}
    for index, raw in enumerate(as_list(data, "monsters", path)):
        entry = as_mapping(raw, path, f"monsters[{index + 1}]")
        monster = monster_from_mapping(
            entry, path, slugify(require_str(entry, "name", path)), warnings
        )
        monsters[monster.id] = monster
    return monsters


def load_ruleset(ruleset_id: str) -> Ruleset:
    directory = paths.ruleset_dir(ruleset_id)
    if not directory.is_dir():
        available = (
            ", ".join(sorted(p.name for p in paths.rules_dir().iterdir() if p.is_dir()))
            if paths.rules_dir().is_dir()
            else "none"
        )
        raise ContentError(
            f"ruleset {ruleset_id!r} not found under rules/. Available: {available}"
        )

    ruleset = Ruleset(id=ruleset_id)
    core_path = directory / CORE_MECHANICS
    if not core_path.is_file():
        raise ContentError("is required but missing", path=core_path)
    (
        ruleset.dc_tiers,
        ruleset.save_dc_formula,
        ruleset.dying,
    ) = _load_core_mechanics(core_path)

    for filename, key, target in (
        (CONDITIONS, "conditions", "conditions"),
        (SPELLS, "spells", "spells"),
        (BESTIARY, "monsters", "bestiary"),
    ):
        path = directory / filename
        if not path.is_file():
            ruleset.warnings.append(
                warning("not present yet — lookups from it are unavailable", path=path)
            )
            continue
        if target == "conditions":
            ruleset.conditions = _load_conditions(path)
        elif target == "bestiary":
            ruleset.bestiary = _load_bestiary(path, ruleset.warnings)
        else:
            setattr(ruleset, target, _load_keyed(path, key))

    return ruleset


def load_dm_tips() -> list[tuple[str, str]]:
    """Generic technique tips, shared across rulesets.

    Lives at the root of rules/ because technique advice is not
    edition-specific. Missing file means no tips, not an error.
    """
    path = paths.rules_dir() / DM_TIPS
    if not path.is_file():
        return []
    data = read_yaml(path)
    tips = []
    for index, raw in enumerate(as_list(data, "tips", path)):
        entry = as_mapping(raw, path, f"tips[{index + 1}]")
        tips.append((require_str(entry, "title", path), require_str(entry, "text", path)))
    return tips
