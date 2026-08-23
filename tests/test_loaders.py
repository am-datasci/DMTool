"""Loading and validating adventure content."""

from __future__ import annotations

import unittest

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


class RulesetTests(ContentTestCase):
    def test_dc_table_loads_from_the_declared_ruleset(self):
        ruleset = load_ruleset("srd-5.1")
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
        ruleset = load_ruleset("srd-5.1")
        self.assertEqual(len(ruleset.conditions), 15)
        self.assertEqual(ruleset.conditions["prone"].name, "Prone")
        self.assertTrue(ruleset.conditions["prone"].effects)

    def test_dying_rules_are_loaded(self):
        dying = load_ruleset("srd-5.1").dying
        self.assertIsNotNone(dying)
        self.assertEqual(dying.death_save_dc, 10)
        self.assertEqual(dying.successes_to_stabilize, 3)
        self.assertEqual(dying.failures_to_die, 3)

    def test_missing_phase_3_files_warn_rather_than_fail(self):
        ruleset = load_ruleset("srd-5.1")
        self.assertTrue(any("spells.yaml" in w for w in ruleset.warnings))
        self.assertTrue(any("bestiary.yaml" in w for w in ruleset.warnings))

    def test_unknown_ruleset_names_what_is_available(self):
        with self.assertRaises(ContentError) as caught:
            load_ruleset("srd-9.9")
        self.assertIn("srd-5.1", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
