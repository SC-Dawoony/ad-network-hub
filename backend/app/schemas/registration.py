"""Registration workflow API schemas."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


FailurePolicy = Literal["stop_on_failure", "continue_on_failure"]
StepStatus = Literal["pending", "running", "success", "failed", "skipped"]
JobStatus = Literal["pending", "running", "success", "failed", "partial_success", "cancelled"]


class NetworkSummary(BaseModel):
    key: str
    display_name: str
    supports_create_app: bool
    supports_create_unit: bool


class RegistrationIntent(BaseModel):
    app_name: str = Field(..., min_length=1)
    android_url: Optional[str] = None
    ios_url: Optional[str] = None
    app_match_name: Optional[str] = None
    networks: List[str] = Field(default_factory=list)
    unit_formats: List[str] = Field(default_factory=lambda: ["rv", "is", "bn"])
    failure_policy: FailurePolicy = "continue_on_failure"
    network_settings: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class RegistrationStep(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    network: str
    action: str
    sequence: int
    status: StepStatus = "pending"
    request_summary: Dict[str, Any] = Field(default_factory=dict)
    response_summary: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class RegistrationJob(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    actor_email: str
    intent: RegistrationIntent
    status: JobStatus = "pending"
    steps: List[RegistrationStep] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None


class AuditEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    actor_email: str
    action: str
    target_type: str
    target_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
