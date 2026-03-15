import uuid

from sqlalchemy import CheckConstraint, Column, DateTime, Double, ForeignKey, Numeric, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending_payment', 'paid', 'failed_payment', 'cancelled')",
            name="ck_orders_status",
        ),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
        default=uuid.uuid4,
    )
    customer_id = Column(Text, nullable=False)
    shipping_address = Column(Text, nullable=False)
    shipping_lat = Column(Double, nullable=False)
    shipping_lng = Column(Double, nullable=False)
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=False)
    status = Column(Text, nullable=False)
    total_amount = Column(Numeric(12, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    warehouse = relationship("Warehouse", back_populates="orders", lazy="selectin")
    items = relationship("OrderItem", back_populates="order", lazy="selectin")
    payments = relationship("Payment", back_populates="order", lazy="selectin")
