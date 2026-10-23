"""
AI Evaluation Engine — uses Google Gemini to evaluate interview responses.
"""
import json
import logging
from typing import List, Dict, Any
from urllib.request import Request, urlopen

from google import genai

from config import settings, ROLES_CONFIG

logger = logging.getLogger(__name__)


def _configure_gemini():
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured. Set it in your .env file.")
    return genai.Client(api_key=settings.GEMINI_API_KEY)


def _parse_and_validate(raw_text: str, rubric_weights: Dict[str, int]) -> Dict[str, Any]:
    raw_text = (raw_text or "").strip()
    if raw_text.startswith("```"):
        lines = raw_text.splitlines()
        raw_text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
    if not raw_text:
        raise RuntimeError("Evaluation provider returned an empty response")
    result = json.loads(raw_text)
    _validate_evaluation_result(result, rubric_weights)
    return result


def _evaluate_with_gemini(prompt: str, rubric_weights: Dict[str, int]) -> Dict[str, Any]:
    client = _configure_gemini()
    response = client.interactions.create(
        model=settings.GEMINI_MODEL,
        input=prompt,
        generation_config={"thinking_level": "low", "max_output_tokens": 4096},
    )
    return _parse_and_validate(response.output_text, rubric_weights)


def _call_ollama(base_url: str, model: str, prompt: str, rubric_weights: Dict[str, int], timeout: int, api_key: str = "") -> Dict[str, Any]:
    endpoint = f"{base_url.rstrip('/')}/api/chat"
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.2, "num_predict": 1200},
    }).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = Request(endpoint, data=body, headers=headers, method="POST")
    with urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    content = payload.get("message", {}).get("content")
    if not isinstance(content, str):
        raise RuntimeError("Ollama returned an unexpected response format")
    return _parse_and_validate(content, rubric_weights)


def _evaluate_with_ollama_local(prompt: str, rubric_weights: Dict[str, int]) -> Dict[str, Any]:
    """Run inference on the local Ollama server without an API key."""
    return _call_ollama(
        settings.OLLAMA_BASE_URL,
        settings.OLLAMA_MODEL,
        prompt,
        rubric_weights,
        settings.OLLAMA_LOCAL_TIMEOUT_SECONDS,
    )


def _evaluate_with_ollama_cloud(prompt: str, rubric_weights: Dict[str, int]) -> Dict[str, Any]:
    """Use Ollama's hosted API when a cloud key is configured."""
    if not settings.OLLAMA_API_KEY:
        raise RuntimeError("OLLAMA_API_KEY is not configured")
    return _call_ollama(
        settings.OLLAMA_CLOUD_BASE_URL,
        settings.OLLAMA_CLOUD_MODEL,
        prompt,
        rubric_weights,
        settings.OLLAMA_CLOUD_TIMEOUT_SECONDS,
        settings.OLLAMA_API_KEY,
    )


def _build_evaluation_prompt(
    role_id: str,
    questions_with_responses: List[Dict[str, str]],
    rubric_weights: Dict[str, int],
) -> str:
    role_cfg = ROLES_CONFIG[role_id]
    role_name = role_cfg["role_name"]
    competencies = role_cfg["competencies"]

    qr_text = ""
    for i, qr in enumerate(questions_with_responses, 1):
        qr_text += f"\n--- Question {i} ---\n"
        qr_text += f"Q: {qr['question_text']}\n"
        response = qr.get("response", "").strip()
        qr_text += f"A: {response if response else '[No response provided]'}\n"

    rubric_desc = "\n".join(
        f"  - {comp}: {weight}% weight"
        for comp, weight in rubric_weights.items()
    )

    prompt = f"""You are an expert behavioural interview evaluator assessing a candidate for the role of **{role_name}**.

You have received the candidate's complete interview responses below. Your task is to produce a single, evidence-based evaluation report.

## Interview Responses
{qr_text}

## Evaluation Rubric for {role_name}
Competencies and their weights (must sum to 100%):
{rubric_desc}

## Instructions

1. Evaluate the ENTIRE set of responses collectively — do NOT score individual questions.
2. For each competency, assign a score from 0–10 based on evidence demonstrated across all responses.
3. If evidence for a competency is absent or insufficient, note the limitation rather than penalizing heavily.
4. Calculate the weighted overall score: sum(weight_i / 100 * score_i) rounded to 1 decimal place.
5. Identify concrete strengths backed by specific examples from the responses.
6. Identify competencies that were less clearly demonstrated, citing what was missing.
7. List key evidence-based observations (specific examples from the candidate's answers).
8. Do NOT make hiring/rejection recommendations.
9. Do NOT invent evidence — ground all observations in the submitted responses.

## Required Output Format (JSON only, no markdown fences)

{{
  "overall_score": <float 0-10>,
  "competency_scores": {{
    "<competency_name>": <float 0-10>,
    ...
  }},
  "overall_summary": "<2-4 sentence overall assessment of the candidate's behavioural performance>",
  "strengths": [
    "<strength backed by evidence>",
    ...
  ],
  "areas_less_demonstrated": [
    "<competency or behaviour that needs more evidence>",
    ...
  ],
  "evidence_observations": [
    "<specific observation from one or more responses>",
    ...
  ],
  "assessment_limitations": "<note any limitations, e.g. skipped questions, very brief responses>"
}}

Output only valid JSON. Do not include any text before or after the JSON object.
"""
    return prompt


def evaluate_interview(
    role_id: str,
    questions_with_responses: List[Dict[str, str]],
) -> Dict[str, Any]:
    """
    Evaluate with local Ollama, Ollama Cloud, then Gemini.

    Args:
        role_id: The role identifier.
        questions_with_responses: List of dicts with 'question_text' and 'response'.

    Returns:
        Parsed evaluation dict matching EvaluationReport fields.
    """
    role_cfg = ROLES_CONFIG.get(role_id)
    if not role_cfg:
        raise ValueError(f"Unknown role_id: {role_id}")

    rubric_weights = role_cfg["rubric_weights"]

    prompt = _build_evaluation_prompt(role_id, questions_with_responses, rubric_weights)

    providers = [
        ("Ollama local", _evaluate_with_ollama_local),
        ("Ollama Cloud", _evaluate_with_ollama_cloud),
        ("Gemini", _evaluate_with_gemini),
    ]
    failures = []
    for name, evaluator in providers:
        if name == "Ollama Cloud" and not settings.OLLAMA_API_KEY:
            continue
        try:
            return evaluator(prompt, rubric_weights)
        except Exception:
            logger.warning("%s evaluation attempt failed", name, exc_info=True)
            failures.append(name)

    attempted = ", ".join(failures)
    raise RuntimeError(f"AI evaluation failed using: {attempted}")


def _validate_evaluation_result(result: dict, rubric_weights: Dict[str, int]) -> None:
    """Validate the structure of the evaluation result."""
    required_keys = [
        "overall_score", "competency_scores", "overall_summary",
        "strengths", "areas_less_demonstrated", "evidence_observations"
    ]
    for key in required_keys:
        if key not in result:
            raise ValueError(f"Evaluation result missing required key: {key}")

    score = result["overall_score"]
    if not (0 <= score <= 10):
        result["overall_score"] = max(0, min(10, score))

    for comp, s in result.get("competency_scores", {}).items():
        if not (0 <= s <= 10):
            result["competency_scores"][comp] = max(0, min(10, s))
