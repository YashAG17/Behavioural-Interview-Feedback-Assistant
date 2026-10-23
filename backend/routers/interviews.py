"""
Interviews router — full CRUD for interview sessions and responses.
"""
import uuid
import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from database import get_db
from auth import get_current_user
from config import ROLES_CONFIG, settings
import models
import schemas
from services.question_bank_loader import (
    get_active_questions, get_bank_version, get_questions_by_ids,
)
from services.question_selector import (
    select_questions_with_coverage, generate_seed, ALGORITHM_VERSION,
)
from services.evaluation_engine import evaluate_interview

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/interviews", tags=["interviews"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_session_or_404(session_id: str, user: models.User, db: Session) -> models.InterviewSession:
    session = db.query(models.InterviewSession).filter(
        models.InterviewSession.session_id == session_id,
        models.InterviewSession.user_id == user.user_id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")
    return session


def _run_evaluation(session_id: str, db_url: str):
    """Background task: run Gemini evaluation and persist report."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(db_url, connect_args={"check_same_thread": False} if "sqlite" in db_url else {})
    BgSession = sessionmaker(bind=engine)
    db = BgSession()

    try:
        session = db.query(models.InterviewSession).filter(
            models.InterviewSession.session_id == session_id
        ).first()
        if not session:
            return

        report = db.query(models.EvaluationReport).filter(
            models.EvaluationReport.session_id == session_id
        ).first()
        if not report:
            return

        report.processing_status = models.ProcessingStatus.processing
        db.commit()

        # Gather questions + responses
        questions = get_questions_by_ids(session.role_id, session.selected_question_ids)
        q_map = {q["id"]: q["text"] for q in questions}

        responses = db.query(models.Response).filter(
            models.Response.session_id == session_id
        ).all()
        r_map = {r.question_id: (r.transcript or r.text_content or "") for r in responses}

        questions_with_responses = [
            {
                "question_text": q_map.get(qid, f"Question {qid}"),
                "response": r_map.get(qid, ""),
            }
            for qid in session.selected_question_ids
        ]

        result = evaluate_interview(session.role_id, questions_with_responses)

        report.overall_score = result.get("overall_score")
        report.competency_scores = result.get("competency_scores")
        report.overall_summary = result.get("overall_summary")
        report.strengths = result.get("strengths")
        report.areas_less_demonstrated = result.get("areas_less_demonstrated")
        report.evidence_observations = result.get("evidence_observations")
        report.assessment_limitations = result.get("assessment_limitations")
        report.processing_status = models.ProcessingStatus.completed

        session.status = models.SessionStatus.evaluated
        db.commit()
        logger.info(f"Evaluation completed for session {session_id}")

    except Exception as e:
        logger.error(f"Evaluation failed for session {session_id}: {e}")
        report = db.query(models.EvaluationReport).filter(
            models.EvaluationReport.session_id == session_id
        ).first()
        if report:
            report.processing_status = models.ProcessingStatus.failed
            report.error_message = str(e)
            db.commit()
    finally:
        db.close()


# ── Create interview ──────────────────────────────────────────────────────────

@router.post("", response_model=schemas.InterviewSessionWithQuestions, status_code=201)
def create_interview(
    payload: schemas.CreateInterviewRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.role_id not in ROLES_CONFIG:
        raise HTTPException(status_code=400, detail=f"Unknown role '{payload.role_id}'")

    seed = payload.seed if payload.seed is not None else generate_seed()
    bank_version = get_bank_version(payload.role_id)
    active_qs = get_active_questions(payload.role_id)

    try:
        selected_ids = select_questions_with_coverage(active_qs, payload.question_count, seed)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    session = models.InterviewSession(
        session_id=str(uuid.uuid4()),
        user_id=current_user.user_id,
        role_id=payload.role_id,
        mode=payload.mode,
        question_count=payload.question_count,
        random_seed=seed,
        bank_version=bank_version,
        selection_algorithm_version=ALGORITHM_VERSION,
        selected_question_ids=selected_ids,
        status=models.SessionStatus.in_progress,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    questions = get_questions_by_ids(payload.role_id, selected_ids)
    q_out = [schemas.QuestionOut(**q) for q in questions]

    return schemas.InterviewSessionWithQuestions(
        **schemas.InterviewSessionOut.model_validate(session).model_dump(),
        questions=q_out,
    )


# ── Get session ───────────────────────────────────────────────────────────────

@router.get("/history", response_model=List[schemas.InterviewHistoryItem])
def get_history(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sessions = (
        db.query(models.InterviewSession)
        .filter(models.InterviewSession.user_id == current_user.user_id)
        .order_by(models.InterviewSession.created_at.desc())
        .all()
    )
    items = []
    for s in sessions:
        role_cfg = ROLES_CONFIG.get(s.role_id, {})
        items.append(schemas.InterviewHistoryItem(
            session_id=s.session_id,
            role_id=s.role_id,
            role_name=role_cfg.get("role_name", s.role_id),
            mode=s.mode,
            status=s.status,
            question_count=s.question_count,
            created_at=s.created_at,
            submitted_at=s.submitted_at,
            has_report=s.report is not None,
        ))
    return items


@router.get("/{session_id}", response_model=schemas.InterviewSessionOut)
def get_session(
    session_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_session_or_404(session_id, current_user, db)


@router.get("/{session_id}/questions", response_model=List[schemas.QuestionOut])
def get_session_questions(
    session_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _get_session_or_404(session_id, current_user, db)
    questions = get_questions_by_ids(session.role_id, session.selected_question_ids)
    return [schemas.QuestionOut(**q) for q in questions]


@router.get("/{session_id}/responses", response_model=List[schemas.ResponseOut])
def get_session_responses(
    session_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_session_or_404(session_id, current_user, db)
    return db.query(models.Response).filter(
        models.Response.session_id == session_id
    ).all()


# ── Save / update response ────────────────────────────────────────────────────

@router.put("/{session_id}/responses/{question_id}", response_model=schemas.ResponseOut)
def save_response(
    session_id: str,
    question_id: str,
    payload: schemas.SaveResponseRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _get_session_or_404(session_id, current_user, db)

    if session.status == models.SessionStatus.submitted:
        raise HTTPException(status_code=400, detail="Cannot modify a submitted interview")

    if question_id not in session.selected_question_ids:
        raise HTTPException(status_code=400, detail=f"Question '{question_id}' not in this session")

    existing = db.query(models.Response).filter(
        models.Response.session_id == session_id,
        models.Response.question_id == question_id,
    ).first()

    if existing:
        existing.response_type = payload.response_type
        existing.text_content = payload.text_content
        existing.transcript = payload.transcript
        existing.duration_seconds = payload.duration_seconds
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing
    else:
        response = models.Response(
            response_id=str(uuid.uuid4()),
            session_id=session_id,
            question_id=question_id,
            response_type=payload.response_type,
            text_content=payload.text_content,
            transcript=payload.transcript,
            duration_seconds=payload.duration_seconds,
            processing_status=models.ProcessingStatus.completed,
        )
        db.add(response)
        db.commit()
        db.refresh(response)
        return response


# ── Submit interview ──────────────────────────────────────────────────────────

@router.post("/{session_id}/submit", response_model=schemas.MessageResponse)
def submit_interview(
    session_id: str,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _get_session_or_404(session_id, current_user, db)

    if session.status in (models.SessionStatus.submitted, models.SessionStatus.evaluated):
        raise HTTPException(status_code=400, detail="Interview already submitted")

    # Check all questions have responses
    responses = db.query(models.Response).filter(
        models.Response.session_id == session_id
    ).all()
    answered_ids = {r.question_id for r in responses if (r.text_content or r.transcript)}
    missing = [qid for qid in session.selected_question_ids if qid not in answered_ids]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Responses missing for questions: {missing}",
        )

    session.status = models.SessionStatus.submitted
    session.submitted_at = datetime.utcnow()

    # Create pending report
    report = models.EvaluationReport(
        report_id=str(uuid.uuid4()),
        session_id=session_id,
        processing_status=models.ProcessingStatus.pending,
    )
    db.add(report)
    db.commit()

    # Kick off evaluation in background
    background_tasks.add_task(_run_evaluation, session_id, settings.DATABASE_URL)

    return schemas.MessageResponse(
        message="Interview submitted successfully. Evaluation is in progress.",
        detail=session_id,
    )


# ── Get report ────────────────────────────────────────────────────────────────

@router.get("/{session_id}/report", response_model=schemas.EvaluationReportOut)
def get_report(
    session_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _get_session_or_404(session_id, current_user, db)
    report = db.query(models.EvaluationReport).filter(
        models.EvaluationReport.session_id == session_id
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not yet available")

    role_cfg = ROLES_CONFIG.get(session.role_id, {})
    out = schemas.EvaluationReportOut.model_validate(report)
    out.role_id = session.role_id
    out.role_name = role_cfg.get("role_name")
    out.bank_version = session.bank_version
    return out


@router.post("/{session_id}/evaluate", response_model=schemas.MessageResponse)
def retry_evaluation(
    session_id: str,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _get_session_or_404(session_id, current_user, db)
    if session.status not in (models.SessionStatus.submitted, models.SessionStatus.failed):
        raise HTTPException(status_code=400, detail="Only submitted interviews can be evaluated")
    report = db.query(models.EvaluationReport).filter(
        models.EvaluationReport.session_id == session_id
    ).first()
    if report is None:
        report = models.EvaluationReport(report_id=str(uuid.uuid4()), session_id=session_id)
        db.add(report)
    report.processing_status = models.ProcessingStatus.pending
    report.error_message = None
    session.status = models.SessionStatus.submitted
    db.commit()
    background_tasks.add_task(_run_evaluation, session_id, settings.DATABASE_URL)
    return schemas.MessageResponse(message="Evaluation retry started", detail=session_id)


# ── Delete session ────────────────────────────────────────────────────────────

@router.delete("/{session_id}", response_model=schemas.MessageResponse)
def delete_session(
    session_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _get_session_or_404(session_id, current_user, db)
    db.delete(session)
    db.commit()
    return schemas.MessageResponse(message="Session deleted successfully")
