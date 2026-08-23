"""Locating the project's content directories.

The engine is run from a checkout, so content lives alongside this
package. `DM_TOOL_ROOT` overrides that, which is what the tests use.
"""

from __future__ import annotations

import os
from pathlib import Path

ENV_ROOT = "DM_TOOL_ROOT"

#: Adventure folders whose name starts with this are scaffolding, not
#: playable content, and never appear in the picker.
PRIVATE_PREFIX = "_"

TEMPLATE_SLUG = "_template"
DEFAULT_RULESET = "srd-5.1"


def project_root() -> Path:
    override = os.environ.get(ENV_ROOT)
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parent.parent


def adventures_dir() -> Path:
    return project_root() / "adventures"


def rules_dir() -> Path:
    return project_root() / "rules"


def template_dir() -> Path:
    return adventures_dir() / TEMPLATE_SLUG


def adventure_dir(slug: str) -> Path:
    return adventures_dir() / slug


def sessions_dir(slug: str) -> Path:
    return adventure_dir(slug) / "sessions"


def ruleset_dir(ruleset: str) -> Path:
    return rules_dir() / ruleset


def is_private(slug: str) -> bool:
    return slug.startswith(PRIVATE_PREFIX)
