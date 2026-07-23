from decimal import Decimal
from pathlib import Path

import pytest

from app.database import (
    Base,
    create_database_engine,
    create_session_factory,
    session_scope,
)
from app.modules.authentication.models import User
from app.modules.customers import CustomerInput, CustomerRepository, CustomerService
from app.modules.orders import OrderInput, OrderItemInput, OrderRepository, OrderService
from app.modules.production import (
    PRODUCTION_STAGES,
    InvalidProductionTransition,
    ProductionJobInput,
    ProductionRepository,
    ProductionService,
    QualityCheckInput,
)
from app.modules.products import ProductInput, ProductRepository, ProductService


@pytest.fixture
def production(tmp_path: Path):
    engine = create_database_engine(f"sqlite:///{tmp_path / 'production.db'}")
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    customers = CustomerService(CustomerRepository(factory))
    products = ProductService(ProductRepository(factory))
    customer = customers.create_customer(CustomerInput("CUS-001", "Customer", "9876543210"))
    category_id, _ = products.create_category("DTF")
    product = products.create_product(
        ProductInput("DTF", "DTF Print", category_id, "metre", Decimal("100"), Decimal("18"))
    )
    order_service = OrderService(OrderRepository(factory), products)
    order = order_service.create_order(
        OrderInput(
            customer.summary.id,
            (OrderItemInput(product.id, Decimal("1")),),
        )
    )
    with session_scope(factory) as session:
        operator = User(
            username="operator",
            password_hash="not-used",
            full_name="Production Operator",
        )
        session.add(operator)
        session.flush()
        operator_id = operator.id
    service = ProductionService(ProductionRepository(factory))
    yield service, order.summary.id, operator_id
    engine.dispose()


def test_create_assign_and_move_through_valid_stages(production) -> None:
    service, order_id, operator_id = production
    job = service.create_job(ProductionJobInput(order_id, priority="High"))
    assigned = service.assign(job.id, machine_name="DTF-01", operator_user_id=operator_id)

    assert assigned.machine_name == "DTF-01"
    assert assigned.operator_name == "Production Operator"
    for stage in PRODUCTION_STAGES[1:]:
        assigned = service.transition(assigned.id, stage)

    assert assigned.stage == "Dispatch"
    stage_events = [event for event in assigned.events if event.event_type == "stage_changed"]
    assert len(stage_events) == len(PRODUCTION_STAGES) - 1
    assert assigned.events[0].event_type == "created"


def test_invalid_stage_transition_is_rejected(production) -> None:
    service, order_id, _ = production
    job = service.create_job(ProductionJobInput(order_id))

    with pytest.raises(InvalidProductionTransition):
        service.transition(job.id, "Printing")

    assert service.get_job(job.id).stage == "Design"
    assert len(service.get_job(job.id).events) == 1


def test_pause_requires_reason_and_blocks_stage_change(production) -> None:
    service, order_id, _ = production
    job = service.create_job(ProductionJobInput(order_id))
    paused = service.pause(job.id, "Waiting for customer")

    with pytest.raises(InvalidProductionTransition):
        service.transition(job.id, "Approval")
    resumed = service.resume(paused.id)
    moved = service.transition(resumed.id, "Approval")

    assert moved.stage == "Approval"
    assert moved.is_paused is False


def test_wastage_quality_and_reprint_are_recorded(production) -> None:
    service, order_id, _ = production
    job = service.create_job(ProductionJobInput(order_id))
    for stage in PRODUCTION_STAGES[1:7]:
        job = service.transition(job.id, stage)
    assert job.stage == "Quality Check"

    checked = service.record_quality_check(
        job.id,
        QualityCheckInput(True, True, False, "Curing needs rework"),
    )
    wasted = service.record_wastage(checked.id, Decimal("0.350"), "Test strip")
    reprint = service.record_reprint(wasted.id, "Failed curing check")

    assert checked.quality_check_count == 1
    assert wasted.wastage_metres == Decimal("0.350")
    assert reprint.reprint_count == 1
    assert reprint.stage == "Printing"
    assert [event.event_type for event in reprint.events][-3:] == [
        "quality_check",
        "wastage",
        "reprint",
    ]
