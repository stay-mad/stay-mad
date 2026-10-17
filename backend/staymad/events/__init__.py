"""Event management, conflict detection, and snapshot synthesis package.

Authority: docs/architecture/B-data-model.md, docs/architecture/E-timeline-algorithm.md
"""

from backend.staymad.events.changes import detect_changeset
from backend.staymad.events.conflicts import ConflictDetector
from backend.staymad.events.manager import EventSynthesisManager

__all__ = [
    "ConflictDetector",
    "EventSynthesisManager",
    "detect_changeset",
]
