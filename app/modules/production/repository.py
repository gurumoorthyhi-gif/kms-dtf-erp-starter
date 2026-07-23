"""Transactional production persistence."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import SessionFactory, session_scope
from app.modules.production.models import ProductionEvent, ProductionJob, QualityCheck
from app.modules.production.schemas import ProductionJobInput, QualityCheckInput


class ProductionRepository:
    def __init__(self, factory: SessionFactory) -> None:
        self.factory = factory

    def create(self, data: ProductionJobInput, actor_user_id: int | None) -> ProductionJob:
        with session_scope(self.factory) as session:
            job = ProductionJob(
                order_id=data.order_id,
                gang_sheet_id=data.gang_sheet_id,
                stage="Design",
                priority=data.priority,
                machine_name=data.machine_name,
                operator_user_id=data.operator_user_id,
                due_date=data.due_date,
                notes=data.notes,
            )
            job.events.append(
                ProductionEvent(
                    event_type="created",
                    to_stage="Design",
                    details="Production job created",
                    actor_user_id=actor_user_id,
                )
            )
            session.add(job)
            session.flush()
            job_id = job.id
        return self._required(job_id)

    def list(self) -> list[ProductionJob]:
        with session_scope(self.factory) as session:
            return list(
                session.scalars(
                    self._statement().order_by(
                        ProductionJob.is_paused.desc(),
                        ProductionJob.due_date,
                        ProductionJob.priority.desc(),
                    )
                )
            )

    def get(self, job_id: int) -> ProductionJob | None:
        with session_scope(self.factory) as session:
            return session.scalar(self._statement().where(ProductionJob.id == job_id))

    def mutate(
        self,
        job_id: int,
        *,
        values: dict,
        event_type: str,
        details: str,
        actor_user_id: int | None,
        from_stage: str | None = None,
        to_stage: str | None = None,
    ) -> ProductionJob:
        with session_scope(self.factory) as session:
            job = session.get(ProductionJob, job_id)
            if job is None:
                raise LookupError("Production job not found")
            for key, value in values.items():
                setattr(job, key, value)
            session.add(
                ProductionEvent(
                    production_job_id=job_id,
                    event_type=event_type,
                    from_stage=from_stage,
                    to_stage=to_stage,
                    details=details,
                    actor_user_id=actor_user_id,
                )
            )
        return self._required(job_id)

    def add_wastage(
        self, job_id: int, metres: Decimal, reason: str, actor_user_id: int | None
    ) -> ProductionJob:
        with session_scope(self.factory) as session:
            job = session.get(ProductionJob, job_id)
            if job is None:
                raise LookupError("Production job not found")
            job.wastage_metres += metres
            session.add(
                ProductionEvent(
                    production_job_id=job_id,
                    event_type="wastage",
                    details=f"{metres} m — {reason}",
                    actor_user_id=actor_user_id,
                )
            )
        return self._required(job_id)

    def add_quality_check(
        self, job_id: int, data: QualityCheckInput, actor_user_id: int | None
    ) -> ProductionJob:
        passed = data.print_quality_ok and data.colour_ok and data.curing_ok
        with session_scope(self.factory) as session:
            job = session.get(ProductionJob, job_id)
            if job is None:
                raise LookupError("Production job not found")
            session.add(
                QualityCheck(
                    production_job_id=job_id,
                    passed=passed,
                    print_quality_ok=data.print_quality_ok,
                    colour_ok=data.colour_ok,
                    curing_ok=data.curing_ok,
                    notes=data.notes,
                    inspector_user_id=actor_user_id,
                )
            )
            session.add(
                ProductionEvent(
                    production_job_id=job_id,
                    event_type="quality_check",
                    details=f"{'Passed' if passed else 'Failed'} — {data.notes}",
                    actor_user_id=actor_user_id,
                )
            )
        return self._required(job_id)

    @staticmethod
    def _statement():
        from app.modules.orders.models import Order

        return select(ProductionJob).options(
            selectinload(ProductionJob.order).selectinload(Order.customer),
            selectinload(ProductionJob.operator),
            selectinload(ProductionJob.events),
            selectinload(ProductionJob.quality_checks),
        )

    def _required(self, job_id: int) -> ProductionJob:
        job = self.get(job_id)
        if job is None:
            raise LookupError("Production job not found")
        return job
