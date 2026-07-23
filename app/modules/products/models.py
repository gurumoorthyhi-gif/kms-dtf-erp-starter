"""Product and configurable pricing models."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class ProductCategory(Base):
    __tablename__ = "product_categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    products: Mapped[list[Product]] = relationship(back_populates="category")


class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    category_id: Mapped[int] = mapped_column(ForeignKey("product_categories.id"))
    unit: Mapped[str] = mapped_column(String(20), default="piece")
    size: Mapped[str] = mapped_column(String(40), default="")
    colour: Mapped[str] = mapped_column(String(60), default="")
    gsm: Mapped[str] = mapped_column(String(20), default="")
    style: Mapped[str] = mapped_column(String(80), default="")
    base_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    category: Mapped[ProductCategory] = relationship(back_populates="products")
    price_rules: Mapped[list[PriceRule]] = relationship(
        back_populates="product", cascade="all, delete-orphan", lazy="selectin"
    )


class PriceRule(Base):
    __tablename__ = "price_rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    minimum_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    product: Mapped[Product] = relationship(back_populates="price_rules")


class DiscountRule(Base):
    __tablename__ = "discount_rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    minimum_subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class TaxConfiguration(Base):
    __tablename__ = "tax_configurations"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
