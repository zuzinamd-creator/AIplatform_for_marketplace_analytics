import uuid

from sqlalchemy import Enum, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin
from app.models.report import Marketplace


class SKUMapping(Base, TenantMixin, TimestampMixin):
    __tablename__ = "sku_mapping"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "marketplace",
            "marketplace_sku",
            name="uq_sku_mapping_tenant_mp_sku",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    internal_sku: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    marketplace: Mapped[Marketplace] = mapped_column(
        Enum(Marketplace, name="marketplace_enum", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    marketplace_sku: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
