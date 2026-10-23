"""
Question bank loader — reads and validates JSON question-bank files.
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from config import settings, ROLES_CONFIG

logger = logging.getLogger(__name__)

# In-memory cache: role_id -> bank dict
_bank_cache: Dict[str, dict] = {}


def _bank_path(role_id: str) -> Optional[Path]:
    cfg = ROLES_CONFIG.get(role_id)
    if not cfg:
        return None
    return settings.QUESTION_BANKS_DIR / cfg["bank_file"]


def load_bank(role_id: str, force_reload: bool = False) -> dict:
    """Load (and cache) the question bank for a given role."""
    if role_id in _bank_cache and not force_reload:
        return _bank_cache[role_id]

    path = _bank_path(role_id)
    if not path or not path.exists():
        raise FileNotFoundError(f"Question bank not found for role '{role_id}': {path}")

    with open(path, "r", encoding="utf-8") as f:
        bank = json.load(f)

    _validate_bank(bank, role_id)
    _bank_cache[role_id] = bank
    return bank


def _validate_bank(bank: dict, role_id: str) -> None:
    """Basic validation of the question-bank structure."""
    assert bank.get("role_id") == role_id, f"role_id mismatch in bank file for '{role_id}'"
    assert "bank_version" in bank, "Missing bank_version"
    assert "questions" in bank, "Missing questions array"

    questions = bank["questions"]
    active_qs = [q for q in questions if q.get("active")]

    ids = [q["id"] for q in questions]
    assert len(ids) == len(set(ids)), "Duplicate question IDs found"

    for q in questions:
        assert q.get("id"), f"Question missing id: {q}"
        assert q.get("text"), f"Question missing text: {q.get('id')}"
        assert q.get("competency"), f"Question missing competency: {q.get('id')}"

    assert len(active_qs) >= settings.MIN_QUESTIONS, (
        f"Not enough active questions ({len(active_qs)}) for role '{role_id}'"
    )


def get_active_questions(role_id: str) -> List[dict]:
    bank = load_bank(role_id)
    return [q for q in bank["questions"] if q.get("active")]


def get_bank_version(role_id: str) -> str:
    bank = load_bank(role_id)
    return bank.get("bank_version", "unknown")


def get_question_by_id(role_id: str, question_id: str) -> Optional[dict]:
    bank = load_bank(role_id)
    for q in bank["questions"]:
        if q["id"] == question_id:
            return q
    return None


def get_questions_by_ids(role_id: str, question_ids: List[str]) -> List[dict]:
    bank = load_bank(role_id)
    q_map = {q["id"]: q for q in bank["questions"]}
    return [q_map[qid] for qid in question_ids if qid in q_map]


def get_bank_meta(role_id: str) -> dict:
    bank = load_bank(role_id)
    active = [q for q in bank["questions"] if q.get("active")]
    return {
        "role_id": bank["role_id"],
        "role_name": bank["role_name"],
        "category": bank["category"],
        "bank_version": bank["bank_version"],
        "total_active_questions": len(active),
    }
