import uuid

from sqlalchemy import Column, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
        default=uuid.uuid4,
    )
    sku = Column(Text, nullable=False, unique=True)
    name = Column(Text, nullable=False)
    manufacturer_country = Column(String(2), nullable=False)

    inventory = relationship("WarehouseInventory", back_populates="product", lazy="selectin")
    order_items = relationship("OrderItem", back_populates="product", lazy="selectin")
