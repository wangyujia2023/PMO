import re
from difflib import SequenceMatcher
from typing import Iterable, Optional


STOP_WORDS = ["项目", "一期", "二期", "三期", "（", "）", "(", ")", " ", "-", "_"]


def normalize_name(name: str) -> str:
    normalized = name.strip().lower()
    for token in STOP_WORDS:
        normalized = normalized.replace(token, "")
    normalized = re.sub(r"[^\w\u4e00-\u9fff]", "", normalized)
    return normalized


def score_project_name(input_name: str, candidate_name: str, aliases: Optional[Iterable[str]] = None) -> float:
    candidates = [candidate_name]
    if aliases:
        candidates.extend([alias for alias in aliases if alias])

    source = normalize_name(input_name)
    best = 0.0
    for item in candidates:
        target = normalize_name(item)
        if not source or not target:
            continue
        if source == target:
            return 1.0
        ratio = SequenceMatcher(None, source, target).ratio()
        if source in target or target in source:
            ratio = max(ratio, 0.92)
        best = max(best, ratio)
    return best
