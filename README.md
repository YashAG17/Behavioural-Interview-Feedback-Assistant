# InterviewIQ

Behavioural interview practice app with a FastAPI API, SQLite by default, 12 JSON role banks, browser text/speech/video capture, and consolidated AI evaluation reports.

## Run locally

1. Install Python 3.10 or newer.
2. Copy `.env.example` to `.env`. Set a private `SECRET_KEY` and `GEMINI_API_KEY`. Evaluations try local Ollama first, Ollama Cloud if `OLLAMA_API_KEY` is configured, then Gemini.
3. Install and start the API from the `backend` directory:

   ```powershell
   cd backend
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   uvicorn main:app --reload
   ```

4. Open `http://127.0.0.1:8000`. API documentation is at `/api/docs`.

The SQLite database is created in the project root on first startup. `DATABASE_URL` can be changed to a PostgreSQL SQLAlchemy URL for deployment. Browsers require localhost or HTTPS for microphone and camera permissions. Speech recognition availability depends on the browser; if unsupported, users can type answers.

## Workflow

Create an account, choose one of the 12 roles, response mode, and 10–15 questions. The backend saves a seeded, fixed question set. Answers are saved while navigating and restored when a session is resumed. Submit once all answers are present; Ollama is tried first and Gemini is used only if Ollama fails. The report and prior sessions are available from History.

Speech transcription uses the browser's Web Speech API. Video can be previewed and recorded in the browser, but the current app does not upload or retain video files; the answer transcript is what is saved and evaluated. Do not enter sensitive personal information in practice responses.

Ollama local must be running on the same computer as the backend and have the configured model available (`ollama list`). The current default is `qwen2.5:0.5b`, already installed here. Local inference has no per-request API charge. If `OLLAMA_API_KEY` is set, Ollama Cloud is used only after local Ollama fails; cloud usage consumes account credits and may incur charges after included starter credits.

## Configuration

See `.env.example` for database, Ollama, Gemini fallback, media directory, and security settings. Local Ollama needs no key. The Ollama Cloud and Gemini keys are optional fallbacks.
