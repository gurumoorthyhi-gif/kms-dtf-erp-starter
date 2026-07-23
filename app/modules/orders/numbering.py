"""Human-readable order number generation."""

from datetime import date


def order_number_prefix(day: date) -> str:
    return f"KMS-{day:%Y%m%d}-"


def generate_order_number(day: date, sequence: int) -> str:
    if sequence < 1:
        raise ValueError("Order sequence must be positive")
    return f"{order_number_prefix(day)}{sequence:04d}"
