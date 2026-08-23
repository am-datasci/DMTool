"""Session handling and the 'Create new adventure...' path."""

from __future__ import annotations

import unittest

from engine.launcher import slugify, stamp_manifest
from engine.loaders.adventure import discover_adventures, load_manifest
from engine.loaders.session import (
    latest_session,
    list_sessions,
    load_session,
    new_session,
    save_session,
)
from tests.support import ContentTestCase


class SlugTests(unittest.TestCase):
    def test_titles_become_folder_names(self):
        self.assertEqual(slugify("A Wild Sheep Chase"), "a-wild-sheep-chase")
        self.assertEqual(slugify("  Trouble at Rockford's Mill! "), "trouble-at-rockford-s-mill")

    def test_unusable_titles_still_produce_a_folder_name(self):
        self.assertEqual(slugify("!!!"), "new-adventure")


class StampTests(ContentTestCase):
    def test_stamping_rewrites_identity_and_keeps_the_comments(self):
        target = self.make_adventure("copied")
        manifest_path = target / "manifest.yaml"
        original = manifest_path.read_text(encoding="utf-8")
        comment_count = original.count("#")

        stamp_manifest(
            manifest_path, title="Sheep Chase", slug="sheep-chase", ruleset="srd-5.2"
        )
        stamped = manifest_path.read_text(encoding="utf-8")

        self.assertEqual(stamped.count("#"), comment_count, "template comments must survive")
        manifest = load_manifest(manifest_path, slug="sheep-chase")
        self.assertEqual(manifest.title, "Sheep Chase")
        self.assertEqual(manifest.slug, "sheep-chase")
        self.assertEqual(manifest.ruleset, "srd-5.2")

    def test_awkward_titles_stay_valid_yaml(self):
        target = self.make_adventure("copied")
        manifest_path = target / "manifest.yaml"
        stamp_manifest(
            manifest_path, title="Trouble: the sequel", slug="copied", ruleset="srd-5.1"
        )
        manifest = load_manifest(manifest_path, slug="copied")
        self.assertEqual(manifest.title, "Trouble: the sequel")

    def test_a_stamped_copy_appears_in_the_picker(self):
        target = self.make_adventure("sheep-chase")
        stamp_manifest(
            target / "manifest.yaml",
            title="Sheep Chase",
            slug="sheep-chase",
            ruleset="srd-5.1",
        )
        manifests, problems = discover_adventures()
        self.assertEqual(problems, [])
        self.assertEqual([m.title for m in manifests], ["Sheep Chase"])


class SessionTests(ContentTestCase):
    def _manifest(self):
        self.make_adventure("example")
        return load_manifest(self.root / "adventures" / "example" / "manifest.yaml",
                             slug="example")

    def test_new_session_starts_at_the_opening_scene(self):
        manifest = self._manifest()
        session = new_session(manifest)
        self.assertEqual(session.current_scene, "01-example-scene")
        self.assertEqual(session.flags, set())
        self.assertEqual(session.characters, [], "the wizard fills these in later")
        self.assertTrue(session.path.is_file())

    def test_flags_and_scene_survive_a_save_and_reload(self):
        manifest = self._manifest()
        session = new_session(manifest)
        session.set_flag("perrin_warned_them")
        session.current_scene = "02-example-second-scene"
        save_session(session)

        reloaded = load_session(session.path)
        self.assertEqual(reloaded.flags, {"perrin_warned_them"})
        self.assertEqual(reloaded.current_scene, "02-example-second-scene")

    def test_setting_a_flag_twice_reports_no_change(self):
        manifest = self._manifest()
        session = new_session(manifest)
        self.assertTrue(session.set_flag("x"))
        self.assertFalse(session.set_flag("x"))
        self.assertTrue(session.unset_flag("x"))
        self.assertFalse(session.unset_flag("x"))

    def test_sessions_do_not_overwrite_each_other(self):
        manifest = self._manifest()
        first = new_session(manifest)
        second = new_session(manifest)
        self.assertNotEqual(first.path, second.path)
        self.assertEqual(len(list_sessions("example")), 2)

    def test_latest_session_is_offered_for_resume(self):
        manifest = self._manifest()
        new_session(manifest)
        second = new_session(manifest)
        import os, time

        now = time.time()
        os.utime(second.path, (now + 10, now + 10))
        self.assertEqual(latest_session("example"), second.path)


if __name__ == "__main__":
    unittest.main()
