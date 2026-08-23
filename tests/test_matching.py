"""Fuzzy name matching, shared by lookup and (later) the setup wizard."""

from __future__ import annotations

import unittest

from engine import matching

SPELLS = [
    "Burning Hands",
    "Charm Person",
    "Chill Touch",
    "Cure Wounds",
    "Fire Bolt",
    "Magic Missile",
]


class NormalizeTests(unittest.TestCase):
    def test_case_and_punctuation_are_folded(self):
        self.assertEqual(matching.normalize("Cure Wounds"), "cure wounds")
        self.assertEqual(matching.normalize("cure-wounds"), "cure wounds")
        self.assertEqual(matching.normalize("  CURE   WOUNDS! "), "cure wounds")


class FindTests(unittest.TestCase):
    def test_exact_match_regardless_of_formatting(self):
        for query in ("Cure Wounds", "cure wounds", "CURE-WOUNDS", "curewounds "):
            self.assertEqual(matching.find(query, SPELLS).exact, "Cure Wounds", query)

    def test_unique_prefix_counts_as_found(self):
        self.assertEqual(matching.find("fire", SPELLS).exact, "Fire Bolt")

    def test_ambiguous_prefix_offers_both(self):
        match = matching.find("ch", SPELLS)
        self.assertIsNone(match.exact)
        self.assertEqual(sorted(match.suggestions), ["Charm Person", "Chill Touch"])

    def test_typo_is_suggested_never_auto_accepted(self):
        match = matching.find("burnin hands", SPELLS)
        self.assertIsNone(match.exact, "a near miss must be confirmed, not assumed")
        self.assertIn("Burning Hands", match.suggestions)

    def test_nonsense_returns_nothing(self):
        match = matching.find("xyzzy", SPELLS)
        self.assertIsNone(match.exact)
        self.assertEqual(match.suggestions, [])

    def test_empty_inputs_are_safe(self):
        self.assertIsNone(matching.find("", SPELLS).exact)
        self.assertIsNone(matching.find("fire", []).exact)

    def test_suggestions_are_capped(self):
        many = [f"Spell {n}" for n in range(50)]
        self.assertLessEqual(len(matching.find("spell", many).suggestions), 5)


if __name__ == "__main__":
    unittest.main()
