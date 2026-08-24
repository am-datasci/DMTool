"""The tutorial's command reference is generated from the registry.

Generated once and committed rather than built at runtime, so it has to
be checked, or it silently rots the first time a command changes.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from engine.app import COMMANDS

DOC = Path(__file__).resolve().parent.parent / "docs" / "running-a-session.md"


class TutorialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = DOC.read_text(encoding="utf-8")
        start = cls.text.index("## Command reference")
        end = cls.text.index("## If something looks wrong")
        cls.reference = cls.text[start:end]

    def test_every_command_is_documented(self):
        for command in COMMANDS:
            usage = command.usage.replace("|", "\\|")
            self.assertIn(
                f"| `{usage}` |",
                self.reference,
                f"{command.name} is missing from the tutorial's reference — "
                "regenerate it from engine.app.COMMANDS",
            )

    def test_every_summary_matches_the_registry(self):
        for command in COMMANDS:
            self.assertIn(command.summary, self.reference, command.name)

    def test_the_reference_documents_nothing_extra(self):
        documented = set(re.findall(r"^\| `(.+?)` \|", self.reference, re.M))
        expected = {c.usage.replace("|", "\\|") for c in COMMANDS}
        self.assertEqual(documented, expected)

    def test_pipes_in_usage_are_escaped_for_markdown(self):
        """An unescaped pipe ends the table cell early."""
        for line in self.reference.splitlines():
            if not line.startswith("| `"):
                continue
            cell = line.split("` |")[0]
            self.assertNotIn("|", cell.replace("\\|", "").lstrip("| `"), line)

    def test_the_design_rules_are_stated_up_front(self):
        """A new DM must not expect the tool to roll or decide."""
        opening = self.text[: self.text.index("## Before the session")]
        self.assertIn("never rolls dice", opening)
        self.assertIn("never decides", opening)
        self.assertIn("does not track player characters' hit points", opening)


if __name__ == "__main__":
    unittest.main()
