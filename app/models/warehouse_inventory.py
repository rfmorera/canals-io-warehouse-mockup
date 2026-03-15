from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base


class WarehouseInventory(Base):
    __tablename__ = "warehouse_inventory"
    __table_args__ = (
        CheckConstraint("available_qty >= 0", name="ck_warehouse_inventory_available_qty"),
        CheckConstraint("reserved_qty >= 0", name="ck_warehouse_inventory_reserved_qty"),
    )

    warehouse_id = Column(
        UUID(as_uuid=True), ForeignKey("warehouses.id"), primary_key=True, nullable=False
    )
    product_id = Column(
        UUID(as_uuid=True), ForeignKey("products.id"), primary_key=True, nullable=False
    )
    available_qty = Column(Integer, nullable=False, default=0, server_default="0")
    reserved_qty = Column(Integer, nullable=False, default=0, server_default="0")
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    warehouse = relationship("Warehouse", back_populates="inventory", lazy="selectin")
    product = relationship("Product", back_populates="inventory", lazy="selectin")
