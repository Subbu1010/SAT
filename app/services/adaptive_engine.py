from __future__ import annotations


DIFFICULTY_ORDER = ["Easy", "Medium", "Hard"]


def next_difficulty(recent_results: list[bool], current: str) -> str:
    if current not in DIFFICULTY_ORDER:
        return "Medium"
    idx = DIFFICULTY_ORDER.index(current)
    if len(recent_results) < 3:
        return current

    streak_correct = all(recent_results[-3:])
    streak_wrong = not any(recent_results[-3:])

    if streak_correct and idx < len(DIFFICULTY_ORDER) - 1:
        return DIFFICULTY_ORDER[idx + 1]
    if streak_wrong and idx > 0:
        return DIFFICULTY_ORDER[idx - 1]
    return current
