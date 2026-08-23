"""Fuzzy name matching with an explicit confirmation step.

Shared by the in-session spell/monster lookup and, later, the setup
wizard's spell entry. The rule in both places is the same: never silently
accept a near-miss and never silently reject one. Return what was found
and let the caller confirm it with the user.

Uses stdlib difflib rather than a fuzzy-matching dependency — the
candidate lists are small, and the confirmation step catches anything the
scorer gets wrong.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field

#: How close a candidate must be before it is worth offering at all.
DEFAULT_CUTOFF = 0.6
DEFAULT_LIMIT = 5


def normalize(text: str) -> str:
    """Fold case, punctuation, and spacing so 'Cure Wounds' == 'cure-wounds'."""
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


@dataclass
class Match:
    """The result of looking a name up.

    `exact` is set only when the normalized forms agree, which is the case
    the caller can act on without asking. Otherwise `suggestions` holds
    the near-misses, best first, for the caller to confirm.
    """

    query: str
    exact: str | None = None
    suggestions: list[str] = field(default_factory=list)

    @property
    def found(self) -> bool:
        return self.exact is not None

    @property
    def has_suggestions(self) -> bool:
        return bool(self.suggestions)


def find(
    query: str,
    candidates: list[str],
    *,
    cutoff: float = DEFAULT_CUTOFF,
    limit: int = DEFAULT_LIMIT,
) -> Match:
    """Look `query` up among `candidates`, exactly then fuzzily."""
    normalized_query = normalize(query)
    if not normalized_query or not candidates:
        return Match(query=query)

    by_normal: dict[str, str] = {}
    for candidate in candidates:
        by_normal.setdefault(normalize(candidate), candidate)

    if normalized_query in by_normal:
        return Match(query=query, exact=by_normal[normalized_query])

    # Spacing is not a typo: "curewounds" means "Cure Wounds". Matched
    # separately from the scorer, which keeps spaces so multi-word names
    # still score sensibly.
    squashed: dict[str, str] = {}
    for normal, original in by_normal.items():
        squashed.setdefault(normal.replace(" ", ""), original)
    squashed_query = normalized_query.replace(" ", "")
    if squashed_query in squashed:
        return Match(query=query, exact=squashed[squashed_query])

    # A unique prefix is a near-certain hit, and much friendlier than
    # making the DM type "Cure Wounds" in full mid-combat.
    prefixed = [
        original
        for normal, original in by_normal.items()
        if normal.startswith(normalized_query)
    ]
    if len(prefixed) == 1:
        return Match(query=query, exact=prefixed[0])

    close = difflib.get_close_matches(
        normalized_query, list(by_normal), n=limit, cutoff=cutoff
    )
    suggestions = [by_normal[normal] for normal in close]
    for original in prefixed:
        if original not in suggestions:
            suggestions.append(original)
    return Match(query=query, suggestions=suggestions[:limit])
