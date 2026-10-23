"""
Pydantic schemas for request / response validation.
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field
from models import SessionStatus, ResponseType, ProcessingStatus


# ── Auth ──────────────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    user_id: str
    email: str
    full_name: Optional[str]
    created_at: datetime
    is_admin: bool

    class Config:
        from_attributes = True


# ── Roles ─────────────────────────────────────────────────────────────────────

class RoleInfo(BaseModel):
    role_id: str
    role_name: str
    category: str
    competencies: List[str]


class RoleListResponse(BaseModel):
    technical: List[RoleInfo]
    non_technical: List[RoleInfo]


class QuestionBankMeta(BaseModel):
    role_id: str
    role_name: str
    category: str
    bank_version: str
    total_active_questions: int


# ── Interview Sessions ────────────────────────────────────────────────────────

class CreateInterviewRequest(BaseModel):
    role_id: str
    mode: ResponseType
    question_count: int = Field(default=10, ge=10, le=15)
    seed: Optional[int] = None  # None → server generates


class QuestionOut(BaseModel):
    id: str
    text: str
    competency: str
    difficulty: str


class InterviewSessionOut(BaseModel):
    session_id: str
    role_id: str
    mode: ResponseType
    question_count: int
    random_seed: int
    bank_version: str
    selected_question_ids: List[str]
    status: SessionStatus
    created_at: datetime
    submitted_at: Optional[datetime]

    class Config:
        from_attributes = True


class InterviewSessionWithQuestions(InterviewSessionOut):
    questions: List[QuestionOut]


class InterviewHistoryItem(BaseModel):
    session_id: str
    role_id: str
    role_name: str
    mode: ResponseType
    status: SessionStatus
    question_count: int
    created_at: datetime
    submitted_at: Optional[datetime]
    has_report: bool

    class Config:
        from_attributes = True


# ── Responses ─────────────────────────────────────────────────────────────────

class SaveResponseRequest(BaseModel):
    response_type: ResponseType
    text_content: Optional[str] = None
    transcript: Optional[str] = None
    duration_seconds: Optional[float] = None


class ResponseOut(BaseModel):
    response_id: str
    session_id: str
    question_id: str
    response_type: ResponseType
    text_content: Optional[str]
    transcript: Optional[str]
    duration_seconds: Optional[float]
    processing_status: ProcessingStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Evaluation Reports ────────────────────────────────────────────────────────

class EvaluationReportOut(BaseModel):
    report_id: str
    session_id: str
    overall_score: Optional[float]
    competency_scores: Optional[Dict[str, float]]
    overall_summary: Optional[str]
    strengths: Optional[List[str]]
    areas_less_demonstrated: Optional[List[str]]
    evidence_observations: Optional[List[str]]
    assessment_limitations: Optional[str]
    error_message: Optional[str] = None
    evaluation_version: str
    processing_status: ProcessingStatus
    created_at: datetime
    # metadata from session
    role_id: Optional[str] = None
    role_name: Optional[str] = None
    bank_version: Optional[str] = None

    class Config:
        from_attributes = True


# ── Generic ───────────────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str
    detail: Optional[str] = None
