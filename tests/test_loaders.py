"""Loading and validating adventure content."""

from __future__ import annotations

import unittest
from pathlib import Path

from engine.errors import ContentError
from engine.loaders.adventure import discover_adventures, load_adventure, load_manifest
from engine.loaders.rules import load_ruleset
from engine.models.scene import Exit
from tests.support import ContentTestCase


class TemplateTests(ContentTestCase):
    """The shipped template is what a new author starts from."""

    def test_template_loads_with_no_warnings(self):
        self.make_adventure("example")
        manifests, problems = discover_adventures()
        self.assertEqual(problems, [])
        self.assertEqual([m.slug for m in manifests], ["example"])

        adventure = load_adventure(manifests[0])
        self.assertEqual(adventure.warnings, [], "the template must validate cleanly")
        self.assertEqual(
            sorted(adventure.scenes), ["01-example-scene", "02-example-second-scene"]
        )
        self.assertIn("example-npc", adventure.npcs)
        self.assertIn("example-monster", adventure.monsters)

    def test_template_is_navigable_from_its_start_scene(self):
        self.make_adventure("example")
        manifests, _ = discover_adventures()
        adventure = load_adventure(manifests[0])
        start = adventure.scene(adventure.manifest.start_scene)
        self.assertIsNotNone(start)
        self.assertTrue(start.available_exits(set()), "start scene must lead somewhere")


class DiscoveryTests(ContentTestCase):
    def test_template_folder_is_never_offered_as_an_adventure(self):
        manifests, problems = discover_adventures()
        self.assertEqual(manifests, [])
        self.assertEqual(problems, [])

    def test_folder_without_a_manifest_is_skipped_not_fatal(self):
        self.make_adventure("good")
        (self.root / "adventures" / "wild-sheep-chase").mkdir()

        manifests, problems = discover_adventures()
        self.assertEqual([m.slug for m in manifests], ["good"])
        self.assertEqual(len(problems), 1)
        self.assertIn("wild-sheep-chase", problems[0])
        self.assertIn("no manifest.yaml", problems[0])

    def test_broken_manifest_is_skipped_with_a_readable_reason(self):
        self.make_adventure("good")
        broken = self.root / "adventures" / "broken"
        broken.mkdir()
        self.write(broken / "manifest.yaml", "title: Broken\nruleset: srd-5.1\n")

        manifests, problems = discover_adventures()
        self.assertEqual([m.slug for m in manifests], ["good"])
        self.assertIn("start_scene", problems[0])

    def test_unparseable_yaml_is_reported_not_raised(self):
        broken = self.root / "adventures" / "broken"
        broken.mkdir()
        self.write(broken / "manifest.yaml", "title: [unclosed\n")

        manifests, problems = discover_adventures()
        self.assertEqual(manifests, [])
        self.assertIn("not valid YAML", problems[0])


class ValidationTests(ContentTestCase):
    def _manifest(self, slug="example"):
        self.make_adventure(slug)
        return load_manifest(self.root / "adventures" / slug / "manifest.yaml", slug=slug)

    def test_missing_start_scene_is_fatal(self):
        manifest = self._manifest()
        manifest.start_scene = "no-such-scene"
        with self.assertRaises(ContentError) as caught:
            load_adventure(manifest)
        self.assertIn("no-such-scene", str(caught.exception))
        self.assertIn("Scenes found:", str(caught.exception))

    def test_dangling_exit_warns_but_still_loads(self):
        manifest = self._manifest()
        scene = manifest.directory / "scenes" / "02-example-second-scene.yaml"
        scene.write_text(
            scene.read_text() + "\nexits:\n  - to: nowhere\n    label: Off the map\n",
            encoding="utf-8",
        )
        adventure = load_adventure(manifest)
        self.assertEqual(len(adventure.warnings), 1)
        self.assertIn("nowhere", adventure.warnings[0])

    def test_unknown_field_warns_rather_than_failing(self):
        manifest = self._manifest()
        scene = manifest.directory / "scenes" / "02-example-second-scene.yaml"
        scene.write_text(scene.read_text() + "\nreadaloud: oops\n", encoding="utf-8")
        adventure = load_adventure(manifest)
        self.assertTrue(
            any("readaloud" in w for w in adventure.warnings), adventure.warnings
        )

    def test_missing_npc_reference_warns(self):
        manifest = self._manifest()
        (manifest.directory / "npcs" / "example-npc.yaml").unlink()
        adventure = load_adventure(manifest)
        self.assertTrue(any("example-npc" in w for w in adventure.warnings))

    def test_scene_id_must_match_its_filename(self):
        manifest = self._manifest()
        scene = manifest.directory / "scenes" / "02-example-second-scene.yaml"
        scene.write_text("id: something-else\n" + scene.read_text(), encoding="utf-8")
        with self.assertRaises(ContentError) as caught:
            load_adventure(manifest)
        self.assertIn("rename the file", str(caught.exception))

    def test_adventure_with_no_scenes_is_fatal(self):
        manifest = self._manifest()
        for path in (manifest.directory / "scenes").iterdir():
            path.unlink()
        with self.assertRaises(ContentError) as caught:
            load_adventure(manifest)
        self.assertIn("no scenes", str(caught.exception))


class ExitGatingTests(unittest.TestCase):
    """Gating is only 'flag set' and 'flag not set', AND-ed."""

    def test_ungated_exit_is_always_available(self):
        self.assertTrue(Exit(to="a", label="x").is_available(set()))

    def test_condition_requires_the_flag(self):
        exit_ = Exit(to="a", label="x", condition="found_it")
        self.assertFalse(exit_.is_available(set()))
        self.assertTrue(exit_.is_available({"found_it"}))

    def test_unless_hides_once_the_flag_is_set(self):
        exit_ = Exit(to="a", label="x", unless="door_barred")
        self.assertTrue(exit_.is_available(set()))
        self.assertFalse(exit_.is_available({"door_barred"}))

    def test_both_must_hold(self):
        exit_ = Exit(to="a", label="x", condition="has_key", unless="door_barred")
        self.assertFalse(exit_.is_available(set()))
        self.assertTrue(exit_.is_available({"has_key"}))
        self.assertFalse(exit_.is_available({"has_key", "door_barred"}))


_SHIPPED = None


def shipped_ruleset():
    """Parsed once — 374KB of spells and 515KB of bestiary per test was
    dominating the suite. Nothing here mutates it."""
    global _SHIPPED
    if _SHIPPED is None:
        _SHIPPED = load_ruleset("srd-5.1")
    return _SHIPPED


class RulesetTests(ContentTestCase):
    def test_dc_table_loads_from_the_declared_ruleset(self):
        ruleset = shipped_ruleset()
        self.assertEqual(
            [(tier.label, tier.dc) for tier in ruleset.dc_tiers],
            [
                ("Very easy", 5),
                ("Easy", 10),
                ("Medium", 15),
                ("Hard", 20),
                ("Very hard", 25),
                ("Nearly impossible", 30),
            ],
        )
        self.assertIn("proficiency bonus", ruleset.save_dc_formula)

    def test_conditions_are_loaded(self):
        ruleset = shipped_ruleset()
        self.assertEqual(len(ruleset.conditions), 15)
        self.assertEqual(ruleset.conditions["prone"].name, "Prone")
        self.assertTrue(ruleset.conditions["prone"].effects)

    def test_dying_rules_are_loaded(self):
        dying = shipped_ruleset().dying
        self.assertIsNotNone(dying)
        self.assertEqual(dying.death_save_dc, 10)
        self.assertEqual(dying.successes_to_stabilize, 3)
        self.assertEqual(dying.failures_to_die, 3)

    def test_the_shipped_ruleset_loads_without_warnings(self):
        self.assertEqual(shipped_ruleset().warnings, [])

    def test_missing_optional_files_warn_rather_than_fail(self):
        """A ruleset with only core mechanics still loads."""
        import os
        import shutil
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "rules" / "bare").mkdir(parents=True)
            shutil.copy(
                self.root / "rules" / "srd-5.1" / "core-mechanics.yaml",
                root / "rules" / "bare" / "core-mechanics.yaml",
            )
            previous = os.environ["DM_TOOL_ROOT"]
            os.environ["DM_TOOL_ROOT"] = str(root)
            try:
                ruleset = load_ruleset("bare")
            finally:
                os.environ["DM_TOOL_ROOT"] = previous
        self.assertTrue(ruleset.dc_tiers)
        for expected in ("conditions.yaml", "spells.yaml", "bestiary.yaml"):
            self.assertTrue(any(expected in w for w in ruleset.warnings), expected)

    def test_the_full_bestiary_loads(self):
        bestiary = shipped_ruleset().bestiary
        self.assertEqual(len(bestiary), 317)
        goblin = bestiary["goblin"]
        self.assertEqual(goblin.stat_block.ac, 15)
        self.assertEqual(goblin.stat_block.hp, 7)
        self.assertEqual(goblin.stat_block.cr, "1/4")
        self.assertEqual(goblin.stat_block.abilities["DEX"], 14)
        self.assertTrue(any(a.name == "Scimitar" for a in goblin.stat_block.actions))

    def test_acolyte_has_its_own_stats_not_the_archmages(self):
        """dnd-5e-srd-master gives Acolyte AC 12 / HP 99 / CR 12 — the
        Archmage's numbers, from the adjacent column of SRD page 395.
        The printed page says AC 10, HP 9 (2d8), CR 1/4."""
        bestiary = shipped_ruleset().bestiary
        acolyte = bestiary["acolyte"]
        self.assertEqual(acolyte.stat_block.ac, 10)
        self.assertEqual(acolyte.stat_block.hp, 9)
        self.assertEqual(acolyte.stat_block.cr, "1/4")
        archmage = bestiary["archmage"]
        self.assertEqual(archmage.stat_block.ac, 12)
        self.assertEqual(archmage.stat_block.hp, 99)
        self.assertEqual(archmage.stat_block.cr, "12")

    def test_legendary_creatures_keep_their_legendary_actions(self):
        bestiary = shipped_ruleset().bestiary
        self.assertTrue(bestiary["adult-red-dragon"].stat_block.legendary_actions)

    def test_spells_load_with_their_fields_intact(self):
        spells = shipped_ruleset().spells
        self.assertGreater(len(spells), 300)
        fire_bolt = spells["fire bolt"]
        self.assertEqual(fire_bolt["level"], 0)
        self.assertEqual(fire_bolt["school"], "Evocation")
        self.assertEqual(fire_bolt["range"], "120 feet")
        self.assertIn("1d10 fire damage", fire_bolt["description"])

    def test_the_conversions_phantom_entries_are_absent(self):
        """Precipitation/Temperature/Wind are Control Weather sub-tables the
        third-party conversion wrongly promoted to top-level spells."""
        spells = shipped_ruleset().spells
        for phantom in ("precipitation", "temperature", "wind"):
            self.assertNotIn(phantom, spells)
        self.assertIn("control weather", spells)

    def test_merged_field_entries_were_split_back_apart(self):
        """The conversion ran Range/Components into the casting time."""
        spells = shipped_ruleset().spells
        for name in ("beacon of hope", "dominate person", "blade barrier"):
            self.assertNotIn("**", spells[name]["casting_time"], name)
            self.assertTrue(spells[name]["range"], name)

    def test_both_rulesets_load(self):
        for ruleset_id in ("srd-5.1", "srd-5.2"):
            ruleset = load_ruleset(ruleset_id)
            self.assertEqual(ruleset.id, ruleset_id)
            self.assertEqual(len(ruleset.dc_tiers), 6)
            self.assertEqual(ruleset.warnings, [], ruleset_id)

    def test_srd_5_2_is_currently_a_copy_of_5_1(self):
        """Phase 4 seeds 5.2 from 5.1 deliberately. When 5.2 is really
        transcribed this will start failing, which is the point — it is
        the signal to update NOTES.md and the attribution."""
        first, second = load_ruleset("srd-5.1"), load_ruleset("srd-5.2")
        self.assertEqual(len(first.spells), len(second.spells))
        self.assertEqual(len(first.conditions), len(second.conditions))
        self.assertEqual(len(first.bestiary), len(second.bestiary))

    def test_the_manifest_ruleset_selects_the_folder_that_is_read(self):
        """The engine must genuinely read the declared ruleset's folder.

        Proven by changing the 5.2 copy and checking the change shows up,
        which a hardcoded path to 5.1 could not do.
        """
        rules = self.private_rules()
        target = rules / "srd-5.2" / "core-mechanics.yaml"
        target.write_text(
            target.read_text().replace("label: Nearly impossible",
                                       "label: Basically hopeless"),
            encoding="utf-8",
        )
        self.assertEqual(load_ruleset("srd-5.2").dc_tiers[-1].label, "Basically hopeless")
        self.assertEqual(load_ruleset("srd-5.1").dc_tiers[-1].label, "Nearly impossible")

    def test_an_adventure_declaring_5_2_gets_5_2(self):
        rules = self.private_rules()
        target = rules / "srd-5.2" / "core-mechanics.yaml"
        target.write_text(target.read_text().replace("dc: 30", "dc: 99"), encoding="utf-8")

        self.make_adventure("example")
        manifest_path = self.root / "adventures" / "example" / "manifest.yaml"
        manifest_path.write_text(
            manifest_path.read_text().replace("ruleset: srd-5.1", "ruleset: srd-5.2"),
            encoding="utf-8",
        )
        manifest = load_manifest(manifest_path, slug="example")
        self.assertEqual(manifest.ruleset, "srd-5.2")
        self.assertEqual(load_ruleset(manifest.ruleset).dc_tiers[-1].dc, 99)

    def test_unknown_ruleset_names_what_is_available(self):
        with self.assertRaises(ContentError) as caught:
            load_ruleset("srd-9.9")
        self.assertIn("srd-5.1", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
