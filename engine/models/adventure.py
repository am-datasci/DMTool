"""Adventure manifest and the fully-loaded adventure."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from engine.models.actors import Monster, NPC
from engine.models.scene import Scene


@dataclass
class Manifest:
    """The identity of an adventure — enough to list it in the picker.

    Loaded on its own during the folder scan so one broken adventure
    can be skipped with a warning instead of stopping the launcher.
    """

    slug: str
    title: str
    ruleset: str
    start_scene: str
    summary: str | None = None
    level_range: str | None = None
    path: Path | None = None
    warnings: list[str] = field(default_factory=list)

    @property
    def directory(self) -> Path | None:
        return self.path.parent if self.path is not None else None


@dataclass
class Adventure:
    manifest: Manifest
    scenes: dict[str, Scene] = field(default_factory=dict)
    npcs: dict[str, NPC] = field(default_factory=dict)
    monsters: dict[str, Monster] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @property
    def slug(self) -> str:
        return self.manifest.slug

    @property
    def title(self) -> str:
        return self.manifest.title

    def scene(self, scene_id: str) -> Scene | None:
        return self.scenes.get(scene_id)

    def scenes_in_order(self) -> list[Scene]:
        """Scenes sorted by id, which is how authors number their files.

        Only used for the unfiltered "Other..." list — play order comes
        from exits, never from this.
        """
        return [self.scenes[key] for key in sorted(self.scenes)]
