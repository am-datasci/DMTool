"""Shared setup for the loader tests.

Each test gets a throwaway project root containing a copy of the real
`_template/` adventure and the real rules folder, pointed at by
DM_TOOL_ROOT. Testing against the shipped template is deliberate: it
means "the template is valid" is checked on every run, and the template
is what "Create new adventure..." hands to a new author.
"""

from __future__ import annotations

import atexit
import os
import shutil
import tempfile
import unittest
from pathlib import Path

REAL_ROOT = Path(__file__).resolve().parent.parent

#: rules/ is read-only for every test and now holds a 374KB spell file, so
#: it is copied once for the whole run and symlinked into each test root
#: rather than copied per test.
_SHARED_RULES = Path(tempfile.mkdtemp(prefix="dmtool-rules-")) / "rules"
shutil.copytree(REAL_ROOT / "rules", _SHARED_RULES)
atexit.register(shutil.rmtree, _SHARED_RULES.parent, True)


class ContentTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "adventures").mkdir()
        shutil.copytree(
            REAL_ROOT / "adventures" / "_template", self.root / "adventures" / "_template"
        )
        (self.root / "rules").symlink_to(_SHARED_RULES, target_is_directory=True)

        self._previous = os.environ.get("DM_TOOL_ROOT")
        os.environ["DM_TOOL_ROOT"] = str(self.root)
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        if self._previous is None:
            os.environ.pop("DM_TOOL_ROOT", None)
        else:
            os.environ["DM_TOOL_ROOT"] = self._previous
        self._tmp.cleanup()

    def make_adventure(self, slug: str) -> Path:
        """Copy the template into a playable adventure folder."""
        target = self.root / "adventures" / slug
        shutil.copytree(self.root / "adventures" / "_template", target)
        manifest = target / "manifest.yaml"
        manifest.write_text(
            manifest.read_text(encoding="utf-8").replace("slug: _template", f"slug: {slug}"),
            encoding="utf-8",
        )
        return target

    def write(self, path: Path, text: str) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path
