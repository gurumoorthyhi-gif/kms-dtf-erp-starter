"""Production workflow rules and immutable event recording."""

from __future__ import annotations

from decimal import Decimal

from app.modules.authentication import AuthenticationService
from app.modules.production.repository import ProductionRepository
from app.modules.production.schemas import (
    ProductionEventDetails,
    ProductionJobDetails,
    ProductionJobInput,
    QualityCheckInput,
)

PRODUCTION_STAGES = (
    "Design",
    "Approval",
    "Gang Sheet",
    "RIP Preparation",
    "Printing",
    "Powder and Cure",
    "Quality Check",
    "Cutting",
    "Packing",
    "Dispatch",
)
PRODUCTION_PRIORITIES = ("Low", "Normal", "High", "Urgent")


class InvalidProductionTransition(ValueError):
    pass


class ProductionService:
    def __init__(
        self,
        repository: ProductionRepository,
        authentication_service: AuthenticationService | None = None,
    ) -> None:
        self.repository = repository
        self.authentication_service = authentication_service

    def create_job(self, data: ProductionJobInput) -> ProductionJobDetails:
        self._require("production.manage")
        if data.order_id < 1 or data.priority not in PRODUCTION_PRIORITIES:
            raise ValueError("Order and valid priority are required")
        return self._details(
            self.repository.create(
                ProductionJobInput(
                    order_id=data.order_id,
                    priority=data.priority,
                    gang_sheet_id=data.gang_sheet_id,
                    due_date=data.due_date,
                    machine_name=data.machine_name.strip(),
                    operator_user_id=data.operator_user_id,
                    notes=data.notes.strip(),
                ),
                self._user_id(),
            )
        )

    def list_jobs(self) -> list[ProductionJobDetails]:
        self._require("production.view")
        return [self._details(job) for job in self.repository.list()]

    def get_job(self, job_id: int) -> ProductionJobDetails:
        self._require("production.view")
        job = self.repository.get(job_id)
        if job is None:
            raise LookupError("Production job not found")
        return self._details(job)

    def transition(self, job_id: int, to_stage: str, note: str = "") -> ProductionJobDetails:
        self._require("production.manage")
        job = self.repository.get(job_id)
        if job is None:
            raise LookupError("Production job not found")
        if job.is_paused:
            raise InvalidProductionTransition("Resume the job before changing stage")
        current_index = PRODUCTION_STAGES.index(job.stage)
        expected = (
            PRODUCTION_STAGES[current_index + 1]
            if current_index + 1 < len(PRODUCTION_STAGES)
            else None
        )
        if to_stage != expected:
            raise InvalidProductionTransition(f"Invalid transition from {job.stage} to {to_stage}")
        return self._details(
            self.repository.mutate(
                job_id,
                values={"stage": to_stage},
                event_type="stage_changed",
                details=note.strip(),
                actor_user_id=self._user_id(),
                from_stage=job.stage,
                to_stage=to_stage,
            )
        )

    def assign(
        self, job_id: int, *, machine_name: str, operator_user_id: int | None
    ) -> ProductionJobDetails:
        self._require("production.manage")
        return self._details(
            self.repository.mutate(
                job_id,
                values={
                    "machine_name": machine_name.strip(),
                    "operator_user_id": operator_user_id,
                },
                event_type="assignment",
                details=f"Machine: {machine_name.strip() or 'Unassigned'}; "
                f"operator ID: {operator_user_id or 'Unassigned'}",
                actor_user_id=self._user_id(),
            )
        )

    def pause(self, job_id: int, reason: str) -> ProductionJobDetails:
        self._require("production.manage")
        if not reason.strip():
            raise ValueError("Pause reason is required")
        return self._details(
            self.repository.mutate(
                job_id,
                values={"is_paused": True, "pause_reason": reason.strip()},
                event_type="paused",
                details=reason.strip(),
                actor_user_id=self._user_id(),
            )
        )

    def resume(self, job_id: int) -> ProductionJobDetails:
        self._require("production.manage")
        return self._details(
            self.repository.mutate(
                job_id,
                values={"is_paused": False, "pause_reason": ""},
                event_type="resumed",
                details="Production resumed",
                actor_user_id=self._user_id(),
            )
        )

    def record_reprint(self, job_id: int, reason: str) -> ProductionJobDetails:
        self._require("production.manage")
        if not reason.strip():
            raise ValueError("Reprint reason is required")
        job = self.repository.get(job_id)
        if job is None:
            raise LookupError("Production job not found")
        if PRODUCTION_STAGES.index(job.stage) < PRODUCTION_STAGES.index("Printing"):
            raise InvalidProductionTransition("Reprint can only be recorded after printing starts")
        return self._details(
            self.repository.mutate(
                job_id,
                values={"stage": "Printing", "reprint_count": job.reprint_count + 1},
                event_type="reprint",
                details=reason.strip(),
                actor_user_id=self._user_id(),
                from_stage=job.stage,
                to_stage="Printing",
            )
        )

    def record_wastage(self, job_id: int, metres: Decimal, reason: str) -> ProductionJobDetails:
        self._require("production.manage")
        if metres <= 0 or not reason.strip():
            raise ValueError("Positive wastage and a reason are required")
        return self._details(
            self.repository.add_wastage(job_id, metres, reason.strip(), self._user_id())
        )

    def record_quality_check(self, job_id: int, data: QualityCheckInput) -> ProductionJobDetails:
        self._require("production.manage")
        job = self.repository.get(job_id)
        if job is None:
            raise LookupError("Production job not found")
        if job.stage != "Quality Check":
            raise InvalidProductionTransition(
                "Quality checks can only be recorded at Quality Check stage"
            )
        return self._details(
            self.repository.add_quality_check(
                job_id,
                QualityCheckInput(
                    data.print_quality_ok,
                    data.colour_ok,
                    data.curing_ok,
                    data.notes.strip(),
                ),
                self._user_id(),
            )
        )

    def update_notes(self, job_id: int, notes: str) -> ProductionJobDetails:
        self._require("production.manage")
        return self._details(
            self.repository.mutate(
                job_id,
                values={"notes": notes.strip()},
                event_type="notes",
                details=notes.strip(),
                actor_user_id=self._user_id(),
            )
        )

    def _require(self, permission: str) -> None:
        if self.authentication_service is not None:
            self.authentication_service.require_permission(permission)

    def _user_id(self) -> int | None:
        if self.authentication_service is None:
            return None
        user = self.authentication_service.current_session.user
        return user.id if user else None

    @staticmethod
    def _details(job) -> ProductionJobDetails:
        return ProductionJobDetails(
            job.id,
            job.order.order_number,
            job.order.customer.name,
            job.stage,
            job.priority,
            job.machine_name,
            job.operator.full_name if job.operator else "",
            job.due_date,
            job.is_paused,
            job.pause_reason,
            job.reprint_count,
            job.wastage_metres,
            job.notes,
            tuple(
                ProductionEventDetails(
                    event.event_type,
                    event.from_stage,
                    event.to_stage,
                    event.details,
                    event.created_at,
                )
                for event in job.events
            ),
            len(job.quality_checks),
        )
