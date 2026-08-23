"""Loading adventures: manifests, scenes, NPCs, and monsters."""

from __future__ import annotations

from pathlib import Path

from engine import paths
from engine.errors import ContentError, warning
from engine.loaders.yaml_loader import (
    as_int_mapping,
    as_list,
    as_mapping,
    as_str_list,
    optional_int,
    optional_str,
    read_yaml,
    require_int,
    require_str,
    unknown_field_warnings,
)
from engine.models.actors import Monster, NPC, Spellcasting, StatBlock, Trait
from engine.models.adventure import Adventure, Manifest
from engine.models.scene import Check, Exit, Scene

MANIFEST_FILENAME = "manifest.yaml"

MANIFEST_FIELDS = {
    "title",
    "slug",
    "ruleset",
    "summary",
    "level_range",
    "start_scene",
}
SCENE_FIELDS = {
    "id",
    "title",
    "read_aloud",
    "dm_notes",
    "improv_notes",
    "npcs",
    "monsters",
    "checks",
    "exits",
}
EXIT_FIELDS = {"to", "label", "condition", "unless"}
CHECK_FIELDS = {"name", "ability", "dc", "notes"}
NPC_FIELDS = {
    "id",
    "name",
    "summary",
    "motivation",
    "attitude",
    "combat_behavior",
    "improv_notes",
    "stat_block",
    "spellcasting",
}
MONSTER_FIELDS = {"id", "name", "summary", "combat_behavior", "stat_block", "spellcasting"}
STAT_BLOCK_FIELDS = {
    "ac",
    "hp",
    "hit_dice",
    "speed",
    "abilities",
    "saves",
    "skills",
    "senses",
    "languages",
    "cr",
    "traits",
    "actions",
    "reactions",
}
SPELLCASTING_FIELDS = {"ability", "save_dc", "save_dc_formula", "attack_bonus", "known"}


# --------------------------------------------------------------------------
# Manifests
# --------------------------------------------------------------------------


def load_manifest(manifest_path: Path, *, slug: str | None = None) -> Manifest:
    """Load one adventure's manifest without loading its content."""
    data = read_yaml(manifest_path)
    folder_slug = slug or manifest_path.parent.name

    manifest = Manifest(
        slug=data.get("slug") or folder_slug,
        title=require_str(data, "title", manifest_path),
        ruleset=require_str(data, "ruleset", manifest_path),
        start_scene=require_str(data, "start_scene", manifest_path),
        summary=optional_str(data, "summary", manifest_path),
        level_range=optional_str(data, "level_range", manifest_path),
        path=manifest_path,
    )
    manifest.warnings.extend(
        unknown_field_warnings(data, MANIFEST_FIELDS, manifest_path)
    )
    if manifest.slug != folder_slug:
        manifest.warnings.append(
            warning(
                f"slug {manifest.slug!r} does not match the folder name "
                f"{folder_slug!r} — using the folder name",
                path=manifest_path,
                field="slug",
            )
        )
        manifest.slug = folder_slug
    return manifest


def discover_adventures() -> tuple[list[Manifest], list[str]]:
    """Scan `adventures/` for playable folders.

    Returns the manifests that loaded, plus a list of problems for the
    ones that did not. A single broken adventure must never stop the
    launcher from listing the others.
    """
    root = paths.adventures_dir()
    manifests: list[Manifest] = []
    problems: list[str] = []

    if not root.is_dir():
        return manifests, [f"{root}: adventures directory not found"]

    for folder in sorted(root.iterdir()):
        if not folder.is_dir() or paths.is_private(folder.name):
            continue
        manifest_path = folder / MANIFEST_FILENAME
        if not manifest_path.is_file():
            problems.append(
                f"{folder.name}: skipped — no {MANIFEST_FILENAME} "
                "(not an adventure folder yet)"
            )
            continue
        try:
            manifests.append(load_manifest(manifest_path, slug=folder.name))
        except ContentError as exc:
            problems.append(f"{folder.name}: skipped — {exc.describe(relative_to=root)}")

    return manifests, problems


# --------------------------------------------------------------------------
# Scenes
# --------------------------------------------------------------------------


def _load_exit(raw: object, path: Path, index: int, warnings: list[str]) -> Exit:
    field = f"exits[{index + 1}]"
    data = as_mapping(raw, path, field)
    warnings.extend(
        warning(f"unrecognised field {key!r} in {field} — ignored", path=path)
        for key in sorted(data)
        if key not in EXIT_FIELDS
    )
    to = data.get("to")
    if not isinstance(to, str) or not to.strip():
        raise ContentError("needs a 'to' scene id", path=path, field=field)
    label = data.get("label")
    if not isinstance(label, str) or not label.strip():
        raise ContentError(
            "needs a 'label' describing this route to the DM", path=path, field=field
        )
    return Exit(
        to=to.strip(),
        label=label.strip(),
        condition=optional_str(data, "condition", path),
        unless=optional_str(data, "unless", path),
    )


def _load_check(raw: object, path: Path, index: int, warnings: list[str]) -> Check:
    field = f"checks[{index + 1}]"
    data = as_mapping(raw, path, field)
    warnings.extend(
        warning(f"unrecognised field {key!r} in {field} — ignored", path=path)
        for key in sorted(data)
        if key not in CHECK_FIELDS
    )
    return Check(
        name=require_str(data, "name", path),
        ability=require_str(data, "ability", path),
        dc=require_int(data, "dc", path),
        notes=optional_str(data, "notes", path),
    )


def load_scene(path: Path) -> tuple[Scene, list[str]]:
    data = read_yaml(path)
    warnings = unknown_field_warnings(data, SCENE_FIELDS, path)
    stem = path.stem

    declared_id = optional_str(data, "id", path)
    if declared_id is not None and declared_id != stem:
        raise ContentError(
            f"is {declared_id!r} but the file is named {stem!r}. Exits refer to "
            "scenes by id, so these must match — rename the file or fix the id",
            path=path,
            field="id",
        )

    scene = Scene(
        id=stem,
        title=require_str(data, "title", path),
        read_aloud=optional_str(data, "read_aloud", path),
        dm_notes=optional_str(data, "dm_notes", path),
        improv_notes=optional_str(data, "improv_notes", path),
        npcs=as_str_list(data, "npcs", path),
        monsters=as_str_list(data, "monsters", path),
        checks=[
            _load_check(raw, path, index, warnings)
            for index, raw in enumerate(as_list(data, "checks", path))
        ],
        exits=[
            _load_exit(raw, path, index, warnings)
            for index, raw in enumerate(as_list(data, "exits", path))
        ],
        source_path=path,
    )
    return scene, warnings


# --------------------------------------------------------------------------
# Actors
# --------------------------------------------------------------------------


def _load_traits(raw: object, path: Path, field: str) -> list[Trait]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ContentError(
            f"must be a list, found {type(raw).__name__}", path=path, field=field
        )
    traits = []
    for index, item in enumerate(raw):
        entry = as_mapping(item, path, f"{field}[{index + 1}]")
        traits.append(
            Trait(
                name=require_str(entry, "name", path),
                text=require_str(entry, "text", path),
            )
        )
    return traits


def _load_cr(raw: object, path: Path) -> str | None:
    """Challenge rating is written as either a number or a fraction."""
    if raw is None:
        return None
    if isinstance(raw, bool):
        raise ContentError("must be a number or fraction", path=path, field="cr")
    if isinstance(raw, (int, float)):
        return str(raw)
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    raise ContentError("must be a number or fraction", path=path, field="cr")


def _load_stat_block(raw: object, path: Path, warnings: list[str]) -> StatBlock | None:
    if raw is None:
        return None
    data = as_mapping(raw, path, "stat_block")
    warnings.extend(
        warning(f"unrecognised field {key!r} in stat_block — ignored", path=path)
        for key in sorted(data)
        if key not in STAT_BLOCK_FIELDS
    )
    return StatBlock(
        ac=optional_int(data, "ac", path),
        hp=optional_int(data, "hp", path),
        hit_dice=optional_str(data, "hit_dice", path),
        speed=optional_str(data, "speed", path),
        abilities=as_int_mapping(data.get("abilities"), path, "abilities"),
        saves=as_int_mapping(data.get("saves"), path, "saves"),
        skills=as_int_mapping(data.get("skills"), path, "skills"),
        senses=optional_str(data, "senses", path),
        languages=optional_str(data, "languages", path),
        cr=_load_cr(data.get("cr"), path),
        traits=_load_traits(data.get("traits"), path, "traits"),
        actions=_load_traits(data.get("actions"), path, "actions"),
        reactions=_load_traits(data.get("reactions"), path, "reactions"),
    )


def _load_spellcasting(
    raw: object, path: Path, warnings: list[str]
) -> Spellcasting | None:
    if raw is None:
        return None
    data = as_mapping(raw, path, "spellcasting")
    warnings.extend(
        warning(f"unrecognised field {key!r} in spellcasting — ignored", path=path)
        for key in sorted(data)
        if key not in SPELLCASTING_FIELDS
    )
    return Spellcasting(
        ability=optional_str(data, "ability", path),
        save_dc=optional_int(data, "save_dc", path),
        save_dc_formula=optional_str(data, "save_dc_formula", path),
        attack_bonus=optional_int(data, "attack_bonus", path),
        known=as_str_list(data, "known", path),
    )


def _check_declared_id(data: dict, path: Path, kind: str) -> str:
    stem = path.stem
    declared = optional_str(data, "id", path)
    if declared is not None and declared != stem:
        raise ContentError(
            f"is {declared!r} but the file is named {stem!r}. Scenes refer to "
            f"{kind}s by id, so these must match — rename the file or fix the id",
            path=path,
            field="id",
        )
    return stem


def load_npc(path: Path) -> tuple[NPC, list[str]]:
    data = read_yaml(path)
    warnings = unknown_field_warnings(data, NPC_FIELDS, path)
    npc = NPC(
        id=_check_declared_id(data, path, "NPC"),
        name=require_str(data, "name", path),
        summary=optional_str(data, "summary", path),
        motivation=optional_str(data, "motivation", path),
        attitude=optional_str(data, "attitude", path),
        combat_behavior=optional_str(data, "combat_behavior", path),
        improv_notes=optional_str(data, "improv_notes", path),
        stat_block=_load_stat_block(data.get("stat_block"), path, warnings),
        spellcasting=_load_spellcasting(data.get("spellcasting"), path, warnings),
        source_path=path,
    )
    return npc, warnings


def load_monster(path: Path) -> tuple[Monster, list[str]]:
    data = read_yaml(path)
    warnings = unknown_field_warnings(data, MONSTER_FIELDS, path)
    monster = Monster(
        id=_check_declared_id(data, path, "monster"),
        name=require_str(data, "name", path),
        summary=optional_str(data, "summary", path),
        combat_behavior=optional_str(data, "combat_behavior", path),
        stat_block=_load_stat_block(data.get("stat_block"), path, warnings),
        spellcasting=_load_spellcasting(data.get("spellcasting"), path, warnings),
        source_path=path,
    )
    return monster, warnings


# --------------------------------------------------------------------------
# Whole adventures
# --------------------------------------------------------------------------


def _yaml_files(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(
        path
        for path in folder.iterdir()
        if path.is_file()
        and path.suffix in {".yaml", ".yml"}
        and not path.name.startswith(".")
    )


def load_adventure(manifest: Manifest) -> Adventure:
    """Load every content file for an adventure and cross-check references."""
    directory = manifest.directory
    if directory is None:
        raise ContentError("adventure has no directory on disk")

    adventure = Adventure(manifest=manifest)
    adventure.warnings.extend(manifest.warnings)

    for path in _yaml_files(directory / "scenes"):
        scene, warnings = load_scene(path)
        if scene.id in adventure.scenes:
            raise ContentError(f"duplicate scene id {scene.id!r}", path=path)
        adventure.scenes[scene.id] = scene
        adventure.warnings.extend(warnings)

    for path in _yaml_files(directory / "npcs"):
        npc, warnings = load_npc(path)
        adventure.npcs[npc.id] = npc
        adventure.warnings.extend(warnings)

    for path in _yaml_files(directory / "monsters"):
        monster, warnings = load_monster(path)
        adventure.monsters[monster.id] = monster
        adventure.warnings.extend(warnings)

    adventure.warnings.extend(validate_references(adventure))
    return adventure


def validate_references(adventure: Adventure) -> list[str]:
    """Check that every id an author typed points at something real.

    A missing start scene is fatal — there is nowhere to begin. Anything
    else is a warning: the DM can still run the session, and stopping
    play over a dangling reference would be worse than flagging it.
    """
    if not adventure.scenes:
        raise ContentError(
            "has no scenes — add at least one file under scenes/",
            path=adventure.manifest.path,
        )

    start = adventure.manifest.start_scene
    if start not in adventure.scenes:
        known = ", ".join(sorted(adventure.scenes)) or "none"
        raise ContentError(
            f"names start_scene {start!r}, which does not exist. Scenes found: {known}",
            path=adventure.manifest.path,
            field="start_scene",
        )

    warnings: list[str] = []
    for scene in adventure.scenes_in_order():
        for exit_ in scene.exits:
            if exit_.to not in adventure.scenes:
                warnings.append(
                    warning(
                        f"exit {exit_.label!r} leads to {exit_.to!r}, "
                        "which is not a scene in this adventure",
                        path=scene.source_path,
                    )
                )
        for npc_id in scene.npcs:
            if npc_id not in adventure.npcs:
                warnings.append(
                    warning(
                        f"lists NPC {npc_id!r}, which has no file in npcs/",
                        path=scene.source_path,
                    )
                )
        for monster_id in scene.monsters:
            if monster_id not in adventure.monsters:
                warnings.append(
                    warning(
                        f"lists monster {monster_id!r}, which has no file in monsters/",
                        path=scene.source_path,
                    )
                )
    return warnings
