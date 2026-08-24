"""Plain-CLI prompting, shared by the launcher and the setup wizard.

These live here rather than in `launcher.py` because the launcher has to
call the wizard, and the wizard needs the same prompts — importing back
the other way would be circular.

Everything reads from stdin via `input()`, so a scripted stdin drives the
whole flow in tests. Ctrl-C and end-of-input exit cleanly rather than
raising into a traceback: this is the pre-session flow, and a stack trace
in front of a table of waiting players is a bad look.
"""

from __future__ import annotations


def prompt(message: str) -> str:
    try:
        return input(message).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        raise SystemExit(0) from None


def choose(title: str, options: list[str]) -> int:
    """Show a numbered menu and return the chosen index."""
    print(f"\n{title}")
    for index, option in enumerate(options, start=1):
        print(f"  {index}. {option}")
    while True:
        answer = prompt("\nChoice: ")
        if answer.isdigit() and 1 <= int(answer) <= len(options):
            return int(answer) - 1
        print(f"Please enter a number from 1 to {len(options)}.")


def ask_text(message: str, *, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    while True:
        answer = prompt(f"{message}{suffix}: ")
        if answer:
            return answer
        if default is not None:
            return default
        print("Please enter a value.")


def ask_optional_text(message: str) -> str | None:
    """Like ask_text, but an empty answer means 'not recorded'."""
    return prompt(f"{message} (optional, press enter to skip): ") or None


def ask_int(
    message: str,
    *,
    default: int | None = None,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    suffix = f" [{default}]" if default is not None else ""
    while True:
        answer = prompt(f"{message}{suffix}: ")
        if not answer and default is not None:
            return default
        try:
            value = int(answer)
        except ValueError:
            print("Please enter a whole number.")
            continue
        if minimum is not None and value < minimum:
            print(f"Please enter {minimum} or more.")
        elif maximum is not None and value > maximum:
            print(f"Please enter {maximum} or less.")
        else:
            return value


def ask_yes_no(message: str, *, default: bool | None = None) -> bool:
    hint = {True: " [Y/n]", False: " [y/N]", None: " [y/n]"}[default]
    while True:
        answer = prompt(f"{message}{hint}: ").lower()
        if not answer and default is not None:
            return default
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        print("Please answer y or n.")
