"""The pre-session setup wizard, driven the way a user drives it."""

from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stdout

from engine import setup_wizard
from engine.loaders.adventure import load_manifest
from engine.loaders.rules import load_ruleset
from engine.loaders.session import list_sessions, load_session
from tests.support import ContentTestCase

_RULESET = None


def shared_ruleset():
    global _RULESET
    if _RULESET is None:
        _RULESET = load_ruleset("srd-5.1")
    return _RULESET


class WizardTestCase(ContentTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.make_adventure("example")
        self.manifest = load_manifest(
            self.root / "adventures" / "example" / "manifest.yaml", slug="example"
        )
        self.ruleset = shared_ruleset()

    def run_wizard(self, keys: str):
        """Drive the wizard with scripted stdin, returning (session, output)."""
        original = sys.stdin
        sys.stdin = io.StringIO(keys)
        buffer = io.StringIO()
        try:
            with redirect_stdout(buffer):
                session = setup_wizard.run(self.manifest, self.ruleset)
        finally:
            sys.stdin = original
        return session, buffer.getvalue()


class BasicFlowTests(WizardTestCase):
    def test_a_single_non_caster_produces_a_valid_session(self):
        session, _ = self.run_wizard("1\nThora\n\nFighter\n\nn\n1\n")

        self.assertEqual(len(session.characters), 1)
        thora = session.characters[0]
        self.assertEqual(thora["name"], "Thora")
        self.assertEqual(thora["character_class"], "Fighter")
        self.assertEqual(thora["level"], 1)
        self.assertNotIn("spellcasting", thora, "a fighter has no spellcasting block")

        reloaded = load_session(session.path)
        self.assertEqual(reloaded.characters, session.characters)
        self.assertEqual(reloaded.current_scene, self.manifest.start_scene)

    def test_the_optional_player_name_is_recorded_when_given(self):
        session, _ = self.run_wizard("1\nThora\nAlan\nFighter\n\nn\n1\n")
        self.assertEqual(session.characters[0]["player"], "Alan")

    def test_a_blank_player_name_is_not_an_error(self):
        session, _ = self.run_wizard("1\nThora\n\nFighter\n\nn\n1\n")
        self.assertIsNone(session.characters[0]["player"])

    def test_several_characters_in_one_run(self):
        session, _ = self.run_wizard(
            "2\n"
            "Thora\n\nFighter\n\nn\n"
            "Brakk\n\nRogue\n2\nn\n"
            "1\n"
        )
        self.assertEqual([c["name"] for c in session.characters], ["Thora", "Brakk"])
        self.assertEqual(session.characters[1]["level"], 2)

    def test_a_party_of_none_is_allowed(self):
        """Useful for testing the play UI without inventing characters."""
        session, _ = self.run_wizard("0\n1\n")
        self.assertEqual(session.characters, [])

    def test_the_tool_records_no_hit_points_or_equipment(self):
        session, _ = self.run_wizard("1\nThora\n\nFighter\n\nn\n1\n")
        recorded = set(session.characters[0])
        self.assertEqual(recorded, {"name", "player", "character_class", "level"})


class SpellEntryTests(WizardTestCase):
    def test_an_exactly_typed_spell_is_accepted_without_a_prompt(self):
        session, output = self.run_wizard(
            "1\nSela\n\nCleric\n\ny\nWisdom\n13\nCure Wounds\n\n1\n"
        )
        casting = session.characters[0]["spellcasting"]
        self.assertEqual(casting["known"], ["Cure Wounds"])
        self.assertEqual(casting["save_dc"], 13)
        self.assertEqual(casting["ability"], "Wisdom")
        self.assertNotIn("Did you mean", output)

    def test_the_save_dc_formula_is_shown_but_not_calculated(self):
        session, output = self.run_wizard(
            "1\nSela\n\nCleric\n\ny\nWisdom\n13\n\n1\n"
        )
        self.assertIn("proficiency bonus", output)
        self.assertIn("does not work it out", output)
        self.assertEqual(session.characters[0]["spellcasting"]["save_dc"], 13)

    def test_case_and_spacing_do_not_matter(self):
        session, _ = self.run_wizard(
            "1\nSela\n\nCleric\n\ny\nWisdom\n13\ncurewounds\n\n1\n"
        )
        self.assertEqual(session.characters[0]["spellcasting"]["known"], ["Cure Wounds"])

    def test_a_partial_name_asks_before_expanding_it(self):
        """The tool picked a name the user did not type, so it must confirm."""
        session, output = self.run_wizard(
            "1\nSela\n\nCleric\n\ny\nWisdom\n13\nfire bo\ny\n\n1\n"
        )
        self.assertIn("Did you mean Fire Bolt?", output)
        self.assertEqual(session.characters[0]["spellcasting"]["known"], ["Fire Bolt"])

    def test_declining_the_expansion_asks_again(self):
        session, _ = self.run_wizard(
            "1\nSela\n\nCleric\n\ny\nWisdom\n13\nfire bo\nn\nCure Wounds\n\n1\n"
        )
        self.assertEqual(session.characters[0]["spellcasting"]["known"], ["Cure Wounds"])

    def test_a_typo_offers_a_menu_and_is_never_auto_accepted(self):
        session, output = self.run_wizard(
            "1\nSela\n\nCleric\n\ny\nWisdom\n13\nburnin hands\n1\n\n1\n"
        )
        self.assertIn("No exact match", output)
        self.assertEqual(
            session.characters[0]["spellcasting"]["known"], ["Burning Hands"]
        )

    def test_an_unmatched_name_can_be_kept_as_typed(self):
        """Homebrew, or anything outside the SRD, must still be recordable."""
        session, output = self.run_wizard(
            "1\nSela\n\nCleric\n\ny\nWisdom\n13\nZzyzx Blast\ny\n\n1\n"
        )
        self.assertIn("Nothing in srd-5.1 matches", output)
        self.assertEqual(session.characters[0]["spellcasting"]["known"], ["Zzyzx Blast"])

    def test_duplicate_spells_are_refused(self):
        session, output = self.run_wizard(
            "1\nSela\n\nCleric\n\ny\nWisdom\n13\nCure Wounds\nCure Wounds\n\n1\n"
        )
        self.assertIn("already on the list", output)
        self.assertEqual(session.characters[0]["spellcasting"]["known"], ["Cure Wounds"])

    def test_a_caster_with_no_spells_listed_is_allowed(self):
        session, _ = self.run_wizard("1\nSela\n\nCleric\n\ny\nWisdom\n13\n\n1\n")
        self.assertEqual(session.characters[0]["spellcasting"]["known"], [])


class ReviewTests(WizardTestCase):
    def test_a_character_can_be_re_entered_before_writing(self):
        session, _ = self.run_wizard(
            "1\nThroa\n\nFigther\n\nn\n"      # typo'd name and class
            "3\n1\n"                          # re-enter one -> the first
            "Thora\n\nFighter\n\nn\n"
            "1\n"
        )
        self.assertEqual(session.characters[0]["name"], "Thora")
        self.assertEqual(session.characters[0]["character_class"], "Fighter")
        self.assertEqual(len(session.characters), 1, "correcting must not duplicate")

    def test_another_character_can_be_added_at_review(self):
        session, _ = self.run_wizard(
            "1\nThora\n\nFighter\n\nn\n"
            "2\nBrakk\n\nRogue\n\nn\n"
            "1\n"
        )
        self.assertEqual([c["name"] for c in session.characters], ["Thora", "Brakk"])

    def test_the_party_is_shown_before_writing(self):
        _, output = self.run_wizard("1\nThora\nAlan\nFighter\n\nn\n1\n")
        self.assertIn("The party:", output)
        self.assertIn("Thora", output)
        self.assertIn("Fighter", output)


class SessionFileTests(WizardTestCase):
    def test_exactly_one_session_file_is_written(self):
        self.run_wizard("1\nThora\n\nFighter\n\nn\n1\n")
        self.assertEqual(len(list_sessions("example")), 1)

    def test_abandoning_setup_writes_nothing(self):
        """Ctrl-C or end of input partway through must not leave a session."""
        original = sys.stdin
        sys.stdin = io.StringIO("1\nThora\n")  # input ends mid-character
        try:
            with redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit):
                    setup_wizard.run(self.manifest, self.ruleset)
        finally:
            sys.stdin = original
        self.assertEqual(list_sessions("example"), [])


if __name__ == "__main__":
    unittest.main()
