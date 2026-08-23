"""YAML loading and validation.

Loaders raise `ContentError` for anything that would make content
unplayable, and collect warnings for anything an author probably got
wrong but that play can continue without (an unrecognised key, a
dangling reference).
"""

from engine.loaders.adventure import (
    discover_adventures,
    load_adventure,
    load_manifest,
)
from engine.loaders.rules import load_dm_tips, load_ruleset
from engine.loaders.session import (
    latest_session,
    list_sessions,
    load_session,
    new_session,
    save_session,
)

__all__ = [
    "discover_adventures",
    "latest_session",
    "list_sessions",
    "load_adventure",
    "load_manifest",
    "load_dm_tips",
    "load_ruleset",
    "load_session",
    "new_session",
    "save_session",
]
