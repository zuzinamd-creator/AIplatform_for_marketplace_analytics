import uuid

from sqlalchemy import Enum, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin
from app.models.report import Marketplace


class Product(Base, TenantMixin, TimestampMixin):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("user_id", "marketplace", "external_sku", name="uq_product_tenant_sku"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    marketplace: Mapped[Marketplace] = mapped_column(
        Enum(Marketplace, name="marketplace_enum", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    external_sku: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    internal_sku: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attributes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
