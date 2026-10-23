"""
Roles router — GET /api/roles and /api/roles/{role_id}/question-bank
"""
from fastapi import APIRouter, HTTPException
from config import ROLES_CONFIG
from services.question_bank_loader import get_bank_meta
import schemas

router = APIRouter(prefix="/api/roles", tags=["roles"])


@router.get("", response_model=schemas.RoleListResponse)
def list_roles():
    technical = []
    non_technical = []
    for role_id, cfg in ROLES_CONFIG.items():
        info = schemas.RoleInfo(
            role_id=cfg["role_id"],
            role_name=cfg["role_name"],
            category=cfg["category"],
            competencies=cfg["competencies"],
        )
        if cfg["category"] == "technical":
            technical.append(info)
        else:
            non_technical.append(info)
    return schemas.RoleListResponse(technical=technical, non_technical=non_technical)


@router.get("/{role_id}/question-bank", response_model=schemas.QuestionBankMeta)
def get_question_bank_meta(role_id: str):
    if role_id not in ROLES_CONFIG:
        raise HTTPException(status_code=404, detail=f"Role '{role_id}' not found")
    try:
        meta = get_bank_meta(role_id)
        return schemas.QuestionBankMeta(**meta)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
