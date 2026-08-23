"""Headless smoke tests for the play UI.

Textual's run_test() drives the real app without a terminal, so these
cover the parts that actually change state: navigation, flags, and the
numbered menus.
"""

from __future__ import annotations

import asyncio
import unittest

from engine.app import DMToolApp, reflow
from engine.loaders.adventure import load_adventure, load_manifest
from engine.loaders.rules import load_ruleset
from engine.loaders.session import load_session, new_session
from tests.support import ContentTestCase

_RULESET = None


def shared_ruleset():
    """Parsing 319 spells per test dominated the suite's runtime.

    Nothing in the app mutates the ruleset, so one parse is reused.
    """
    global _RULESET
    if _RULESET is None:
        _RULESET = load_ruleset("srd-5.1")
    return _RULESET


class AppTests(ContentTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.make_adventure("example")
        manifest = load_manifest(
            self.root / "adventures" / "example" / "manifest.yaml", slug="example"
        )
        self.adventure = load_adventure(manifest)
        self.ruleset = shared_ruleset()
        self.session = new_session(manifest)

    def _app(self) -> DMToolApp:
        return DMToolApp(
            adventure=self.adventure, ruleset=self.ruleset, session=self.session
        )

    def _run(self, scenario):
        async def main():
            app = self._app()
            async with app.run_test() as pilot:
                await scenario(app, pilot)

        asyncio.run(main())

    def _text(self, app, selector: str) -> str:
        from textual.widgets import Static

        return str(app.query_one(selector, Static).content)

    def _message(self, app) -> str:
        return self._text(app, "#message")

    def test_opens_on_the_start_scene_with_the_dc_table_visible(self):
        async def scenario(app, pilot):
            self.assertEqual(app.scene.id, "01-example-scene")
            title = self._text(app, "#scene-title")
            self.assertIn("The Crossroads", title)
            dc_panel = self._text(app, "#dc-panel")
            self.assertIn("Nearly impossible", dc_panel)
            self.assertIn("30", dc_panel)

        self._run(scenario)

    def test_goto_menu_hides_gated_exits_until_the_flag_is_set(self):
        async def scenario(app, pilot):
            app.run_command("goto")
            labels = [label for label, _ in app.pending.options]
            self.assertEqual(len(labels), 2, labels)  # one exit + Other...
            self.assertTrue(labels[-1].startswith("Other"))

            app.run_command("flag set perrin_warned_them")
            app.run_command("goto")
            labels = [label for label, _ in app.pending.options]
            self.assertEqual(len(labels), 3, labels)  # gated exit now shows

        self._run(scenario)

    def test_choosing_a_number_moves_the_party_and_saves(self):
        async def scenario(app, pilot):
            app.run_command("goto")
            app.run_command("1")
            self.assertEqual(app.session.current_scene, "02-example-second-scene")
            self.assertIsNone(app.pending)
            reloaded = load_session(self.session.path)
            self.assertEqual(reloaded.current_scene, "02-example-second-scene")

        self._run(scenario)

    def test_other_opens_the_full_scene_list(self):
        async def scenario(app, pilot):
            app.run_command("goto")
            other = len(app.pending.options)
            app.run_command(str(other))
            self.assertEqual(len(app.pending.options), len(self.adventure.scenes))

        self._run(scenario)

    def test_scene_never_changes_without_an_explicit_command(self):
        async def scenario(app, pilot):
            app.run_command("flag set perrin_warned_them")
            app.run_command("flag list")
            app.run_command("help")
            self.assertEqual(app.session.current_scene, "01-example-scene")

        self._run(scenario)

    def test_flags_persist_to_disk_immediately(self):
        async def scenario(app, pilot):
            app.run_command("flag set perrin_warned_them")
            self.assertEqual(load_session(self.session.path).flags, {"perrin_warned_them"})
            app.run_command("flag unset perrin_warned_them")
            self.assertEqual(load_session(self.session.path).flags, set())

        self._run(scenario)

    def test_unknown_scene_is_refused_with_a_message(self):
        async def scenario(app, pilot):
            app.run_command("goto nowhere")
            self.assertEqual(app.session.current_scene, "01-example-scene")
            self.assertIn("no scene called", self._message(app))

        self._run(scenario)

    def test_unknown_command_does_not_crash(self):
        async def scenario(app, pilot):
            app.run_command("frobnicate the goat")
            self.assertIn("Unknown command", self._message(app))

        self._run(scenario)

    def test_scene_text_that_looks_like_markup_is_escaped(self):
        """Authored text must never be interpreted as Textual markup.

        Lowercase bracketed words are exactly what rich treats as style
        tags, so an unescaped "[red]" in read-aloud text would vanish
        from the screen mid-session.
        """
        scene = self.adventure.scenes["02-example-second-scene"]
        scene.read_aloud = "The door is painted [red] and marked [bold]."
        self.adventure.npcs["example-npc"].name = "[italic] the Bard"

        async def scenario(app, pilot):
            app.run_command("goto 02-example-second-scene")
            body = self._text(app, "#scene-body")
            self.assertIn(r"\[red]", body)
            self.assertIn(r"\[bold]", body)

            app.run_command("goto 01-example-scene")
            present = self._text(app, "#tracker")
            self.assertIn(r"\[italic]", present)

        self._run(scenario)


class ReflowTests(unittest.TestCase):
    """Authored line breaks must not survive into the rendered panel."""

    def test_soft_breaks_are_joined(self):
        self.assertEqual(
            reflow("The road forks\nbeside a signpost."),
            "The road forks beside a signpost.",
        )

    def test_blank_lines_keep_paragraphs_apart(self):
        self.assertEqual(reflow("One\ntwo.\n\nThree."), "One two.\n\nThree.")

    def test_runs_of_blank_lines_collapse_to_one(self):
        self.assertEqual(reflow("One.\n\n\n\nTwo."), "One.\n\nTwo.")

    def test_list_items_keep_their_own_lines(self):
        self.assertEqual(
            reflow("She wants:\n- a friend\n- the boar gone\n* peace and quiet"),
            "She wants:\n- a friend\n- the boar gone\n* peace and quiet",
        )

    def test_numbered_lists_keep_their_own_lines(self):
        self.assertEqual(reflow("Order:\n1. first\n2. second"), "Order:\n1. first\n2. second")

    def test_empty_text_is_handled(self):
        self.assertEqual(reflow("   \n\n  "), "")


if __name__ == "__main__":
    unittest.main()


class CombatCommandTests(ContentTestCase):
    """Combat driven the way the DM drives it: through typed commands."""

    def setUp(self) -> None:
        super().setUp()
        self.make_adventure("example")
        manifest = load_manifest(
            self.root / "adventures" / "example" / "manifest.yaml", slug="example"
        )
        self.adventure = load_adventure(manifest)
        self.ruleset = shared_ruleset()
        self.session = new_session(manifest)

    def _run(self, scenario, size=(100, 30)):
        from engine.app import DMToolApp

        async def main():
            app = DMToolApp(
                adventure=self.adventure,
                ruleset=self.ruleset,
                session=self.session,
                tips=[("A tip", "Some advice.")],
            )
            async with app.run_test(size=size) as pilot:
                await scenario(app, pilot)

        asyncio.run(main())

    def _text(self, app, selector):
        from textual.widgets import Static

        return str(app.query_one(selector, Static).content)

    def test_adding_a_known_monster_brings_its_hit_points(self):
        async def scenario(app, pilot):
            app.run_command("combat start")
            app.run_command("add Ill-Tempered Boar 12")
            boar = app.combat.find("Ill-Tempered Boar")
            self.assertEqual((boar.hp, boar.max_hp), (11, 11))
            self.assertFalse(boar.is_pc)
            self.assertEqual(boar.ref, "example-monster")

        self._run(scenario)

    def test_an_unknown_name_is_treated_as_a_player_character(self):
        async def scenario(app, pilot):
            app.run_command("combat start")
            app.run_command("add Thora 15")
            thora = app.combat.find("Thora")
            self.assertTrue(thora.is_pc)
            self.assertIsNone(thora.hp, "PC hit points live on the paper sheet")

        self._run(scenario)

    def test_the_tool_refuses_to_track_pc_hit_points(self):
        async def scenario(app, pilot):
            app.run_command("combat start")
            app.run_command("add Thora 15")
            app.run_command("hp Thora -4")
            self.assertIsNone(app.combat.find("Thora").hp)
            self.assertIn("character sheet", self._text(app, "#message"))

        self._run(scenario)

    def test_damage_and_healing_a_monster(self):
        async def scenario(app, pilot):
            app.run_command("combat start")
            app.run_command("add Ill-Tempered Boar 12")
            app.run_command("hp Ill-Tempered Boar -4")
            self.assertEqual(app.combat.find("Ill-Tempered Boar").hp, 7)
            app.run_command("hp Ill-Tempered Boar +2")
            self.assertEqual(app.combat.find("Ill-Tempered Boar").hp, 9)

        self._run(scenario)

    def test_healing_cannot_exceed_maximum(self):
        async def scenario(app, pilot):
            app.run_command("combat start")
            app.run_command("add Ill-Tempered Boar 12")
            app.run_command("hp Ill-Tempered Boar +50")
            self.assertEqual(app.combat.find("Ill-Tempered Boar").hp, 11)

        self._run(scenario)

    def test_a_monster_at_zero_dies_and_can_be_healed_back(self):
        async def scenario(app, pilot):
            app.run_command("combat start")
            app.run_command("add Ill-Tempered Boar 12")
            app.run_command("hp Ill-Tempered Boar -20")
            boar = app.combat.find("Ill-Tempered Boar")
            self.assertEqual(boar.hp, 0)
            self.assertTrue(boar.dead)
            app.run_command("hp Ill-Tempered Boar +5")
            self.assertFalse(boar.dead, "healing above 0 must clear the dead flag")

        self._run(scenario)

    def test_turn_order_and_round_counter(self):
        async def scenario(app, pilot):
            app.run_command("combat start")
            app.run_command("add Thora 20")
            app.run_command("add Ill-Tempered Boar 5")
            self.assertEqual(app.combat.current().name, "Thora")
            app.run_command("next")
            self.assertEqual(app.combat.current().name, "Ill-Tempered Boar")
            app.run_command("next")
            self.assertEqual(app.combat.current().name, "Thora")
            self.assertEqual(app.combat.round, 2)
            app.run_command("back")
            self.assertEqual(app.combat.round, 1)

        self._run(scenario)

    def test_combat_survives_a_reload(self):
        async def scenario(app, pilot):
            app.run_command("combat start")
            app.run_command("add Ill-Tempered Boar 12")
            app.run_command("hp Ill-Tempered Boar -4")
            app.run_command("next")

        self._run(scenario)
        reloaded = load_session(self.session.path)
        from engine.models.combat import Combat

        combat = Combat.from_dict(reloaded.combat)
        self.assertTrue(combat.active)
        self.assertEqual(combat.find("Ill-Tempered Boar").hp, 7)

    def test_ending_combat_clears_the_tracker(self):
        async def scenario(app, pilot):
            app.run_command("combat start")
            app.run_command("add Thora 15")
            app.run_command("combat end")
            self.assertFalse(app.combat.active)
            self.assertEqual(app.combat.combatants, [])

        self._run(scenario)


class DeathSaveTests(CombatCommandTests):
    """0 hit points, per SRD 5.1 — the thing a new DM forgets."""

    def _down_pc(self, app):
        app.run_command("combat start")
        app.run_command("add Thora 15")
        app.run_command("down Thora")
        return app.combat.find("Thora")

    def test_going_down_applies_unconscious_and_explains_the_rules(self):
        async def scenario(app, pilot):
            thora = self._down_pc(app)
            self.assertTrue(thora.down)
            self.assertIn("unconscious", thora.conditions)
            message = self._text(app, "#message")
            self.assertIn("10 or higher", message)
            self.assertIn("Medicine", message)

        self._run(scenario)

    def test_three_failures_kills(self):
        async def scenario(app, pilot):
            thora = self._down_pc(app)
            for _ in range(3):
                app.run_command("save Thora fail")
            self.assertTrue(thora.dead)
            self.assertFalse(thora.down)

        self._run(scenario)

    def test_three_successes_stabilises(self):
        async def scenario(app, pilot):
            thora = self._down_pc(app)
            for _ in range(3):
                app.run_command("save Thora ok")
            self.assertTrue(thora.stable)
            self.assertFalse(thora.down)
            self.assertFalse(thora.dead)

        self._run(scenario)

    def test_successes_and_failures_may_interleave(self):
        async def scenario(app, pilot):
            thora = self._down_pc(app)
            for result in ("ok", "fail", "ok", "fail", "ok"):
                app.run_command(f"save Thora {result}")
            self.assertTrue(thora.stable)

        self._run(scenario)

    def test_a_natural_one_counts_as_two_failures(self):
        async def scenario(app, pilot):
            thora = self._down_pc(app)
            app.run_command("save Thora nat1")
            self.assertEqual(thora.death_failures, 2)
            app.run_command("save Thora fail")
            self.assertTrue(thora.dead)

        self._run(scenario)

    def test_a_natural_twenty_puts_them_back_up(self):
        async def scenario(app, pilot):
            thora = self._down_pc(app)
            app.run_command("save Thora fail")
            app.run_command("save Thora nat20")
            self.assertFalse(thora.down)
            self.assertFalse(thora.dead)
            self.assertEqual(thora.death_failures, 0, "tallies reset on regaining hp")
            self.assertNotIn("unconscious", thora.conditions)

        self._run(scenario)

    def test_saves_are_refused_for_someone_who_is_not_down(self):
        async def scenario(app, pilot):
            app.run_command("combat start")
            app.run_command("add Thora 15")
            app.run_command("save Thora fail")
            self.assertEqual(app.combat.find("Thora").death_failures, 0)
            self.assertIn("isn't making death saves", self._text(app, "#message"))

        self._run(scenario)

    def test_the_turn_prompt_reminds_the_dm_a_save_is_due(self):
        async def scenario(app, pilot):
            self._down_pc(app)
            app.run_command("add Ill-Tempered Boar 1")
            app.run_command("next")
            app.run_command("next")
            self.assertIn("death saving throw", self._text(app, "#message").lower())

        self._run(scenario)


class ConditionTests(CombatCommandTests):
    def test_applying_a_condition_shows_what_it_does(self):
        async def scenario(app, pilot):
            app.run_command("combat start")
            app.run_command("add Thora 15")
            app.run_command("cond add Thora prone")
            self.assertIn("prone", app.combat.find("Thora").conditions)
            message = self._text(app, "#message")
            self.assertIn("crawl", message)
            self.assertIn("disadvantage on attack rolls", message)

        self._run(scenario)

    def test_conditions_work_for_names_containing_spaces(self):
        async def scenario(app, pilot):
            app.run_command("combat start")
            app.run_command("add Ill-Tempered Boar 12")
            app.run_command("cond add Ill-Tempered Boar restrained")
            self.assertIn("restrained", app.combat.find("Ill-Tempered Boar").conditions)

        self._run(scenario)

    def test_removing_a_condition(self):
        async def scenario(app, pilot):
            app.run_command("combat start")
            app.run_command("add Thora 15")
            app.run_command("cond add Thora poisoned")
            app.run_command("cond remove Thora poisoned")
            self.assertEqual(app.combat.find("Thora").conditions, set())

        self._run(scenario)

    def test_a_misspelled_condition_is_suggested_not_applied(self):
        async def scenario(app, pilot):
            app.run_command("combat start")
            app.run_command("add Thora 15")
            app.run_command("cond add Thora prne")
            self.assertEqual(app.combat.find("Thora").conditions, set())
            self.assertIn("Prone", self._text(app, "#message"))

        self._run(scenario)

    def test_every_srd_condition_is_listed(self):
        async def scenario(app, pilot):
            app.run_command("conditions")
            self.assertEqual(len(app.pending.options), 15)

        self._run(scenario)


class ReferenceTests(CombatCommandTests):
    def test_look_shows_a_stat_block(self):
        async def scenario(app, pilot):
            app.run_command("look Ill-Tempered Boar")
            message = self._text(app, "#message")
            self.assertIn("AC 11", message)
            self.assertIn("Charge", message)

        self._run(scenario)

    def test_look_finds_an_npc_by_id_as_well_as_name(self):
        async def scenario(app, pilot):
            app.run_command("look example-npc")
            self.assertIn("Perrin Ashdown", self._text(app, "#message"))

        self._run(scenario)

    def test_look_suggests_on_a_near_miss(self):
        async def scenario(app, pilot):
            app.run_command("look Perrin Ashdow")
            self.assertIn("Perrin", self._text(app, "#message"))

        self._run(scenario)

    def test_a_casters_known_spells_are_offered_as_a_menu(self):
        async def scenario(app, pilot):
            app.run_command("spell")
            labels = [label for label, _ in app.pending.options]
            self.assertTrue(any("Charm Person" in label for label in labels))

        self._run(scenario)

    def test_spell_lookup_finds_an_srd_spell(self):
        async def scenario(app, pilot):
            app.run_command("spell Fire Bolt")
            message = self._text(app, "#message")
            self.assertIn("Fire Bolt", message)
            self.assertIn("120 feet", message)

        self._run(scenario)

    def test_spell_lookup_suggests_on_a_typo_rather_than_guessing(self):
        async def scenario(app, pilot):
            app.run_command("spell firebalt")
            labels = [label for label, _ in (app.pending.options if app.pending else [])]
            self.assertTrue(any("Fireball" in l for l in labels), labels)

        self._run(scenario)

    def test_spell_lookup_degrades_gracefully_when_a_ruleset_has_no_spells(self):
        from engine.models.rules import Ruleset

        async def scenario(app, pilot):
            app.ruleset = Ruleset(id="srd-5.2", dc_tiers=app.ruleset.dc_tiers)
            app.run_command("spell Fireball")
            self.assertIn("isn't transcribed yet", self._text(app, "#message"))

        self._run(scenario)

    def test_dying_rules_are_available_on_demand(self):
        async def scenario(app, pilot):
            app.run_command("dying")
            self.assertIn("Medicine", self._text(app, "#message"))

        self._run(scenario)

    def test_tips_are_generic_and_selectable(self):
        async def scenario(app, pilot):
            app.run_command("tips")
            self.assertEqual(len(app.pending.options), 1)
            app.run_command("1")
            self.assertIn("Some advice", self._text(app, "#message"))

        self._run(scenario)


class LayoutTests(CombatCommandTests):
    """Checks the rendered screen, not just widget content.

    Widget content can be perfectly correct while the layout clips it —
    a combatant scrolled out of sight mid-fight is invisible to every
    other test in this file.
    """

    def _screen_text(self, app) -> str:
        # Private compositor API, but it is the only way to see what the
        # terminal would actually show.
        return "\n".join(strip.text for strip in app.screen._compositor.render_strips())

    NAMES = ("Thora", "Brakk", "Sela", "Wren", "Ill-Tempered Boar")

    def _busy_fight(self, app):
        app.run_command("combat start")
        for name, initiative in zip(self.NAMES, (20, 18, 15, 12, 9)):
            app.run_command(f"add {name} {initiative}")
        app.run_command("cond add Ill-Tempered Boar prone")
        app.run_command("down Wren")  # produces the longest message there is

    def test_a_full_party_and_monsters_all_fit_on_a_normal_terminal(self):
        async def scenario(app, pilot):
            self._busy_fight(app)
            await pilot.pause()
            screen = self._screen_text(app)
            for name in self.NAMES:
                self.assertIn(name, screen, f"{name} was pushed out of view")

        self._run(scenario, size=(100, 30))

    def test_on_a_cramped_terminal_the_tracker_scrolls_rather_than_vanishing(self):
        """80x24 cannot show five combatants, two condition lines, the DC
        table and a long message at once. What it must never do is show
        an empty tracker — the failure this test was written for."""

        async def scenario(app, pilot):
            self._busy_fight(app)
            await pilot.pause()
            screen = self._screen_text(app)
            visible = [name for name in self.NAMES if name in screen]
            self.assertGreaterEqual(len(visible), 4, f"only {visible} visible")
            self.assertIn("Thora", screen, "the combatant whose turn it is must show")

        self._run(scenario, size=(80, 24))

    def test_the_dc_table_is_always_visible(self):
        async def scenario(app, pilot):
            app.run_command("combat start")
            app.run_command("add Thora 20")
            app.run_command("down Thora")
            await pilot.pause()
            screen = self._screen_text(app)
            self.assertIn("Very easy", screen)
            self.assertIn("Nearly impossible", screen)

        self._run(scenario)


class SpellDisplayTests(CombatCommandTests):
    def test_a_cantrip_shows_its_level(self):
        """Level 0 is falsy — cantrips displayed with no level at all."""

        async def scenario(app, pilot):
            app.run_command("spell Fire Bolt")
            message = self._text(app, "#message")
            self.assertIn("Evocation cantrip", message)
            self.assertIn("120 feet", message)

        self._run(scenario)

    def test_a_levelled_spell_shows_its_level_and_school(self):
        async def scenario(app, pilot):
            app.run_command("spell Fireball")
            self.assertIn("3rd-level Evocation", self._text(app, "#message"))

        self._run(scenario)

    def test_a_ritual_is_marked_as_one(self):
        async def scenario(app, pilot):
            app.run_command("spell Find Familiar")
            self.assertIn("(ritual)", self._text(app, "#message"))

        self._run(scenario)
