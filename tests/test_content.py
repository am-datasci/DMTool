"""Validates the content this repo actually ships.

Unlike the other suites, these run against the real project root rather
than a temp fixture: their job is to catch a schema change or a typo that
breaks the adventure a DM is about to run at a table.
"""

from __future__ import annotations

import os
import unittest

from engine import paths
from engine.loaders.adventure import discover_adventures, load_adventure
from engine.loaders.rules import load_dm_tips, load_ruleset


class ShippedContentTests(unittest.TestCase):
    def setUp(self) -> None:
        self._previous = os.environ.pop("DM_TOOL_ROOT", None)
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        if self._previous is not None:
            os.environ["DM_TOOL_ROOT"] = self._previous

    def test_every_shipped_adventure_loads_without_problems(self):
        manifests, problems = discover_adventures()
        self.assertEqual(problems, [], "an adventure folder failed to load")
        self.assertTrue(manifests, "no adventures found")
        for manifest in manifests:
            adventure = load_adventure(manifest)
            self.assertEqual(adventure.warnings, [], f"{manifest.slug} has warnings")

    def test_wild_sheep_chase_is_complete(self):
        manifest = next(m for m in discover_adventures()[0] if m.slug == "wild-sheep-chase")
        adventure = load_adventure(manifest)

        self.assertEqual(adventure.manifest.ruleset, "srd-5.1")
        self.assertEqual(len(adventure.scenes), 9)
        # The three NPCs the brief calls out as carrying the adventure.
        for npc_id in ("finethir-shinebright", "guz", "ahmed-noke"):
            npc = adventure.npcs[npc_id]
            self.assertTrue(npc.motivation, npc_id)
            self.assertTrue(npc.attitude or npc.summary, npc_id)
            self.assertTrue(npc.combat_behavior, npc_id)

    def test_the_module_branch_is_reachable_both_ways(self):
        """Handing the sheep over is a real branch, not a dead end."""
        manifest = next(m for m in discover_adventures()[0] if m.slug == "wild-sheep-chase")
        adventure = load_adventure(manifest)
        fight = adventure.scenes["02-shepherds-crooks"]

        self.assertEqual(
            [e.to for e in fight.available_exits(set())], ["03-after-the-dust"]
        )
        self.assertEqual(
            [e.to for e in fight.available_exits({"sheep_taken"})],
            ["09-noke-attacks-cradle"],
        )

    def test_every_scene_is_reachable_from_the_start(self):
        manifest = next(m for m in discover_adventures()[0] if m.slug == "wild-sheep-chase")
        adventure = load_adventure(manifest)

        seen, queue = set(), [adventure.manifest.start_scene]
        while queue:
            scene_id = queue.pop()
            if scene_id in seen:
                continue
            seen.add(scene_id)
            queue.extend(e.to for e in adventure.scenes[scene_id].exits)

        self.assertEqual(
            seen, set(adventure.scenes), "some scenes cannot be reached by any exit"
        )

    def test_encounters_are_rebalanced_for_first_level(self):
        """The printed module is for 4th-5th level. Nothing here should
        still be carrying its original hit points."""
        manifest = next(m for m in discover_adventures()[0] if m.slug == "wild-sheep-chase")
        adventure = load_adventure(manifest)

        as_printed = {"Guz": 67, "Ahmed Noke": 55, "Bed Dragon Wyrmling": 75}
        for actor in list(adventure.npcs.values()) + list(adventure.monsters.values()):
            original = as_printed.get(actor.name)
            if original is None or actor.stat_block is None:
                continue
            self.assertLess(
                actor.stat_block.hp, original,
                f"{actor.name} still has its 4th-level hit points",
            )

    def test_the_rulesets_and_tips_ship_intact(self):
        for ruleset_id in ("srd-5.1", "srd-5.2"):
            ruleset = load_ruleset(ruleset_id)
            self.assertEqual(len(ruleset.spells), 319, ruleset_id)
            self.assertEqual(len(ruleset.conditions), 15, ruleset_id)
            self.assertTrue(ruleset.bestiary, ruleset_id)
            self.assertEqual(ruleset.warnings, [], ruleset_id)
        self.assertTrue(load_dm_tips())


if __name__ == "__main__":
    unittest.main()
