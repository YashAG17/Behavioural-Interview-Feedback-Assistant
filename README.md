# InterviewPrep

InterviewPrep is a web application for practising behavioural interview questions. A candidate chooses a job role and interview format, answers a fixed set of questions, and receives a structured review of the complete session.

## Project overview

Behavioural interviews ask candidates to explain how they handled situations at work or in a team. It can be difficult to practise these questions without a partner, and difficult to judge whether an answer gives enough context, describes the candidate’s actions, and explains the outcome.

This project provides a place to practise independently. Questions are organised by role and competency. After submission, an AI evaluation service reviews the answers together and produces a report with competency scores and examples drawn from the candidate’s responses. The report is intended for practice and reflection; it does not make hiring recommendations.

## Intended users

- Students preparing for placements, internships, or graduate roles.
- Job seekers practising behavioural questions for a specific profession.
- Instructors demonstrating a full-stack application that combines structured question data, browser input, persistence, and an AI-backed evaluation workflow.

## How a practice session works

1. The user creates an account or signs in.
2. They select one of 12 roles, choose text, voice, or video mode, and set a session length of 5–15 questions.
3. The server selects and saves a fixed question set for the session. Questions do not change in response to earlier answers.
4. The user answers each question. Answers are saved as the user moves through the session, and an unfinished session can be resumed.
5. On submission, the server evaluates all answers together and saves a report.
6. The user can view the report and past sessions from the history page.

## Main specifications

### Role question banks

The question banks are JSON files stored in `question_banks/`. Each question is associated with a competency and difficulty. The 12 supported roles are:

| Technical roles | Non-technical roles |
| --- | --- |
| Software Development Engineer | Product Manager |
| Data Scientist | Business Analyst |
| Data Analyst | Human Resources Professional |
| Machine Learning Engineer | Marketing Manager |
| DevOps Engineer | Sales Executive |
| Cybersecurity Engineer | Management / Consulting |

### Response formats

- **Text:** type and edit an answer in the browser.
- **Voice:** use browser speech recognition to transcribe a spoken answer. Availability depends on the browser and its speech service; text entry remains available.
- **Video:** preview and record a response in the browser. The current version does not upload or store video; the transcript is what is saved and evaluated.

### Evaluation report

Each role has its own competency rubric and weights in `backend/config.py`. The evaluator reviews the full set of responses and returns:

- An overall score from 0 to 10, calculated from weighted competency scores.
- A score for each competency in the selected role’s rubric.
- An overall summary, evidence-based strengths, and areas that were less clearly demonstrated.
- Specific observations from the submitted answers and any assessment limitations.

The evaluation is instructed to use only the submitted evidence and not to recommend hiring or rejection. As with any language-model output, feedback can be incomplete or inaccurate and should be treated as practice guidance.

## Technology and design

| Area | Implementation |
| --- | --- |
| Frontend | HTML, CSS, and JavaScript; served by FastAPI |
| API | Python 3.10+ and FastAPI |
| Persistence | SQLAlchemy with SQLite by default; PostgreSQL is supported through `DATABASE_URL` |
| Authentication | JWT access tokens and hashed passwords |
| Question data | Versioned JSON question banks |
| Speech input | Browser Web Speech API where supported |
| Evaluation | Local Ollama first, optional Ollama Cloud second, Google Gemini last |

Provider order is intentional. The backend first calls the local Ollama server using `OLLAMA_MODEL` (default `qwen2.5:0.5b`). If local evaluation fails, it tries Ollama Cloud only when `OLLAMA_API_KEY` is configured. Gemini (`GEMINI_MODEL`, default `gemini-3.8-flash`) is the final fallback. The required providers and their availability depend on the values in `.env`.

## Repository layout

```text
backend/                 FastAPI application, API routes, models, and services
  routers/               Authentication, role, and interview endpoints
  services/              Question-bank loading, selection, and evaluation
frontend/                Browser pages, shared styles, and client-side code
question_banks/           Role-specific question data in JSON
tests/                    Project test files
.env.example              Configuration template (no real credentials)
```

## Run locally on Windows

### Requirements

- Python 3.10 or newer.
- Internet access for package installation and any configured hosted AI provider.
- Ollama is optional. Install it and download the configured local model to use local evaluation.

### 1. Configure the environment

From the project root in PowerShell:

```powershell
Copy-Item .env.example .env
```

Open `.env` and set a private `SECRET_KEY`. Add a Gemini API key if you want the Gemini fallback. Ollama Cloud is optional; set `OLLAMA_API_KEY` only if you want that provider enabled. Keep `.env` private; it is excluded from Git.

For local Ollama, make sure Ollama is running and the configured model is available. With the default model:

```powershell
ollama pull qwen2.5:0.5b
ollama list
```

### 2. Install and start the API

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
```

Open `http://127.0.0.1:8000` in a browser. Interactive API documentation is available at `http://127.0.0.1:8000/api/docs`; the health endpoint is `http://127.0.0.1:8000/api/health`.

The SQLite database file, `interview_app.db`, is created in the project root when the application starts. To use PostgreSQL, set `DATABASE_URL` in `.env` to a SQLAlchemy PostgreSQL URL; the PostgreSQL driver is included in `backend/requirements.txt`.

## Configuration reference

See `.env.example` for all available settings. The most commonly used are:

| Setting | Purpose |
| --- | --- |
| `SECRET_KEY` | Signs authentication tokens; replace the development value |
| `DATABASE_URL` | Database connection; defaults to project-local SQLite |
| `OLLAMA_BASE_URL` | Local Ollama server address |
| `OLLAMA_MODEL` | Local evaluation model |
| `OLLAMA_API_KEY` | Optional key that enables the Ollama Cloud fallback |
| `OLLAMA_CLOUD_MODEL` | Model used by the Ollama Cloud fallback |
| `GEMINI_API_KEY` | Optional Gemini fallback credential |
| `GEMINI_MODEL` | Gemini model identifier |
| `MIN_QUESTIONS` / `MAX_QUESTIONS` | Allowed session length; defaults to 5 and 15 |

Do not commit real API keys, passwords, or `.env` files to source control. The `.env.example` file contains placeholders only.

## API areas

All API routes are under `/api`:

- `/auth` — account registration, login, and current-user information.
- `/roles` — available roles and question-bank metadata.
- `/interviews` — create and resume sessions, save responses, submit for evaluation, view history and reports, retry evaluation, and delete sessions.

The complete route list and request schemas are shown in FastAPI’s `/api/docs` page.

## Current scope and limitations

- This is a local-first educational prototype, not a production hiring or assessment system.
- Speech transcription depends on browser support and may use a browser-managed speech service.
- Video recordings are not uploaded or retained by the server in the current implementation.
- Hosted evaluation providers require valid credentials and may have usage limits or charges. Local Ollama avoids hosted model charges but requires suitable local hardware and can be slower.
- AI-generated scores and comments are estimates for practice; they are not validated employment decisions.

## Project status

The repository contains the working application, role question banks, database-backed sessions and reports, and local run instructions. Deployment, production security review, and formal evaluation of feedback quality are outside the current project scope.
