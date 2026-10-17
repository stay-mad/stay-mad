"""Conflict detection and resolution module.

Authority: docs/architecture/B-data-model.md §2.12, docs/architecture/E-timeline-algorithm.md §53-E Step 4,
Addendum §5, decisions.md Conflict #4
"""

from __future__ import annotations

import re
import uuid
from typing import TYPE_CHECKING

from backend.staymad.db.models.conflict import Conflict

if TYPE_CHECKING:
    from backend.staymad.db.models.claim import Claim


class ConflictDetector:
    """Detects factual conflicts among claims in an event and resolves them via official updates."""

    @staticmethod
    def detect_conflicts(
        claims: list[Claim],
        event_id: uuid.UUID,
        snapshot_id: uuid.UUID,
    ) -> list[Conflict]:
        """Detect factual contradictions between claims within an event.

        Focuses on:
        1. Numerical contradictions on the same unit/scope (e.g. 5 vs 7 kecamatan).
        2. Status contradictions (e.g. Level III vs Level IV).
        """
        conflicts: list[Conflict] = []
        seen_pairs: set[tuple[str, str]] = set()

        for i, c1 in enumerate(claims):
            for c2 in claims[i + 1 :]:
                pair_key = tuple(sorted([str(c1.id), str(c2.id)]))
                if pair_key in seen_pairs:
                    continue

                # 1. Check numerical conflicts on the same unit
                if (
                    c1.numeric_value is not None
                    and c2.numeric_value is not None
                    and c1.numeric_value != c2.numeric_value
                ):
                    # Check unit match
                    unit1 = (c1.unit or "").lower()
                    unit2 = (c2.unit or "").lower()
                    if unit1 and unit2 and unit1 == unit2:
                        seen_pairs.add(pair_key)
                        conflicts.append(
                            Conflict(
                                id=uuid.uuid4(),
                                event_id=event_id,
                                snapshot_id=snapshot_id,
                                field_name=f"affected_{unit1}_count",
                                claim_a_id=c1.id,
                                claim_b_id=c2.id,
                                value_a=str(
                                    int(c1.numeric_value)
                                    if c1.numeric_value.is_integer()
                                    else c1.numeric_value
                                ),
                                value_b=str(
                                    int(c2.numeric_value)
                                    if c2.numeric_value.is_integer()
                                    else c2.numeric_value
                                ),
                                context=f"Perbedaan data jumlah {unit1} antara klaim sumber ({c1.numeric_value} vs {c2.numeric_value})",
                                resolved=False,
                            )
                        )
                        continue

                # 2. Check regex pattern for numerical claims in text (fallback if numeric_value was missed)
                id_words = {
                    "satu": 1,
                    "dua": 2,
                    "tiga": 3,
                    "empat": 4,
                    "lima": 5,
                    "enam": 6,
                    "tujuh": 7,
                    "delapan": 8,
                    "sembilan": 9,
                    "sepuluh": 10,
                }
                num_unit_pat = r"(?:(\d+)|(satu|dua|tiga|empat|lima|enam|tujuh|delapan|sembilan|sepuluh))\s*(kecamatan|desa|kelurahan|jiwa|meter|posko)"
                m1 = re.search(num_unit_pat, c1.claim_text, re.IGNORECASE)
                m2 = re.search(num_unit_pat, c2.claim_text, re.IGNORECASE)
                if m1 and m2 and m1.group(3).lower() == m2.group(3).lower():
                    v1 = (
                        int(m1.group(1))
                        if m1.group(1)
                        else id_words.get(m1.group(2).lower(), 0)
                    )
                    v2 = (
                        int(m2.group(1))
                        if m2.group(1)
                        else id_words.get(m2.group(2).lower(), 0)
                    )
                    unit_name = m1.group(3).lower()
                    if v1 != v2 and v1 > 0 and v2 > 0:
                        seen_pairs.add(pair_key)
                        conflicts.append(
                            Conflict(
                                id=uuid.uuid4(),
                                event_id=event_id,
                                snapshot_id=snapshot_id,
                                field_name=f"affected_{unit_name}_count",
                                claim_a_id=c1.id,
                                claim_b_id=c2.id,
                                value_a=str(v1),
                                value_b=str(v2),
                                context=f"Perbedaan data jumlah {unit_name} dalam laporan ({v1} vs {v2})",
                                resolved=False,
                            )
                        )
                        continue

                # 3. Check status contradictions (e.g. Level III Siaga vs Level IV Awas)
                status_pat = r"(level\s*(?:iii|iv|1|2|3|4)|siaga\s*[123]|awas|waspada)"
                s1 = re.search(status_pat, c1.claim_text, re.IGNORECASE)
                s2 = re.search(status_pat, c2.claim_text, re.IGNORECASE)
                if s1 and s2 and s1.group(1).lower() != s2.group(1).lower():
                    seen_pairs.add(pair_key)
                    conflicts.append(
                        Conflict(
                            id=uuid.uuid4(),
                            event_id=event_id,
                            snapshot_id=snapshot_id,
                            field_name="status_level",
                            claim_a_id=c1.id,
                            claim_b_id=c2.id,
                            value_a=s1.group(1).strip(),
                            value_b=s2.group(1).strip(),
                            context="Perbedaan status siaga antara laporan lapangan",
                            resolved=False,
                        )
                    )

        return conflicts

    @staticmethod
    def resolve_conflicts_with_update(
        conflicts: list[Conflict],
        claims: list[Claim],
    ) -> list[Conflict]:
        """Resolve existing conflicts when an authoritative official claim provides clarification."""
        for cf in conflicts:
            if cf.resolved:
                continue

            for c in claims:
                tier_str = (
                    c.source.source_tier.value
                    if (c.source and hasattr(c.source.source_tier, "value"))
                    else str(c.source.source_tier if c.source else "")
                ).upper()
                is_official = (
                    c.source is not None
                    and c.source.source_family.startswith("GOV_")
                    and ("TIER_1" in tier_str or tier_str == "1")
                )
                lower_text = c.claim_text.lower()

                # Case 1: Official update on numbers (e.g. BPBD DKI verifying 6 kecamatan)
                if (
                    is_official
                    and cf.field_name.startswith("affected_")
                    and (
                        "terverifikasi" in lower_text
                        or "total" in lower_text
                        or "mencatat" in lower_text
                    )
                ):
                    cf.resolved = True
                    cf.resolution_claim_id = c.id
                    break

                # Case 2: Clarification / retraction (e.g. BPPTKG confirming Level III instead of IV)
                if (
                    "ralat" in lower_text
                    or "klarifikasi" in lower_text
                    or "kekeliruan" in lower_text
                    or is_official
                ) and cf.field_name == "status_level":
                    cf.resolved = True
                    cf.resolution_claim_id = c.id
                    break

        return conflicts
