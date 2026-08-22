"""
Pydantic schema definitions for LLM Triage input and output.
"""

from enum import Enum
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any


class CategoryEnum(str, Enum):
    BILLING = "billing"
    BUG = "bug"
    FEATURE = "feature"
    OTHER = "other"


class UrgencyEnum(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class TriageInput(BaseModel):
    """Input payload for POST /triage."""
    text: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Raw customer support message text (1-2000 characters)"
    )

    @field_validator("text")
    def validate_non_whitespace(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("text cannot be empty or whitespace only")
        return stripped


class TriageResponse(BaseModel):
    """Clean, schema-validated triage output."""
    category: CategoryEnum = Field(..., description="Canonical message category")
    urgency: UrgencyEnum = Field(..., description="Triage urgency level")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model certainty score between 0.0 and 1.0")
    reason: str = Field(..., min_length=1, description="One short sentence explaining the classification")


class QuarantineLogRecord(BaseModel):
    """Schema for records quarantined in logs/quarantine.jsonl."""
    timestamp: str
    prompt_version: str
    input_text: str
    raw_model_output: str
    validation_error: str
    repair_attempted: bool
