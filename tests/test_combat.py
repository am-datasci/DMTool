"""The combat model: initiative order, turn cycling, and serialization."""

from __future__ import annotations

import unittest

from engine.models.combat import Combat, Combatant


def _combat() -> Combat:
    return Combat(
        active=True,
        combatants=[
            Combatant(name="Boar", initiative=12, hp=11, max_hp=11),
            Combatant(name="Perrin", initiative=18, is_pc=True),
            Combatant(name="Goblin", initiative=12, hp=7, max_hp=7),
        ],
    )


class OrderTests(unittest.TestCase):
    def test_highest_initiative_goes_first(self):
        self.assertEqual([c.name for c in _combat().order()], ["Perrin", "Boar", "Goblin"])

    def test_ties_break_by_name_so_the_order_is_stable(self):
        first = [c.name for c in _combat().order()]
        self.assertEqual(first, [c.name for c in _combat().order()])

    def test_combatants_without_initiative_sort_last(self):
        combat = _combat()
        combat.combatants.append(Combatant(name="Aardvark"))
        self.assertEqual(combat.order()[-1].name, "Aardvark")


class TurnTests(unittest.TestCase):
    def test_next_walks_the_order(self):
        combat = _combat()
        self.assertEqual(combat.current().name, "Perrin")
        combat.advance()
        self.assertEqual(combat.current().name, "Boar")

    def test_wrapping_past_the_end_increments_the_round(self):
        combat = _combat()
        for _ in range(3):
            combat.advance()
        self.assertEqual(combat.round, 2)
        self.assertEqual(combat.current().name, "Perrin")

    def test_stepping_back_past_the_start_decrements_the_round(self):
        combat = _combat()
        combat.round = 2
        combat.advance(-1)
        self.assertEqual(combat.round, 1)
        self.assertEqual(combat.current().name, "Goblin")

    def test_round_never_drops_below_one(self):
        combat = _combat()
        for _ in range(5):
            combat.advance(-1)
        self.assertGreaterEqual(combat.round, 1)

    def test_no_current_combatant_when_combat_is_inactive(self):
        combat = _combat()
        combat.active = False
        self.assertIsNone(combat.current())


class FindTests(unittest.TestCase):
    def test_exact_name_case_insensitive(self):
        self.assertEqual(_combat().find("perrin").name, "Perrin")

    def test_unique_prefix_matches(self):
        self.assertEqual(_combat().find("bo").name, "Boar")

    def test_ambiguous_prefix_matches_nothing(self):
        """Two combatants share a prefix, so the tool must not guess."""
        combat = _combat()
        combat.combatants.append(Combatant(name="Boar Cub"))
        self.assertIsNone(combat.find("boa"))
        self.assertEqual(combat.find("boar cub").name, "Boar Cub")

    def test_unknown_name_returns_none(self):
        self.assertIsNone(_combat().find("nobody"))


class StatusTests(unittest.TestCase):
    def test_pcs_show_no_hit_points(self):
        self.assertEqual(Combatant(name="Perrin", is_pc=True).status(), "pc")

    def test_monsters_show_hit_points(self):
        self.assertEqual(Combatant(name="Boar", hp=5, max_hp=11).status(), "5/11 hp")

    def test_downed_shows_the_death_save_tally(self):
        c = Combatant(name="Perrin", is_pc=True, down=True, death_successes=1, death_failures=2)
        self.assertIn("1", c.status())
        self.assertIn("2", c.status())


class RoundTripTests(unittest.TestCase):
    def test_combat_survives_save_and_reload(self):
        combat = _combat()
        combat.advance()
        combat.combatants[0].conditions.add("prone")
        combat.combatants[1].down = True
        combat.combatants[1].death_failures = 2

        restored = Combat.from_dict(combat.to_dict())
        self.assertEqual(restored.round, combat.round)
        self.assertEqual(restored.turn, combat.turn)
        self.assertEqual(restored.current().name, combat.current().name)
        self.assertEqual(restored.find("Boar").conditions, {"prone"})
        self.assertTrue(restored.find("Perrin").down)
        self.assertEqual(restored.find("Perrin").death_failures, 2)

    def test_empty_dict_gives_an_empty_combat(self):
        combat = Combat.from_dict({})
        self.assertFalse(combat.active)
        self.assertEqual(combat.combatants, [])


if __name__ == "__main__":
    unittest.main()
