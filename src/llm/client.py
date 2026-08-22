"""
Production-grade LLM client with schema validation, repair retries, timeouts,
cost logging, kill switch, and stub mode.
"""

import os
import time
import json
import random
import re
from datetime import datetime, timezone
from typing import Tuple, Dict, Any, Optional
from dotenv import load_dotenv
from openai import OpenAI, APIError, APITimeoutError, RateLimitError, AuthenticationError
from pydantic import ValidationError
from .schema import TriageResponse, CategoryEnum, UrgencyEnum

load_dotenv(override=True)


PROMPT_VERSION = "v1"
PROMPT_FILE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "prompts",
    "triage-v1.md"
)
LOGS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "logs"
)
QUARANTINE_LOG_PATH = os.path.join(LOGS_DIR, "quarantine.jsonl")


def load_system_prompt() -> str:
    """Load prompt spec from versioned markdown file."""
    if os.path.exists(PROMPT_FILE_PATH):
        with open(PROMPT_FILE_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return "You classify customer support messages into JSON: category, urgency, confidence, reason."


def clean_json_text(raw_text: str) -> str:
    """Strip markdown code fences and conversational wrappers."""
    text = raw_text.strip()
    if text.startswith("```"):
        # Remove opening and closing fences
        lines = text.split("\n")
        if len(lines) >= 2 and lines[-1].strip() == "```":
            text = "\n".join(lines[1:-1]).strip()
        elif len(lines) >= 1:
            text = "\n".join(lines[1:]).replace("```", "").strip()

    # Search for matching { ... } block
    match = re.search(r"(\{.*\})", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


def log_quarantine(input_text: str, raw_output: str, error_msg: str, repaired: bool) -> None:
    """Append unrepairable model failures to logs/quarantine.jsonl."""
    os.makedirs(LOGS_DIR, exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt_version": PROMPT_VERSION,
        "input_text": input_text,
        "raw_model_output": raw_output,
        "validation_error": error_msg,
        "repair_attempted": repaired
    }
    with open(QUARANTINE_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def log_structured_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    duration_ms: float,
    repairs: int,
    status: str
) -> None:
    """Print structured JSON cost and observability log line."""
    log_entry = {
        "event": "llm_call",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt_version": PROMPT_VERSION,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "duration_ms": round(duration_ms, 2),
        "repair_count": repairs,
        "status": status
    }
    print(f"[METRIC] {json.dumps(log_entry)}")


class LLMService:
    """Encapsulates reliable model execution with schema validation and repair retries."""

    @staticmethod
    def get_client() -> Tuple[OpenAI, str]:
        base_url = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
        api_key = os.getenv("LLM_API_KEY", "ollama")
        model = os.getenv("LLM_MODEL", "openrouter/free")
        # Explicit 30.0s timeout and max_retries=0 so our own retry policy controls backoff
        client = OpenAI(base_url=base_url, api_key=api_key, timeout=30.0, max_retries=0)
        return client, model

    @classmethod
    def execute_triage(cls, text: str) -> TriageResponse:
        """
        Execute triage pipeline:
        1. Check Kill Switch (LLM_ENABLED=false)
        2. Check Stub Mode (LLM_STUB=1)
        3. Call model with prompt v1 and safe retries
        4. Validate against Pydantic schema
        5. Repair once if invalid; quarantine and return 422 if still failing.
        """
        # Kill switch check
        llm_enabled = os.getenv("LLM_ENABLED", "true").lower() not in ("false", "0", "no", "off")
        if not llm_enabled:
            # Deterministic safe fallback
            return TriageResponse(
                category=CategoryEnum.OTHER,
                urgency=UrgencyEnum.NORMAL,
                confidence=0.5,
                reason="LLM feature disabled via kill switch (LLM_ENABLED=false)."
            )

        # Stub mode check
        llm_stub = os.getenv("LLM_STUB", "0").lower() in ("true", "1", "yes")
        if llm_stub:
            lower = text.lower()
            if "override" in lower or "ignore" in lower or "banana" in lower:
                cat, urg, conf, reason = CategoryEnum.OTHER, UrgencyEnum.LOW, 0.20, "Prompt injection attempt ignored in stub mode."
            elif "testing" in lower or "hello" in lower:
                cat, urg, conf, reason = CategoryEnum.OTHER, UrgencyEnum.LOW, 0.35, "General non-actionable greeting."
            elif "vat id" in lower or "receipt" in lower:
                cat, urg, conf, reason = CategoryEnum.BILLING, UrgencyEnum.NORMAL, 0.92, "VAT / receipt inquiry."
            elif any(w in lower for w in ["billed twice", "refund", "card"]):
                cat, urg, conf, reason = CategoryEnum.BILLING, UrgencyEnum.HIGH, 0.98, "Duplicate charge refund request."
            elif "typo" in lower:
                cat, urg, conf, reason = CategoryEnum.BUG, UrgencyEnum.LOW, 0.89, "Minor UI spelling defect."
            elif any(w in lower for w in ["crash", "500", "error"]):
                cat, urg, conf, reason = CategoryEnum.BUG, UrgencyEnum.HIGH, 0.96, "Application crash error reported."
            elif "dark mode" in lower:
                cat, urg, conf, reason = CategoryEnum.FEATURE, UrgencyEnum.LOW, 0.90, "UI feature request."
            elif "webhook" in lower or "kafka" in lower or "feature" in lower:
                cat, urg, conf, reason = CategoryEnum.FEATURE, UrgencyEnum.NORMAL, 0.94, "Technical integration feature request."
            else:
                cat, urg, conf, reason = CategoryEnum.OTHER, UrgencyEnum.NORMAL, 0.45, "General inquiry handled in stub mode."

            return TriageResponse(category=cat, urgency=urg, confidence=conf, reason=reason)


        # Real model call
        client, model = cls.get_client()
        system_prompt = load_system_prompt()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]

        t0 = time.time()
        repair_count = 0
        input_tokens_total = 0
        output_tokens_total = 0

        # Primary attempt with retry policy
        raw_output, in_tok, out_tok = cls._call_model_with_retries(client, model, messages)
        input_tokens_total += in_tok
        output_tokens_total += out_tok

        cleaned = clean_json_text(raw_output)
        try:
            parsed = TriageResponse.model_validate_json(cleaned)
            duration_ms = (time.time() - t0) * 1000
            log_structured_cost(model, input_tokens_total, output_tokens_total, duration_ms, repair_count, "SUCCESS")
            return parsed
        except (ValidationError, Exception) as first_err:
            # Stage 3: Repair once — and only once
            repair_count = 1
            repair_messages = list(messages)
            repair_messages.append({"role": "assistant", "content": raw_output})
            repair_messages.append({
                "role": "user",
                "content": (
                    f"Your previous answer was rejected for this validation error: {str(first_err)}. "
                    "Return ONLY corrected, valid JSON matching the schema with category in [billing, bug, feature, other] "
                    "and urgency in [low, normal, high]."
                )
            })

            repair_raw, r_in, r_out = cls._call_model_with_retries(client, model, repair_messages)
            input_tokens_total += r_in
            output_tokens_total += r_out

            repair_cleaned = clean_json_text(repair_raw)
            try:
                parsed_repaired = TriageResponse.model_validate_json(repair_cleaned)
                duration_ms = (time.time() - t0) * 1000
                log_structured_cost(model, input_tokens_total, output_tokens_total, duration_ms, repair_count, "REPAIRED")
                return parsed_repaired
            except Exception as final_err:
                duration_ms = (time.time() - t0) * 1000
                log_structured_cost(model, input_tokens_total, output_tokens_total, duration_ms, repair_count, "QUARANTINED")
                log_quarantine(text, repair_raw, str(final_err), repaired=True)
                raise UnprocessableEntityError(f"Model output failed schema validation after repair attempt: {str(final_err)}")

    @classmethod
    def _call_model_with_retries(cls, client: OpenAI, model: str, messages: list) -> Tuple[str, int, int]:
        """Execute chat completion with backoff + jitter on 429, 5xx, timeouts. Never retries 400, 401, 403."""
        max_attempts = 3
        backoff_base = 1.0

        for attempt in range(1, max_attempts + 1):
            try:
                res = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.1
                )
                raw_text = res.choices[0].message.content or "{}"
                in_tokens = res.usage.prompt_tokens if res.usage else 0
                out_tokens = res.usage.completion_tokens if res.usage else 0
                return raw_text, in_tokens, out_tokens

            except AuthenticationError as e:
                # 401 / 403: Bad API key — fail fast without retrying
                raise BadCredentialsError(f"LLM Provider Authentication Failed: {str(e)}")

            except APITimeoutError as e:
                if attempt == max_attempts:
                    raise GatewayTimeoutError("LLM call timed out after 30 seconds.")
                sleep_time = backoff_base * (2 ** (attempt - 1)) + random.uniform(0.1, 0.4)
                time.sleep(sleep_time)

            except RateLimitError as e:
                if attempt == max_attempts:
                    raise RateLimitExceededError(f"LLM Provider rate limit exceeded: {str(e)}")
                sleep_time = backoff_base * (2 ** (attempt - 1)) + random.uniform(0.2, 0.6)
                time.sleep(sleep_time)

            except APIError as e:
                # 400 Bad Request — never retry
                if getattr(e, "status_code", 0) == 400:
                    raise UnprocessableEntityError(f"Bad request to LLM provider: {str(e)}")
                # 5xx Server Error — retry with exponential backoff
                if attempt == max_attempts:
                    raise LLMProviderError(f"LLM Provider server error: {str(e)}")
                sleep_time = backoff_base * (2 ** (attempt - 1)) + random.uniform(0.1, 0.5)
                time.sleep(sleep_time)

        raise LLMProviderError("Failed to communicate with LLM provider.")


class UnprocessableEntityError(Exception):
    pass


class GatewayTimeoutError(Exception):
    pass


class BadCredentialsError(Exception):
    pass


class RateLimitExceededError(Exception):
    pass


class LLMProviderError(Exception):
    pass
