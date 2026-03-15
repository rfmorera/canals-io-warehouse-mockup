import uuid

from geoalchemy2 import Geography
from sqlalchemy import Boolean, Column, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base


class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
        default=uuid.uuid4,
    )
    name = Column(Text, nullable=False)
    address = Column(Text, nullable=False)
    location = Column(Geography(geometry_type="Point", srid=4326), nullable=False)
    active = Column(Boolean, nullable=False, default=True, server_default="true")

    inventory = relationship("WarehouseInventory", back_populates="warehouse", lazy="selectin")
    orders = relationship("Order", back_populates="warehouse", lazy="selectin")
