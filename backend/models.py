"""
SQLAlchemy database models.
"""
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean,
    DateTime, ForeignKey, Text, JSON, Enum as SAEnum
)
from sqlalchemy.orm import relationship
import enum
from database import Base


class SessionStatus(str, enum.Enum):
    in_progress = "in_progress"
    submitted = "submitted"
    evaluated = "evaluated"
    failed = "failed"


class ResponseType(str, enum.Enum):
    text = "text"
    voice = "voice"
    video = "video"


class ProcessingStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class User(Base):
    __tablename__ = "users"

    user_id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)

    sessions = relationship("InterviewSession", back_populates="user")


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    session_id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    role_id = Column(String, nullable=False)
    mode = Column(SAEnum(ResponseType), nullable=False)
    question_count = Column(Integer, nullable=False)
    random_seed = Column(Integer, nullable=False)
    bank_version = Column(String, nullable=False)
    selection_algorithm_version = Column(String, default="1.0")
    selected_question_ids = Column(JSON, nullable=False)   # ordered list
    status = Column(SAEnum(SessionStatus), default=SessionStatus.in_progress)
    created_at = Column(DateTime, default=datetime.utcnow)
    submitted_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="sessions")
    responses = relationship("Response", back_populates="session", cascade="all, delete-orphan")
    report = relationship("EvaluationReport", back_populates="session", uselist=False, cascade="all, delete-orphan")


class Response(Base):
    __tablename__ = "responses"

    response_id = Column(String, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("interview_sessions.session_id"), nullable=False)
    question_id = Column(String, nullable=False)
    response_type = Column(SAEnum(ResponseType), nullable=False)
    text_content = Column(Text, nullable=True)
    media_object_key = Column(String, nullable=True)
    transcript = Column(Text, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    processing_status = Column(SAEnum(ProcessingStatus), default=ProcessingStatus.completed)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    session = relationship("InterviewSession", back_populates="responses")


class EvaluationReport(Base):
    __tablename__ = "evaluation_reports"

    report_id = Column(String, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("interview_sessions.session_id"), unique=True, nullable=False)
    overall_score = Column(Float, nullable=True)
    competency_scores = Column(JSON, nullable=True)       # {competency: score}
    overall_summary = Column(Text, nullable=True)
    strengths = Column(JSON, nullable=True)               # list of strings
    areas_less_demonstrated = Column(JSON, nullable=True) # list of strings
    evidence_observations = Column(JSON, nullable=True)   # list of strings
    assessment_limitations = Column(Text, nullable=True)
    evaluation_version = Column(String, default="1.0")
    processing_status = Column(SAEnum(ProcessingStatus), default=ProcessingStatus.pending)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("InterviewSession", back_populates="report")
