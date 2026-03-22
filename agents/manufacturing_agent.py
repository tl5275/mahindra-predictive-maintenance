"""Manufacturing feedback agent for recurring defect patterns."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Dict, Iterable, List, Mapping


class ManufacturingAgent:
    """Tracks recurring issues to provide design and production feedback."""

    def detect_patterns(self, diagnoses: Iterable[Mapping[str, object]]) -> List[Dict[str, object]]:
        issue_counter: Counter[tuple[str, str]] = Counter()
        issue_examples: Dict[tuple[str, str], List[str]] = defaultdict(list)

        for diagnosis in diagnoses:
            model = str(diagnosis["model"])
            vehicle_id = str(diagnosis["vehicle_id"])
            for issue in diagnosis["issues"]:  # type: ignore[index]
                issue_code = str(issue["issue"])
                key = (model, issue_code)
                issue_counter[key] += 1
                if len(issue_examples[key]) < 5:
                    issue_examples[key].append(vehicle_id)

        recurring_patterns: List[Dict[str, object]] = []
        for (model, issue_code), count in issue_counter.items():
            if count < 8:
                continue
            recurring_patterns.append(
                {
                    "model": model,
                    "issue": issue_code,
                    "occurrences": count,
                    "sample_vehicle_ids": issue_examples[(model, issue_code)],
                    "recommendation": (
                        "Investigate supplier quality and tolerance windows for this subsystem."
                    ),
                }
            )

        recurring_patterns.sort(key=lambda item: int(item["occurrences"]), reverse=True)
        return recurring_patterns[:20]
