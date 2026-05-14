"""Registration job orchestration scaffold."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional

from backend.app.core.logging import get_logger
from backend.app.schemas.registration import (
    RegistrationIntent,
    RegistrationJob,
    RegistrationStep,
)

logger = get_logger(__name__)

DEFAULT_NETWORK_ORDER = [
    "applovin",
    "bigoads",
    "ironsource",
    "mintegral",
    "pangle",
    "fyber",
    "inmobi",
    "unity",
    "vungle",
    "admob",
]


class RegistrationOrchestrator:
    """Temporary in-memory orchestrator.

    This proves the API contract and UI workflow. Production execution should
    persist jobs in PostgreSQL and run each step through Cloud Tasks.
    """

    def __init__(self) -> None:
        self._jobs: Dict[str, RegistrationJob] = {}

    async def create_job(self, *, intent: RegistrationIntent, actor_email: str) -> RegistrationJob:
        selected = [network for network in DEFAULT_NETWORK_ORDER if network in set(intent.networks)]
        for network in intent.networks:
            if network not in selected:
                selected.append(network)

        steps = [
            RegistrationStep(
                network=network,
                action="create_app_and_units",
                sequence=index + 1,
            )
            for index, network in enumerate(selected)
        ]
        job = RegistrationJob(actor_email=actor_email, intent=intent, steps=steps)
        self._jobs[job.id] = job
        logger.info(
            "registration_job_created",
            extra={
                "job_id": job.id,
                "actor_email": actor_email,
                "app_name": intent.app_name,
                "networks": selected,
            },
        )
        return job

    def get_job(self, job_id: str) -> Optional[RegistrationJob]:
        return self._jobs.get(job_id)

    def list_jobs(self) -> List[RegistrationJob]:
        return sorted(self._jobs.values(), key=lambda job: job.created_at, reverse=True)

    async def run_job(self, job_id: str) -> None:
        job = self._jobs.get(job_id)
        if not job:
            logger.warning("registration_job_missing", extra={"job_id": job_id})
            return

        job.status = "running"
        logger.info("registration_job_started", extra={"job_id": job.id})

        failed = False
        for step in job.steps:
            if failed and job.intent.failure_policy == "stop_on_failure":
                step.status = "skipped"
                continue

            step.status = "running"
            step.started_at = datetime.now(timezone.utc)
            logger.info(
                "registration_step_started",
                extra={"job_id": job.id, "step_id": step.id, "network": step.network},
            )

            try:
                await self._run_step(job, step)
                step.status = "success"
                step.response_summary = {"message": "Step scaffold completed"}
            except Exception as exc:
                failed = True
                step.status = "failed"
                step.error_message = str(exc)
                logger.exception(
                    "registration_step_failed",
                    extra={"job_id": job.id, "step_id": step.id, "network": step.network},
                )
            finally:
                step.finished_at = datetime.now(timezone.utc)

        job.finished_at = datetime.now(timezone.utc)
        statuses = {step.status for step in job.steps}
        if "failed" in statuses and "success" in statuses:
            job.status = "partial_success"
        elif "failed" in statuses:
            job.status = "failed"
        else:
            job.status = "success"
        logger.info("registration_job_finished", extra={"job_id": job.id, "status": job.status})

    async def _run_step(self, job: RegistrationJob, step: RegistrationStep) -> None:
        step.request_summary = {
            "app_name": job.intent.app_name,
            "android_url": job.intent.android_url,
            "ios_url": job.intent.ios_url,
            "unit_formats": job.intent.unit_formats,
            "network_settings": job.intent.network_settings.get(step.network, {}),
        }
        await asyncio.sleep(0)


orchestrator = RegistrationOrchestrator()
