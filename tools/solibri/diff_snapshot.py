"""Diff helper for Solibri RuleResult snapshots (Plan F Section 4 Task 12).

``diff(baseline, current)`` reports which rule violations are new in
``current`` and which violations vanished compared to ``baseline``. The
comparison is order-independent and treats every (rule_name, severity,
ifc_guid, message) tuple as one fingerprint.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

RuleResult = dict[str, str]


def _fingerprint(entry: RuleResult) -> tuple[str, str, str, str]:
    return (
        str(entry.get("rule_name", "")),
        str(entry.get("severity", "")),
        str(entry.get("ifc_guid", "")),
        str(entry.get("message", "")),
    )


@dataclass
class SnapshotDelta:
    """Result of comparing a fresh Solibri report against the baseline."""

    added: list[RuleResult] = field(default_factory=list)
    removed: list[RuleResult] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        return not self.added and not self.removed


def diff(
    baseline: Iterable[RuleResult],
    current: Iterable[RuleResult],
) -> SnapshotDelta:
    base_list = list(baseline)
    cur_list = list(current)
    base_keys = {_fingerprint(e) for e in base_list}
    cur_keys = {_fingerprint(e) for e in cur_list}

    added = [e for e in cur_list if _fingerprint(e) not in base_keys]
    removed = [e for e in base_list if _fingerprint(e) not in cur_keys]
    return SnapshotDelta(added=added, removed=removed)
