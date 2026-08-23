"""Reading and writing session files.

A session is per-table state: where the party is and which story flags
are set. In this phase it is created directly with no player characters
— the setup wizard that records those replaces `new_session` later.
"""

from __future__ import annotations

import datetime as _datetime
from pathlib import Path

import yaml

from engine import paths
from engine.errors import ContentError
from engine.loaders.yaml_loader import (
    as_list,
    as_mapping,
    as_str_list,
    read_yaml,
    require_str,
)
from engine.models.adventure import Manifest
from engine.models.session import Session


def list_sessions(slug: str) -> list[Path]:
    """Session files for an adventure, most recently modified first."""
    directory = paths.sessions_dir(slug)
    if not directory.is_dir():
        return []
    files = [
        path
        for path in directory.iterdir()
        if path.is_file()
        and path.suffix in {".yaml", ".yml"}
        and not path.name.startswith(".")
    ]
    return sorted(files, key=lambda path: path.stat().st_mtime, reverse=True)


def latest_session(slug: str) -> Path | None:
    sessions = list_sessions(slug)
    return sessions[0] if sessions else None


def load_session(path: Path) -> Session:
    data = read_yaml(path)
    return Session(
        adventure=require_str(data, "adventure", path),
        current_scene=require_str(data, "current_scene", path),
        created=require_str(data, "created", path),
        flags=set(as_str_list(data, "flags", path)),
        characters=[
            as_mapping(entry, path, f"characters[{index + 1}]")
            for index, entry in enumerate(as_list(data, "characters", path))
        ],
        combat=as_mapping(data.get("combat"), path, "combat"),
        path=path,
    )


def save_session(session: Session) -> None:
    if session.path is None:
        raise ContentError("session has no file to save to")
    session.path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(
        session.to_dict(), sort_keys=False, allow_unicode=True, default_flow_style=False
    )
    session.path.write_text(text, encoding="utf-8")


def _unused_path(directory: Path, stem: str) -> Path:
    candidate = directory / f"{stem}.yaml"
    counter = 2
    while candidate.exists():
        candidate = directory / f"{stem}-{counter}.yaml"
        counter += 1
    return candidate


def new_session(manifest: Manifest, *, name: str = "session") -> Session:
    """Start a fresh session at the adventure's opening scene."""
    today = _datetime.date.today().isoformat()
    directory = paths.sessions_dir(manifest.slug)
    session = Session(
        adventure=manifest.slug,
        current_scene=manifest.start_scene,
        created=today,
        path=_unused_path(directory, f"{today}-{name}"),
    )
    save_session(session)
    return session
