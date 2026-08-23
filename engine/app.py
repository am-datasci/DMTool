"""The Textual play UI.

A persistent layout, not a scrolling log: scene text on the left, the
combat tracker (or who is present, out of combat) and the DC guideline
table on the right, one command line at the bottom. The tool changes
state only when the DM types a command — it never advances a scene,
rolls a die, or infers what the players did.

Menus are numbered lists printed into the message area and answered by
typing a number at the same command line. One input, no modal screens.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from rich.markup import escape
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Footer, Header, Input, Static

from engine import matching
from engine.loaders.session import save_session
from engine.models.adventure import Adventure
from engine.models.combat import Combat, Combatant
from engine.models.rules import Ruleset
from engine.models.scene import Scene
from engine.models.session import Session

OTHER_OPTION = "Other... (any scene in the adventure)"

HELP_TEXT = """\
Scene
  goto                     choose where to go next, from this scene's exits
  goto <scene>             go straight to a scene by its id
  scenes                   list every scene in the adventure
  flag set|unset <name>    set or clear a story flag (may open up exits)
  flag list                show which flags are set

Combat
  combat start|end         begin or end the encounter
  add <name> [initiative]  add a combatant (known creatures bring their hp)
  init <name> <n>          set someone's initiative
  next / back              move the turn marker
  hp <name> -5             apply damage or healing you have already rolled
  down <name>              they are at 0 hit points, start death saves
  save <name> ok|fail|nat20|nat1
  stable <name>            they have been stabilised
  up <name> [hp]           back on their feet

Reference
  cond add <name> <condition>      apply a condition and show what it does
  cond remove <name> <condition>
  cond <name>                      list a combatant's conditions
  conditions                       list every SRD condition
  look <name>                      stat block for an NPC or monster
  spell [name]                     spells known by casters here, or look one up
  tips                             general DM technique tips
  dying                            what happens at 0 hit points

  help / quit

When a numbered list is showing, just type the number.
"""

#: A line starting a list keeps its own break when text is reflowed.
_LIST_MARKER = re.compile(r"^\s*([-*+]\s|\d+[.)]\s)")


def reflow(text: str) -> str:
    """Undo an author's hard line breaks so the panel can wrap to its width.

    Authors write prose in YAML block scalars, which preserves exactly the
    line breaks they typed. Rendering those into a panel wraps them a
    second time and produces ragged half-lines — bad for anything, worse
    for read-aloud text the DM is speaking. So: a blank line starts a new
    paragraph, a list line keeps its break, and every other newline is
    treated as a soft break.
    """
    blocks: list[str] = []
    paragraph: list[str] = []

    def flush() -> None:
        if paragraph:
            blocks.append(" ".join(paragraph))
            paragraph.clear()

    for line in text.strip().splitlines():
        stripped = line.strip()
        if not stripped:
            flush()
            blocks.append("")
        elif _LIST_MARKER.match(line):
            flush()
            blocks.append(stripped)
        else:
            paragraph.append(stripped)
    flush()

    collapsed: list[str] = []
    for block in blocks:
        if not block and (not collapsed or not collapsed[-1]):
            continue
        collapsed.append(block)
    return "\n".join(collapsed).strip()


@dataclass
class PendingChoice:
    """A numbered list waiting for the DM to type a number.

    Each option carries an action as (kind, value) so the same mechanism
    serves scene navigation, spell lookup, and the tips list.
    """

    prompt: str
    options: list[tuple[str, tuple[str, str]]]


class DMToolApp(App):
    """Play UI for one adventure and one session."""

    CSS = """
    Screen { layout: vertical; }
    #body { height: 1fr; }
    #main { width: 2fr; border-right: solid $panel; padding: 0 1; }
    #sidebar { width: 1fr; padding: 0 1; }
    #scene-title { text-style: bold; color: $accent; padding: 1 0 0 0; }
    #scene-body { height: 1fr; }
    /* The tracker and the message area both scroll inside their own box.
       A long message must never be able to push a combatant off the
       bottom of the tracker — that is exactly when the DM needs it. */
    /* The DC panel is a fixed 8 rows (title + six tiers + its border) so
       the tracker can take 1fr and be guaranteed the rest. With the panel
       set to auto it won the sizing fight and squeezed the tracker to
       nothing on an 80x24 terminal. */
    #tracker-scroll { height: 1fr; min-height: 4; padding: 1 0 0 0; }
    #tracker { height: auto; }
    #dc-panel { height: 8; border-top: solid $panel; }
    #message-scroll { height: auto; max-height: 4; padding: 0 1; }
    #message { height: auto; color: $warning; }
    #command { dock: bottom; }
    """

    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
    ]

    def __init__(
        self,
        adventure: Adventure,
        ruleset: Ruleset,
        session: Session,
        tips: list[tuple[str, str]] | None = None,
    ) -> None:
        super().__init__()
        self.adventure = adventure
        self.ruleset = ruleset
        self.session = session
        self.tips = tips or []
        self.combat = Combat.from_dict(session.combat)
        self.pending: PendingChoice | None = None

    # -- layout ------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="body"):
            with Vertical(id="main"):
                yield Static(id="scene-title")
                yield VerticalScroll(Static(id="scene-body"))
            with Vertical(id="sidebar"):
                yield VerticalScroll(Static(id="tracker"), id="tracker-scroll")
                yield Static(id="dc-panel")
        yield VerticalScroll(Static(id="message"), id="message-scroll")
        yield Input(placeholder="Command (try 'help')", id="command")
        yield Footer()

    def on_mount(self) -> None:
        self.title = self.adventure.title
        self.sub_title = self.ruleset.id
        self._render_dc_panel()
        self._render_all()
        self.query_one("#command", Input).focus()
        if self.adventure.warnings:
            self._say(
                f"{len(self.adventure.warnings)} content warning(s) — see the "
                "launcher output above."
            )

    # -- state -------------------------------------------------------------

    @property
    def scene(self) -> Scene | None:
        return self.adventure.scene(self.session.current_scene)

    def _say(self, message: str) -> None:
        self.query_one("#message", Static).update(escape(message))

    def _markup(self, message: str) -> None:
        """Write a message that already contains intentional markup."""
        self.query_one("#message", Static).update(message)

    def _save(self) -> None:
        self.session.combat = self.combat.to_dict()
        save_session(self.session)

    def _render_all(self) -> None:
        self._render_scene()
        self._render_tracker()

    # -- rendering ---------------------------------------------------------

    def _render_dc_panel(self) -> None:
        """Always visible, so it is kept as short as it can usefully be —
        every row here is a row the combat tracker does not get."""
        lines = ["[bold]DC guidelines[/bold]"]
        for tier in self.ruleset.dc_tiers:
            lines.append(f"  {escape(tier.label):<18}[bold]{tier.dc}[/bold]")
        self.query_one("#dc-panel", Static).update("\n".join(lines))

    def _render_scene(self) -> None:
        scene = self.scene
        title_widget = self.query_one("#scene-title", Static)
        body_widget = self.query_one("#scene-body", Static)

        if scene is None:
            title_widget.update("[red]No scene loaded[/red]")
            body_widget.update(
                f"Session points at {escape(self.session.current_scene)}, "
                "which is not in this adventure. Use 'scenes' to pick one."
            )
            return

        title_widget.update(f"{escape(scene.title)}  [dim]({escape(scene.id)})[/dim]")

        sections: list[str] = []
        if scene.read_aloud:
            sections.append("[bold]Read aloud[/bold]\n" + escape(reflow(scene.read_aloud)))
        if scene.dm_notes:
            sections.append("[bold]DM notes[/bold]\n" + escape(reflow(scene.dm_notes)))
        if scene.checks:
            rows = []
            for check in scene.checks:
                rows.append(f"  [bold]DC {check.dc}[/bold]  {escape(check.name)}")
                rows.append(f"        [dim]{escape(check.ability)}[/dim]")
                if check.notes:
                    rows.append(f"        [dim]{escape(reflow(check.notes))}[/dim]")
            sections.append("[bold]Checks in this scene[/bold]\n" + "\n".join(rows))
        if scene.improv_notes:
            sections.append(
                "[bold]If they go off-script[/bold]\n" + escape(reflow(scene.improv_notes))
            )

        exits = scene.available_exits(self.session.flags)
        if exits:
            sections.append(
                "[bold]Exits[/bold]\n"
                + "\n".join(f"  - {escape(exit_.label)}" for exit_ in exits)
            )
        else:
            sections.append("[dim]No exits from here. 'goto' still offers every scene.[/dim]")

        body_widget.update("\n\n".join(sections))

    def _render_tracker(self) -> None:
        """The sidebar shows the fight during combat, and the room otherwise."""
        widget = self.query_one("#tracker", Static)
        widget.update(self._combat_text() if self.combat.active else self._present_text())

    def _combat_text(self) -> str:
        current = self.combat.current()
        lines = [f"[bold]Combat — round {self.combat.round}[/bold]"]
        if not self.combat.combatants:
            lines.append("[dim]  nobody added yet — 'add <name> <init>'[/dim]")
        for combatant in self.combat.order():
            marker = "[reverse]>[/reverse]" if combatant is current else " "
            initiative = (
                f"{combatant.initiative:>3}" if combatant.initiative is not None else "  ?"
            )
            status = combatant.status()
            colour = "red" if combatant.dead or combatant.down else "white"
            row = f"{marker}{initiative} [{colour}]{escape(combatant.name)}[/{colour}]"
            if status:
                row += f" [dim]{escape(status)}[/dim]"
            lines.append(row)
            if combatant.conditions:
                lines.append(
                    f"     [yellow]{escape(', '.join(sorted(combatant.conditions)))}[/yellow]"
                )
        if self.session.flags:
            lines += ["", "[bold]Flags set[/bold]"]
            lines += [f"  {escape(flag)}" for flag in sorted(self.session.flags)]
        return "\n".join(lines)

    def _present_text(self) -> str:
        scene = self.scene
        lines = ["[bold]Present[/bold]"]
        if scene is None or (not scene.npcs and not scene.monsters):
            lines.append("[dim]  nobody listed[/dim]")
        if scene is not None:
            for npc_id in scene.npcs:
                npc = self.adventure.npcs.get(npc_id)
                label = escape(npc.name) if npc else f"{escape(npc_id)} [red](missing)[/red]"
                lines.append(f"  {label}")
                if npc and npc.summary:
                    lines.append(f"    [dim]{escape(npc.summary)}[/dim]")
            for monster_id in scene.monsters:
                monster = self.adventure.monsters.get(monster_id)
                label = (
                    escape(monster.name)
                    if monster
                    else f"{escape(monster_id)} [red](missing)[/red]"
                )
                lines.append(f"  {label} [dim](monster)[/dim]")
        if self.session.flags:
            lines += ["", "[bold]Flags set[/bold]"]
            lines += [f"  {escape(flag)}" for flag in sorted(self.session.flags)]
        return "\n".join(lines)

    # -- command dispatch --------------------------------------------------

    def on_input_submitted(self, event: Input.Submitted) -> None:
        command = event.value.strip()
        event.input.value = ""
        if command:
            self.run_command(command)

    def run_command(self, command: str) -> None:
        if self.pending is not None and command.isdigit():
            self._resolve_choice(int(command))
            return

        word, _, rest = command.partition(" ")
        word = word.lower()
        rest = rest.strip()
        self.pending = None

        handlers = {
            "goto": self._cmd_goto,
            "scenes": lambda _: self._offer_all_scenes(),
            "flag": self._cmd_flag,
            "combat": self._cmd_combat,
            "add": self._cmd_add,
            "init": self._cmd_init,
            "next": lambda _: self._cmd_turn(1),
            "back": lambda _: self._cmd_turn(-1),
            "hp": self._cmd_hp,
            "down": self._cmd_down,
            "save": self._cmd_save_throw,
            "stable": self._cmd_stable,
            "up": self._cmd_up,
            "cond": self._cmd_cond,
            "conditions": lambda _: self._list_conditions(),
            "look": self._cmd_look,
            "spell": self._cmd_spell,
            "tips": lambda _: self._offer_tips(),
            "dying": lambda _: self._show_dying(),
            "help": lambda _: self._say(HELP_TEXT),
        }

        if word in {"quit", "exit", "q"}:
            self._save()
            self.exit()
            return
        handler = handlers.get(word)
        if handler is None:
            self._say(f"Unknown command: {command!r}. Type 'help' for the list.")
            return
        handler(rest)

    # -- numbered menus ----------------------------------------------------

    def _offer(self, prompt: str, options: list[tuple[str, tuple[str, str]]]) -> None:
        self.pending = PendingChoice(prompt=prompt, options=options)
        lines = [prompt]
        for index, (label, _) in enumerate(options, start=1):
            lines.append(f"  {index}. {label}")
        lines += ["", "Type a number, or anything else to cancel."]
        self._say("\n".join(lines))

    def _resolve_choice(self, number: int) -> None:
        pending = self.pending
        if pending is None:
            return
        if not 1 <= number <= len(pending.options):
            self._say(f"Please type a number from 1 to {len(pending.options)}.")
            return
        _, (kind, value) = pending.options[number - 1]
        self.pending = None

        if kind == "scene":
            self._enter_scene(value)
        elif kind == "all-scenes":
            self._offer_all_scenes()
        elif kind == "tip":
            self._show_tip(int(value))
        elif kind == "spell":
            self._show_spell(value)
        elif kind == "look":
            self._show_actor(value)
        elif kind == "condition":
            self._show_condition(value)

    # -- scene navigation --------------------------------------------------

    def _cmd_goto(self, target: str) -> None:
        if target:
            self._enter_scene(target)
            return
        scene = self.scene
        if scene is None:
            self._offer_all_scenes()
            return
        options: list[tuple[str, tuple[str, str]]] = [
            (exit_.label, ("scene", exit_.to))
            for exit_ in scene.available_exits(self.session.flags)
        ]
        options.append((OTHER_OPTION, ("all-scenes", "")))
        self._offer("Where to?", options)

    def _offer_all_scenes(self) -> None:
        self._offer(
            "Any scene:",
            [
                (f"{scene.title}  ({scene.id})", ("scene", scene.id))
                for scene in self.adventure.scenes_in_order()
            ],
        )

    def _enter_scene(self, scene_id: str) -> None:
        if scene_id not in self.adventure.scenes:
            self._say(
                f"There is no scene called {scene_id!r}. Type 'scenes' to see them all."
            )
            return
        self.session.current_scene = scene_id
        self._save()
        self._render_all()
        self._say(f"Now in: {self.adventure.scenes[scene_id].title}")

    def _cmd_flag(self, rest: str) -> None:
        action, _, name = rest.partition(" ")
        action = action.lower()
        name = name.strip()

        if action == "list" or not action:
            if self.session.flags:
                self._say("Flags set: " + ", ".join(sorted(self.session.flags)))
            else:
                self._say("No flags set.")
            return
        if action not in {"set", "unset"}:
            self._say("Usage: flag set <name> | flag unset <name> | flag list")
            return
        if not name:
            self._say(f"Which flag? Usage: flag {action} <name>")
            return

        changed = (
            self.session.set_flag(name) if action == "set" else self.session.unset_flag(name)
        )
        self._save()
        self._render_all()
        state = "set" if action == "set" else "cleared"
        self._say(
            f"Flag {name!r} {state}."
            if changed
            else f"Flag {name!r} was already {'set' if action == 'set' else 'clear'}."
        )

    # -- combat ------------------------------------------------------------

    def _require_combatant(self, name: str) -> Combatant | None:
        combatant = self.combat.find(name)
        if combatant is None:
            known = ", ".join(c.name for c in self.combat.combatants) or "nobody yet"
            self._say(f"No combatant matching {name!r}. In the fight: {known}.")
        return combatant

    def _cmd_combat(self, rest: str) -> None:
        action = rest.strip().lower()
        if action == "start":
            self.combat.active = True
            self.combat.round = 1
            self.combat.turn = 0
            self._save()
            self._render_tracker()
            self._say("Combat started. Add combatants with 'add <name> <initiative>'.")
        elif action == "end":
            self.combat = Combat()
            self._save()
            self._render_tracker()
            self._say("Combat ended and the tracker cleared.")
        else:
            self._say("Usage: combat start | combat end")

    def _lookup_actor(self, name: str):
        """Find an NPC or monster by id or name, for stat blocks and hp."""
        candidates: dict[str, object] = {}
        for actor in list(self.adventure.npcs.values()) + list(
            self.adventure.monsters.values()
        ):
            candidates[actor.name] = actor
            candidates[actor.id] = actor
        match = matching.find(name, list(candidates))
        if match.exact:
            return candidates[match.exact], match
        return None, match

    def _cmd_add(self, rest: str) -> None:
        if not rest:
            self._say("Usage: add <name> [initiative]")
            return
        parts = rest.rsplit(" ", 1)
        initiative = None
        name = rest
        if len(parts) == 2 and _is_int(parts[1]):
            name, initiative = parts[0].strip(), int(parts[1])

        if self.combat.find(name) is not None:
            self._say(f"{name!r} is already in the fight.")
            return

        actor, _ = self._lookup_actor(name)
        if actor is not None:
            hp = actor.stat_block.hp if actor.stat_block else None
            combatant = Combatant(
                name=actor.name, initiative=initiative, hp=hp, max_hp=hp, ref=actor.id
            )
            note = f"{actor.name} added with {hp} hp." if hp else f"{actor.name} added."
        else:
            combatant = Combatant(name=name, initiative=initiative, is_pc=True)
            note = (
                f"{name} added as a player character — hit points stay on their "
                "sheet. Use 'down <name>' when they drop."
            )

        self.combat.combatants.append(combatant)
        if not self.combat.active:
            self.combat.active = True
        self._save()
        self._render_tracker()
        self._say(note)

    def _cmd_init(self, rest: str) -> None:
        parts = rest.rsplit(" ", 1)
        if len(parts) != 2 or not _is_int(parts[1]):
            self._say("Usage: init <name> <number>")
            return
        combatant = self._require_combatant(parts[0])
        if combatant is None:
            return
        combatant.initiative = int(parts[1])
        self._save()
        self._render_tracker()
        self._say(f"{combatant.name} has initiative {combatant.initiative}.")

    def _cmd_turn(self, step: int) -> None:
        if not self.combat.active or not self.combat.combatants:
            self._say("No combat running. 'combat start' first.")
            return
        self.combat.advance(step)
        self._save()
        self._render_tracker()
        current = self.combat.current()
        if current is None:
            return
        message = f"Round {self.combat.round} — {current.name}'s turn."
        if current.down and not current.stable:
            message += (
                f"  They are at 0 hit points: death saving throw now "
                f"({current.death_successes} success(es), "
                f"{current.death_failures} failure(s) so far)."
            )
        self._say(message)

    def _cmd_hp(self, rest: str) -> None:
        parts = rest.rsplit(" ", 1)
        if len(parts) != 2 or not _is_signed_int(parts[1]):
            self._say("Usage: hp <name> -5   (or +3 to heal)")
            return
        combatant = self._require_combatant(parts[0])
        if combatant is None:
            return
        delta = int(parts[1])

        if combatant.is_pc:
            self._say(
                f"{combatant.name}'s hit points live on their character sheet — the "
                "tool doesn't track them. Use 'down <name>' when they reach 0."
            )
            return
        if combatant.max_hp is None:
            self._say(f"{combatant.name} has no hit points recorded to adjust.")
            return

        before = combatant.hp or 0
        combatant.hp = max(0, min(combatant.max_hp, before + delta))
        if combatant.hp > 0:
            combatant.dead = False

        if combatant.hp == 0 and not combatant.dead:
            combatant.dead = True
            self._save()
            self._render_tracker()
            self._say(  # noqa: E501 - message is deliberately explicit

                f"{combatant.name} drops to 0 and dies. (Most GMs have monsters die "
                "outright; if this one should make death saves instead, use "
                f"'down {combatant.name}'.)"
            )
        else:
            self._save()
            self._render_tracker()
            self._say(f"{combatant.name}: {before} -> {combatant.hp} hp.")

    def _cmd_down(self, rest: str) -> None:
        combatant = self._require_combatant(rest)
        if combatant is None:
            return
        combatant.down = True
        combatant.dead = False
        combatant.stable = False
        combatant.conditions.add("unconscious")
        if combatant.tracks_hp:
            combatant.hp = 0
        self._save()
        self._render_tracker()

        dying = self.ruleset.dying
        lines = [f"{combatant.name} is at 0 hit points and unconscious."]
        if dying is not None:
            lines.append(
                f"Death saving throw at the start of each of their turns: d20, "
                f"{dying.death_save_dc} or higher succeeds. "
                f"{dying.successes_to_stabilize} successes and they stabilise; "
                f"{dying.failures_to_die} failures and they die."
            )
            if dying.stabilize_check:
                lines.append(f"Another character can stabilise them: {dying.stabilize_check}")
            lines.append(f"Record each roll with 'save {combatant.name} ok|fail'.")
        self._say("\n".join(lines))

    def _cmd_save_throw(self, rest: str) -> None:
        parts = rest.rsplit(" ", 1)
        if len(parts) != 2:
            self._say("Usage: save <name> ok | fail | nat20 | nat1")
            return
        combatant = self._require_combatant(parts[0])
        if combatant is None:
            return
        result = parts[1].lower()
        dying = self.ruleset.dying
        successes_needed = dying.successes_to_stabilize if dying else 3
        failures_allowed = dying.failures_to_die if dying else 3

        if not combatant.down:
            self._say(f"{combatant.name} isn't making death saves. Use 'down' first.")
            return

        if result in {"ok", "success", "pass"}:
            combatant.death_successes += 1
        elif result in {"fail", "failure"}:
            combatant.death_failures += 1
        elif result == "nat1":
            combatant.death_failures += 2
        elif result == "nat20":
            combatant.reset_death_saves()
            combatant.conditions.discard("unconscious")
            if combatant.tracks_hp:
                combatant.hp = 1
            self._save()
            self._render_tracker()
            self._say(f"Natural 20 — {combatant.name} regains 1 hit point and is up.")
            return
        else:
            self._say("Usage: save <name> ok | fail | nat20 | nat1")
            return

        if combatant.death_failures >= failures_allowed:
            combatant.dead = True
            combatant.down = False
            message = f"That is {failures_allowed} failures — {combatant.name} dies."
        elif combatant.death_successes >= successes_needed:
            combatant.stable = True
            combatant.down = False
            message = (
                f"That is {successes_needed} successes — {combatant.name} is stable, "
                "still unconscious, and regains 1 hit point after 1d4 hours."
            )
        else:
            message = (
                f"{combatant.name}: {combatant.death_successes} success(es), "
                f"{combatant.death_failures} failure(s)."
            )
        self._save()
        self._render_tracker()
        self._say(message)

    def _cmd_stable(self, rest: str) -> None:
        combatant = self._require_combatant(rest)
        if combatant is None:
            return
        combatant.down = False
        combatant.stable = True
        combatant.death_successes = 0
        combatant.death_failures = 0
        self._save()
        self._render_tracker()
        self._say(
            f"{combatant.name} is stable at 0 hit points — still unconscious, no "
            "more death saves, and back to 1 hit point after 1d4 hours."
        )

    def _cmd_up(self, rest: str) -> None:
        parts = rest.rsplit(" ", 1)
        hp = None
        name = rest
        if len(parts) == 2 and _is_int(parts[1]):
            name, hp = parts[0].strip(), int(parts[1])
        combatant = self._require_combatant(name)
        if combatant is None:
            return
        combatant.reset_death_saves()
        combatant.dead = False
        combatant.conditions.discard("unconscious")
        if combatant.tracks_hp:
            combatant.hp = hp if hp is not None else max(1, combatant.hp or 1)
        self._save()
        self._render_tracker()
        suffix = f" at {combatant.hp} hp" if combatant.tracks_hp else ""
        self._say(f"{combatant.name} is back on their feet{suffix}.")

    # -- reference ---------------------------------------------------------

    def _cmd_cond(self, rest: str) -> None:
        action, _, remainder = rest.partition(" ")
        action = action.lower()

        if action not in {"add", "remove"}:
            # `cond <name>` lists what that combatant has.
            combatant = self._require_combatant(rest)
            if combatant is None:
                return
            if combatant.conditions:
                self._say(
                    f"{combatant.name}: " + ", ".join(sorted(combatant.conditions))
                )
            else:
                self._say(f"{combatant.name} has no conditions.")
            return

        # The condition is the last word; everything before it is the name,
        # so combatants with spaces in their names still work.
        parts = remainder.rsplit(" ", 1)
        if len(parts) != 2:
            self._say(f"Usage: cond {action} <name> <condition>")
            return
        combatant = self._require_combatant(parts[0])
        if combatant is None:
            return

        match = matching.find(parts[1], [c.name for c in self.ruleset.conditions.values()])
        if not match.exact:
            if match.has_suggestions:
                self._say(
                    f"No condition called {parts[1]!r}. Did you mean: "
                    + ", ".join(match.suggestions)
                    + "?"
                )
            else:
                self._say(f"No condition called {parts[1]!r}. Type 'conditions' to list them.")
            return

        condition = next(
            c for c in self.ruleset.conditions.values() if c.name == match.exact
        )
        if action == "add":
            combatant.conditions.add(condition.id)
            self._save()
            self._render_tracker()
            self._show_condition(condition.id, prefix=f"{combatant.name} is now ")
        else:
            combatant.conditions.discard(condition.id)
            self._save()
            self._render_tracker()
            self._say(f"{combatant.name} is no longer {condition.name.lower()}.")

    def _show_condition(self, condition_id: str, *, prefix: str = "") -> None:
        condition = self.ruleset.conditions.get(condition_id)
        if condition is None:
            self._say(f"No condition {condition_id!r} in {self.ruleset.id}.")
            return
        lines = [f"{prefix}[bold]{escape(condition.name)}[/bold]"]
        lines += [f"  - {escape(reflow(effect))}" for effect in condition.effects]
        self._markup("\n".join(lines))

    def _list_conditions(self) -> None:
        if not self.ruleset.conditions:
            self._say(f"No conditions loaded for {self.ruleset.id}.")
            return
        self._offer(
            "Conditions:",
            [
                (condition.name, ("condition", condition.id))
                for condition in sorted(
                    self.ruleset.conditions.values(), key=lambda c: c.name
                )
            ],
        )

    def _show_dying(self) -> None:
        dying = self.ruleset.dying
        if dying is None:
            self._say(f"No dying rules loaded for {self.ruleset.id}.")
            return
        lines = ["[bold]At 0 hit points[/bold]"]
        lines += [f"  - {escape(reflow(note))}" for note in dying.notes]
        if dying.stabilize_check:
            lines.append(f"  - {escape(reflow(dying.stabilize_check))}")
        self._markup("\n".join(lines))

    def _cmd_look(self, rest: str) -> None:
        if not rest:
            here = self._actors_here()
            if not here:
                self._say("Nobody is listed in this scene. Try 'look <name>'.")
                return
            self._offer(
                "Look at:",
                [(actor.name, ("look", actor.id)) for actor in here],
            )
            return
        actor, match = self._lookup_actor(rest)
        if actor is None:
            if match.has_suggestions:
                self._say(
                    f"No NPC or monster called {rest!r}. Did you mean: "
                    + ", ".join(match.suggestions)
                    + "?"
                )
            else:
                self._say(f"No NPC or monster called {rest!r} in this adventure.")
            return
        self._show_actor(actor.id)

    def _actors_here(self) -> list:
        scene = self.scene
        if scene is None:
            return []
        actors = [self.adventure.npcs[i] for i in scene.npcs if i in self.adventure.npcs]
        actors += [
            self.adventure.monsters[i]
            for i in scene.monsters
            if i in self.adventure.monsters
        ]
        return actors

    def _show_actor(self, actor_id: str) -> None:
        actor = self.adventure.npcs.get(actor_id) or self.adventure.monsters.get(actor_id)
        if actor is None:
            self._say(f"No NPC or monster with id {actor_id!r}.")
            return

        lines = [f"[bold]{escape(actor.name)}[/bold]"]
        if actor.summary:
            lines.append(escape(reflow(actor.summary)))

        for label, value in (
            ("Wants", getattr(actor, "motivation", None)),
            ("Attitude", getattr(actor, "attitude", None)),
            ("In a fight", actor.combat_behavior),
        ):
            if value:
                lines.append(f"[dim]{label}:[/dim] {escape(reflow(value))}")

        block = actor.stat_block
        if block is not None:
            header = []
            if block.ac is not None:
                header.append(f"AC {block.ac}")
            if block.hp is not None:
                header.append(f"HP {block.hp}" + (f" ({block.hit_dice})" if block.hit_dice else ""))
            if block.speed:
                header.append(f"Speed {block.speed}")
            if block.cr:
                header.append(f"CR {block.cr}")
            if header:
                lines.append("  " + escape("  ".join(header)))
            if block.abilities:
                abilities = "  ".join(
                    f"{name} {score}" for name, score in block.abilities.items()
                )
                lines.append("  " + escape(abilities))
            for group_name, group in (
                ("Traits", block.traits),
                ("Actions", block.actions),
                ("Reactions", block.reactions),
            ):
                if not group:
                    continue
                lines.append(f"[bold]{group_name}[/bold]")
                for trait in group:
                    lines.append(f"  [bold]{escape(trait.name)}.[/bold] {escape(reflow(trait.text))}")

        casting = actor.spellcasting
        if casting is not None:
            bits = []
            if casting.save_dc is not None:
                bits.append(f"save DC {casting.save_dc}")
            if casting.save_dc_formula:
                bits.append(f"({casting.save_dc_formula})")
            if casting.attack_bonus is not None:
                bits.append(f"attack +{casting.attack_bonus}")
            lines.append("[bold]Spellcasting[/bold] " + escape(" ".join(bits)))
            if casting.known:
                lines.append("  " + escape(", ".join(casting.known)))
                lines.append("[dim]  'spell' lists these as a numbered menu.[/dim]")

        self._markup("\n".join(lines))

    def _cmd_spell(self, rest: str) -> None:
        if rest:
            self._lookup_spell(rest)
            return
        options: list[tuple[str, tuple[str, str]]] = []
        for actor in self._actors_here():
            if actor.spellcasting and actor.spellcasting.known:
                for name in actor.spellcasting.known:
                    options.append((f"{name}  [{actor.name}]", ("spell", name)))
        if not options:
            self._say(
                "No casters with a known-spell list in this scene. "
                "Use 'spell <name>' to look one up."
            )
            return
        self._offer("Spells known by casters here:", options)

    def _lookup_spell(self, query: str) -> None:
        if not self.ruleset.spells:
            self._say(
                f"The SRD spell reference isn't transcribed yet "
                f"(rules/{self.ruleset.id}/spells.yaml), so full spell text isn't "
                "available. Casters' known-spell lists and save DCs still work — "
                "type 'spell' with no name."
            )
            return
        match = matching.find(query, [entry["name"] for entry in self.ruleset.spells.values()])
        if match.exact:
            self._show_spell(match.exact)
        elif match.has_suggestions:
            self._offer(
                f"No exact match for {query!r}. Did you mean:",
                [(name, ("spell", name)) for name in match.suggestions],
            )
        else:
            self._say(f"No spell matching {query!r} in {self.ruleset.id}.")

    def _show_spell(self, name: str) -> None:
        entry = self.ruleset.spells.get(name.lower())
        if entry is None:
            self._say(
                f"[bold]{escape(name)}[/bold] — no SRD text loaded yet. The caster's "
                "save DC is on their stat block ('look <name>')."
            )
            return
        lines = [f"[bold]{escape(str(entry.get('name', name)))}[/bold]"]

        # Level 0 is a cantrip — and falsy, so it needs handling of its own
        # or every cantrip would display with no level at all.
        level, school = entry.get("level"), entry.get("school", "")
        if level == 0:
            descriptor = f"{school} cantrip".strip()
        elif level is not None:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(level, "th")
            descriptor = f"{level}{suffix}-level {school}".strip()
        else:
            descriptor = school
        if entry.get("ritual"):
            descriptor += " (ritual)"
        if descriptor:
            lines.append(f"[dim]{escape(descriptor)}[/dim]")

        for key in ("casting_time", "range", "components", "duration"):
            if entry.get(key):
                label = key.replace("_", " ").title()
                lines.append(f"[dim]{label}:[/dim] {escape(str(entry[key]))}")
        if entry.get("description"):
            lines.append(escape(reflow(str(entry["description"]))))
        self._markup("\n".join(lines))

    # -- tips --------------------------------------------------------------

    def _offer_tips(self) -> None:
        if not self.tips:
            self._say("No DM tips loaded (rules/dm-tips.yaml).")
            return
        self._offer(
            "DM technique tips:",
            [(title, ("tip", str(index))) for index, (title, _) in enumerate(self.tips)],
        )

    def _show_tip(self, index: int) -> None:
        if not 0 <= index < len(self.tips):
            return
        title, text = self.tips[index]
        self._markup(f"[bold]{escape(title)}[/bold]\n{escape(reflow(text))}")


def _is_int(text: str) -> bool:
    return bool(re.fullmatch(r"-?\d+", text.strip()))


def _is_signed_int(text: str) -> bool:
    return bool(re.fullmatch(r"[+-]?\d+", text.strip()))


def run_app(
    *,
    adventure: Adventure,
    ruleset: Ruleset,
    session: Session,
    tips: list[tuple[str, str]] | None = None,
) -> None:
    DMToolApp(
        adventure=adventure, ruleset=ruleset, session=session, tips=tips
    ).run()
