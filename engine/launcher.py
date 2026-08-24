"""Entry point: pick an adventure, pick a session, then start play.

Running `dm-tool` with no arguments is the only thing a user has to type.
Everything from here is numbered choices. This is plain CLI on purpose —
it stays deliberately simple, and cannot be broken by changes to the
Textual play UI.
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

import yaml

from engine import paths
from engine.errors import ContentError
from engine.loaders.adventure import discover_adventures, load_adventure, load_manifest
from engine.loaders.rules import load_dm_tips, load_ruleset
from engine.loaders.session import list_sessions, load_session
from engine import setup_wizard
from engine.models.adventure import Manifest
from engine.models.rules import Ruleset
from engine.models.session import Session
from engine.prompts import ask_text, choose

CREATE_NEW = "Create new adventure..."
QUIT = "Quit"


def report_problems(problems: list[str]) -> None:
    if not problems:
        return
    print("\nSome folders were skipped:")
    for problem in problems:
        print(f"  ! {problem}")


def report_warnings(warnings: list[str], *, heading: str) -> None:
    if not warnings:
        return
    print(f"\n{heading}")
    for item in warnings:
        print(f"  ! {item}")


# --------------------------------------------------------------------------
# Creating a new adventure
# --------------------------------------------------------------------------


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "new-adventure"


def _yaml_line(field: str, value: str) -> str:
    """Render one `field: value` line, quoted if YAML needs it."""
    return yaml.safe_dump(
        {field: value}, default_flow_style=False, width=10_000, allow_unicode=True
    ).strip()


def stamp_manifest(manifest_path: Path, *, title: str, slug: str, ruleset: str) -> None:
    """Rewrite the identity lines of a copied template manifest.

    Done as a line edit rather than a YAML round-trip so the template's
    comments survive — they are the whole point of the template.
    """
    text = manifest_path.read_text(encoding="utf-8")
    for field, value in (("title", title), ("slug", slug), ("ruleset", ruleset)):
        pattern = re.compile(rf"^{field}:.*$", re.MULTILINE)
        replacement = _yaml_line(field, value)
        text, count = pattern.subn(lambda _match, r=replacement: r, text, count=1)
        if count == 0:
            text = text.rstrip("\n") + f"\n{replacement}\n"
    manifest_path.write_text(text, encoding="utf-8")


def available_rulesets() -> list[str]:
    rules_root = paths.rules_dir()
    if not rules_root.is_dir():
        return []
    return sorted(
        path.name
        for path in rules_root.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    )


def create_adventure() -> Manifest | None:
    """Copy the template into a new adventure folder and stamp it."""
    template = paths.template_dir()
    if not template.is_dir():
        print(f"\nCannot create an adventure: {template} is missing.")
        return None

    print("\nCreating a new adventure.")
    title = ask_text("Title")
    while True:
        slug = slugify(ask_text("Folder name", default=slugify(title)))
        target = paths.adventure_dir(slug)
        if paths.is_private(slug):
            print(f"'{slug}' starts with '_', which is reserved. Pick another.")
        elif target.exists():
            print(f"'{slug}' already exists. Pick another.")
        else:
            break

    rulesets = available_rulesets()
    default_ruleset = (
        paths.DEFAULT_RULESET if paths.DEFAULT_RULESET in rulesets else (rulesets or [""])[0]
    )
    if len(rulesets) > 1:
        index = choose(
            "Which ruleset?",
            [f"{name}{' (default)' if name == default_ruleset else ''}" for name in rulesets],
        )
        ruleset = rulesets[index]
    else:
        ruleset = default_ruleset

    shutil.copytree(template, target)
    stamp_manifest(target / "manifest.yaml", title=title, slug=slug, ruleset=ruleset)

    print(f"\nCreated adventures/{slug}/ from the template.")
    print("It contains an example scene, NPC, and monster to edit or delete.")
    return load_manifest(target / "manifest.yaml", slug=slug)


# --------------------------------------------------------------------------
# Sessions
# --------------------------------------------------------------------------


def choose_session(manifest: Manifest, ruleset: Ruleset) -> Session:
    """Resume an existing session, or run the setup wizard for a fresh one."""
    sessions = list_sessions(manifest.slug)
    if not sessions:
        return setup_wizard.run(manifest, ruleset)

    most_recent = sessions[0]
    print(f"\nFound an existing session for {manifest.title} ({most_recent.name}).")
    options = ["Resume this session", "Start a new session"]
    if len(sessions) > 1:
        options.append("Choose a different session")

    index = choose("What would you like to do?", options)
    if index == 0:
        return load_session(most_recent)
    if index == 1:
        return setup_wizard.run(manifest, ruleset)

    pick = choose("Which session?", [path.name for path in sessions])
    return load_session(sessions[pick])


# --------------------------------------------------------------------------
# Main flow
# --------------------------------------------------------------------------


def pick_adventure() -> Manifest | None:
    """Loop the picker until the user chooses something playable or quits."""
    while True:
        manifests, problems = discover_adventures()
        report_problems(problems)

        labels = [
            f"{manifest.title}" + (f" — {manifest.summary}" if manifest.summary else "")
            for manifest in manifests
        ]
        options = labels + [CREATE_NEW, QUIT]
        index = choose("Which adventure?", options)

        if index == len(options) - 1:
            return None
        if index == len(options) - 2:
            created = create_adventure()
            if created is None:
                continue
            play_now = choose(
                f"Start {created.title} now?", ["Yes", "No, back to the list"]
            )
            if play_now == 0:
                return created
            continue
        return manifests[index]


def main() -> int:
    print("dm-tool — D&D 5e one-shot assistant")

    try:
        manifest = pick_adventure()
        if manifest is None:
            print("\nGoodbye.")
            return 0

        adventure = load_adventure(manifest)
        report_warnings(
            adventure.warnings, heading=f"Content warnings for {adventure.title}:"
        )

        ruleset = load_ruleset(manifest.ruleset)
        report_warnings(ruleset.warnings, heading=f"Ruleset notes ({ruleset.id}):")
        tips = load_dm_tips()

        session = choose_session(manifest, ruleset)
        if session.current_scene not in adventure.scenes:
            print(
                f"\n! Session points at scene '{session.current_scene}', which no "
                f"longer exists. Starting from '{manifest.start_scene}' instead."
            )
            session.current_scene = manifest.start_scene

    except ContentError as error:
        print(f"\nContent error: {error.describe(relative_to=paths.project_root())}")
        return 1

    from engine.app import run_app

    run_app(adventure=adventure, ruleset=ruleset, session=session, tips=tips)
    print(f"\nSession saved to {session.path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
