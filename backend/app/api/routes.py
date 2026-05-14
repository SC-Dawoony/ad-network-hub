"""Initial API routes for the migration scaffold."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, BackgroundTasks, HTTPException

from backend.app.schemas.registration import (
    AuditEvent,
    NetworkSummary,
    RegistrationIntent,
    RegistrationJob,
)
from backend.app.services.audit_log import audit_log
from backend.app.services.registration_orchestrator import orchestrator

router = APIRouter()


@router.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}


@router.get("/api/networks", response_model=List[NetworkSummary])
async def list_networks() -> List[NetworkSummary]:
    from network_configs import get_available_networks, get_network_config

    summaries: List[NetworkSummary] = []
    for network in get_available_networks():
        config = get_network_config(network)
        summaries.append(
            NetworkSummary(
                key=network,
                display_name=config.display_name,
                supports_create_app=config.supports_create_app(),
                supports_create_unit=config.supports_create_unit(),
            )
        )
    return summaries


@router.post("/api/registration-jobs", response_model=RegistrationJob, status_code=202)
async def create_registration_job(
    intent: RegistrationIntent,
    background_tasks: BackgroundTasks,
) -> RegistrationJob:
    actor_email = "local-dev@example.com"
    job = await orchestrator.create_job(intent=intent, actor_email=actor_email)
    audit_log.record(
        actor_email=actor_email,
        action="registration_job.created",
        target_type="registration_job",
        target_id=job.id,
        metadata={
            "app_name": intent.app_name,
            "networks": intent.networks,
            "failure_policy": intent.failure_policy,
        },
    )
    background_tasks.add_task(orchestrator.run_job, job.id)
    return job


@router.get("/api/registration-jobs", response_model=List[RegistrationJob])
async def list_registration_jobs() -> List[RegistrationJob]:
    return orchestrator.list_jobs()


@router.get("/api/registration-jobs/{job_id}", response_model=RegistrationJob)
async def get_registration_job(job_id: str) -> RegistrationJob:
    job = orchestrator.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Registration job not found")
    return job


@router.get("/api/audit-events", response_model=List[AuditEvent])
async def list_audit_events() -> List[AuditEvent]:
    return audit_log.list_events()
