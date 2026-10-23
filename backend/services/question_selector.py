"""
Seeded question-selection algorithm (Section 5 of the SRS).

Algorithm version: 1.0
RNG: Python's random.Random (Mersenne Twister) seeded with an integer seed.
"""
import random
import time
from typing import List

from config import settings


ALGORITHM_VERSION = "1.0"


def generate_seed() -> int:
    """Generate a new random seed based on current time."""
    return int(time.time() * 1000) % (2**31)


def select_questions(
    active_questions: List[dict],
    count: int,
    seed: int,
) -> List[str]:
    """
    Select `count` unique question IDs from `active_questions` using a seeded RNG.

    Returns an ordered list of question IDs.

    Requirements satisfied:
    - Deterministic: same seed + same sorted input → same output.
    - No replacement (unique questions).
    - Count must be within [MIN_QUESTIONS, MAX_QUESTIONS].
    - Selection is completed before the interview starts.
    """
    if not (settings.MIN_QUESTIONS <= count <= settings.MAX_QUESTIONS):
        raise ValueError(
            f"Question count {count} is outside allowed range "
            f"[{settings.MIN_QUESTIONS}, {settings.MAX_QUESTIONS}]"
        )

    if len(active_questions) < count:
        raise ValueError(
            f"Not enough active questions ({len(active_questions)}) to select {count}"
        )

    # Stable ordering before shuffle — sort by question id for determinism
    sorted_questions = sorted(active_questions, key=lambda q: q["id"])

    rng = random.Random(seed)
    shuffled = sorted_questions.copy()
    rng.shuffle(shuffled)

    selected = shuffled[:count]
    return [q["id"] for q in selected]


def select_questions_with_coverage(
    active_questions: List[dict],
    count: int,
    seed: int,
) -> List[str]:
    """
    Extended selection with competency coverage.

    Groups questions by competency and tries to spread selection across groups
    before falling back to pure random selection for remaining slots.
    """
    if not (settings.MIN_QUESTIONS <= count <= settings.MAX_QUESTIONS):
        raise ValueError(
            f"Question count {count} is outside allowed range "
            f"[{settings.MIN_QUESTIONS}, {settings.MAX_QUESTIONS}]"
        )

    if len(active_questions) < count:
        raise ValueError(
            f"Not enough active questions ({len(active_questions)}) to select {count}"
        )

    # Stable sort
    sorted_questions = sorted(active_questions, key=lambda q: q["id"])

    # Group by competency
    groups: dict[str, List[dict]] = {}
    for q in sorted_questions:
        comp = q.get("competency", "general")
        groups.setdefault(comp, []).append(q)

    rng = random.Random(seed)

    selected_ids: List[str] = []
    remaining_pool: List[dict] = []

    # Take 1 from each competency group (if possible)
    group_keys = sorted(groups.keys())
    for key in group_keys:
        if len(selected_ids) >= count:
            break
        group_qs = groups[key].copy()
        rng.shuffle(group_qs)
        chosen = group_qs[0]
        selected_ids.append(chosen["id"])
        # remaining questions from this group go into pool
        remaining_pool.extend(group_qs[1:])

    # If we still need more, draw from remaining pool
    if len(selected_ids) < count:
        rng.shuffle(remaining_pool)
        needed = count - len(selected_ids)
        for q in remaining_pool:
            if q["id"] not in selected_ids and needed > 0:
                selected_ids.append(q["id"])
                needed -= 1

    # Final shuffle for question order (same seed, extended)
    rng.shuffle(selected_ids)
    return selected_ids[:count]
