"""
Application configuration — loaded from environment variables / .env file.
"""
import os
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings


BASE_DIR = Path(__file__).resolve().parent.parent  # project root


class Settings(BaseSettings):
    # ── Security ──────────────────────────────────────────────────────────────
    SECRET_KEY: str = "change-me-in-production-use-a-long-random-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/interview_app.db"

    # ── Google Gemini ─────────────────────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.8-flash"

    # Local Ollama primary evaluator
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:0.5b"
    OLLAMA_API_KEY: str = ""
    OLLAMA_CLOUD_BASE_URL: str = "https://ollama.com"
    OLLAMA_CLOUD_MODEL: str = "gemma4:31b"
    OLLAMA_LOCAL_TIMEOUT_SECONDS: int = Field(default=45, ge=1, le=300)
    OLLAMA_CLOUD_TIMEOUT_SECONDS: int = Field(default=90, ge=1, le=300)

    # ── Question banks ────────────────────────────────────────────────────────
    QUESTION_BANKS_DIR: Path = BASE_DIR / "question_banks"

    # ── Interview constraints ─────────────────────────────────────────────────
    MIN_QUESTIONS: int = 5
    MAX_QUESTIONS: int = 15
    DEFAULT_QUESTIONS: int = 5

    # ── Media storage ─────────────────────────────────────────────────────────
    MEDIA_DIR: Path = BASE_DIR / "media"

    # ── CORS ──────────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["*"]

    class Config:
        env_file = str(BASE_DIR / ".env")
        env_file_encoding = "utf-8"


settings = Settings()

# Ensure media directory exists
settings.MEDIA_DIR.mkdir(parents=True, exist_ok=True)

# ── Role configuration ────────────────────────────────────────────────────────
ROLES_CONFIG = {
    "SDE": {
        "role_id": "SDE",
        "role_name": "Software Development Engineer",
        "category": "technical",
        "bank_file": "technical/sde.json",
        "competencies": ["ownership", "problem_solving", "teamwork", "conflict_resolution", "adaptability", "accountability", "prioritization"],
        "rubric_weights": {"ownership": 20, "problem_solving": 20, "teamwork": 15, "conflict_resolution": 15, "adaptability": 15, "accountability": 15},
    },
    "DS": {
        "role_id": "DS",
        "role_name": "Data Scientist",
        "category": "technical",
        "bank_file": "technical/data_scientist.json",
        "competencies": ["analytical_reasoning", "experimentation", "communicating_findings", "collaboration", "ownership", "accountability", "adaptability", "prioritization"],
        "rubric_weights": {"analytical_reasoning": 25, "experimentation": 20, "communicating_findings": 20, "collaboration": 15, "ownership": 10, "accountability": 10},
    },
    "DA": {
        "role_id": "DA",
        "role_name": "Data Analyst",
        "category": "technical",
        "bank_file": "technical/data_analyst.json",
        "competencies": ["attention_to_detail", "data_driven_decisions", "stakeholder_communication", "structured_analysis", "accountability", "adaptability"],
        "rubric_weights": {"attention_to_detail": 20, "data_driven_decisions": 20, "stakeholder_communication": 25, "structured_analysis": 20, "accountability": 15},
    },
    "MLE": {
        "role_id": "MLE",
        "role_name": "Machine Learning Engineer",
        "category": "technical",
        "bank_file": "technical/ml_engineer.json",
        "competencies": ["experimentation", "reliability", "problem_solving", "teamwork", "handling_model_failures", "ownership", "accountability", "adaptability"],
        "rubric_weights": {"experimentation": 20, "reliability": 20, "problem_solving": 20, "teamwork": 15, "handling_model_failures": 15, "accountability": 10},
    },
    "DEVOPS": {
        "role_id": "DEVOPS",
        "role_name": "DevOps Engineer",
        "category": "technical",
        "bank_file": "technical/devops_engineer.json",
        "competencies": ["incident_ownership", "reliability", "collaboration", "prioritization", "accountability", "adaptability"],
        "rubric_weights": {"incident_ownership": 25, "reliability": 25, "collaboration": 20, "prioritization": 15, "accountability": 15},
    },
    "CYBERSEC": {
        "role_id": "CYBERSEC",
        "role_name": "Cybersecurity Engineer",
        "category": "technical",
        "bank_file": "technical/cybersecurity_engineer.json",
        "competencies": ["risk_judgment", "responsible_escalation", "incident_response", "integrity", "collaboration", "adaptability"],
        "rubric_weights": {"risk_judgment": 25, "responsible_escalation": 20, "incident_response": 25, "integrity": 20, "collaboration": 10},
    },
    "PM": {
        "role_id": "PM",
        "role_name": "Product Manager",
        "category": "non_technical",
        "bank_file": "non_technical/product_manager.json",
        "competencies": ["prioritization", "leadership", "conflict_resolution", "decision_making", "adaptability", "accountability"],
        "rubric_weights": {"prioritization": 20, "leadership": 25, "conflict_resolution": 15, "decision_making": 25, "adaptability": 15},
    },
    "BA": {
        "role_id": "BA",
        "role_name": "Business Analyst",
        "category": "non_technical",
        "bank_file": "non_technical/business_analyst.json",
        "competencies": ["requirements_clarification", "stakeholder_management", "analytical_reasoning", "accountability", "adaptability"],
        "rubric_weights": {"requirements_clarification": 30, "stakeholder_management": 25, "analytical_reasoning": 25, "accountability": 10, "adaptability": 10},
    },
    "HR": {
        "role_id": "HR",
        "role_name": "Human Resources Professional",
        "category": "non_technical",
        "bank_file": "non_technical/hr.json",
        "competencies": ["confidentiality", "empathy", "conflict_resolution", "fairness", "adaptability"],
        "rubric_weights": {"confidentiality": 20, "empathy": 25, "conflict_resolution": 25, "fairness": 25, "adaptability": 5},
    },
    "MKT": {
        "role_id": "MKT",
        "role_name": "Marketing Manager",
        "category": "non_technical",
        "bank_file": "non_technical/marketing_manager.json",
        "competencies": ["creativity", "campaign_ownership", "collaboration", "adaptability"],
        "rubric_weights": {"creativity": 25, "campaign_ownership": 30, "collaboration": 20, "adaptability": 25},
    },
    "SALES": {
        "role_id": "SALES",
        "role_name": "Sales Executive",
        "category": "non_technical",
        "bank_file": "non_technical/sales_executive.json",
        "competencies": ["communication", "relationship_management", "resilience", "accountability"],
        "rubric_weights": {"communication": 25, "relationship_management": 30, "resilience": 25, "accountability": 20},
    },
    "MC": {
        "role_id": "MC",
        "role_name": "Management / Consulting",
        "category": "non_technical",
        "bank_file": "non_technical/management_consulting.json",
        "competencies": ["structured_problem_solving", "teamwork", "client_communication", "adaptability"],
        "rubric_weights": {"structured_problem_solving": 30, "teamwork": 20, "client_communication": 30, "adaptability": 20},
    },
}
