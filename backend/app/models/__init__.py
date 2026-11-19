# ============================================
# SupplyChainIQ — ORM Models (All operational tables)
# ============================================
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey,
    Index, Enum as SAEnum, Numeric
)
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


# ---- Enums ----

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    LOGISTICS_MANAGER = "logistics_manager"
    OPERATIONS_ANALYST = "operations_analyst"


class ShipmentStatus(str, enum.Enum):
    CREATED = "CREATED"
    PICKED_UP = "PICKED_UP"
    IN_TRANSIT = "IN_TRANSIT"
    AT_WAREHOUSE = "AT_WAREHOUSE"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    DELAYED = "DELAYED"
    CANCELLED = "CANCELLED"


class ShipmentType(str, enum.Enum):
    STANDARD = "STANDARD"
    EXPRESS = "EXPRESS"
    SAME_DAY = "SAME_DAY"
    ECONOMY = "ECONOMY"
    FRAGILE = "FRAGILE"
    BULK = "BULK"


class EventType(str, enum.Enum):
    ORDER_CREATED = "ORDER_CREATED"
    PICKED_UP = "PICKED_UP"
    ARRIVED_WAREHOUSE = "ARRIVED_WAREHOUSE"
    DEPARTED_WAREHOUSE = "DEPARTED_WAREHOUSE"
    IN_TRANSIT = "IN_TRANSIT"
    WEATHER_DELAY = "WEATHER_DELAY"
    TRAFFIC_DELAY = "TRAFFIC_DELAY"
    CUSTOMS_HOLD = "CUSTOMS_HOLD"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    FAILED_DELIVERY = "FAILED_DELIVERY"
    RETURNED = "RETURNED"


class AlertSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ---- Helper ----

def utcnow():
    return datetime.now(timezone.utc)


# ============================================
# Operational Tables
# ============================================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default=UserRole.OPERATIONS_ANALYST.value)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=True)
    phone = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    shipments = relationship("Shipment", back_populates="customer")


class Carrier(Base):
    __tablename__ = "carriers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    code = Column(String(50), nullable=False, unique=True)
    service_type = Column(String(100), nullable=True)
    rating = Column(Float, default=4.0)
    on_time_rate = Column(Float, default=0.85)
    avg_delay_hours = Column(Float, default=0.0)
    total_shipments = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    shipments = relationship("Shipment", back_populates="carrier")


class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=False, unique=True)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    capacity = Column(Integer, default=1000)
    current_utilization = Column(Float, default=0.5)  # 0.0 to 1.0
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    shipments = relationship("Shipment", back_populates="warehouse")


class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True, index=True)
    tracking_number = Column(String(50), unique=True, nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    carrier_id = Column(Integer, ForeignKey("carriers.id"), nullable=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)

    origin = Column(String(255), nullable=False)
    destination = Column(String(255), nullable=False)
    shipment_type = Column(String(50), default=ShipmentType.STANDARD.value)

    package_weight = Column(Float, nullable=True)  # kg
    package_value = Column(Numeric(12, 2), nullable=True)  # INR

    expected_delivery = Column(DateTime(timezone=True), nullable=True)
    actual_delivery = Column(DateTime(timezone=True), nullable=True)

    status = Column(String(50), default=ShipmentStatus.CREATED.value, index=True)
    current_location = Column(String(255), nullable=True)
    current_latitude = Column(Float, nullable=True)
    current_longitude = Column(Float, nullable=True)

    distance_km = Column(Float, nullable=True)

    # ML prediction fields
    delay_probability = Column(Float, nullable=True)
    predicted_delay_hours = Column(Float, nullable=True)
    risk_level = Column(String(20), nullable=True)  # LOW, MEDIUM, HIGH

    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    customer = relationship("Customer", back_populates="shipments")
    carrier = relationship("Carrier", back_populates="shipments")
    warehouse = relationship("Warehouse", back_populates="shipments")
    events = relationship("ShipmentEvent", back_populates="shipment", order_by="ShipmentEvent.timestamp")
    alerts = relationship("Alert", back_populates="shipment")

    __table_args__ = (
        Index("ix_shipments_status_created", "status", "created_at"),
        Index("ix_shipments_origin_dest", "origin", "destination"),
        Index("ix_shipments_carrier_status", "carrier_id", "status"),
    )


class ShipmentEvent(Base):
    __tablename__ = "shipment_events"

    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)
    location = Column(String(255), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=utcnow, index=True)
    description = Column(Text, nullable=True)
    source = Column(String(100), nullable=True)  # carrier_api, warehouse_system, etc.

    shipment = relationship("Shipment", back_populates="events")

    __table_args__ = (
        Index("ix_events_shipment_time", "shipment_id", "timestamp"),
    )


class WeatherData(Base):
    __tablename__ = "weather_data"

    id = Column(Integer, primary_key=True, index=True)
    location = Column(String(255), nullable=False, index=True)
    temperature = Column(Float, nullable=True)
    rainfall = Column(Float, nullable=True)  # mm
    humidity = Column(Float, nullable=True)
    wind_speed = Column(Float, nullable=True)  # km/h
    weather_condition = Column(String(100), nullable=True)  # Clear, Rainy, Foggy, Storm
    timestamp = Column(DateTime(timezone=True), default=utcnow, index=True)


class RouteData(Base):
    __tablename__ = "route_data"

    id = Column(Integer, primary_key=True, index=True)
    origin = Column(String(255), nullable=False)
    destination = Column(String(255), nullable=False)
    distance_km = Column(Float, nullable=False)
    avg_transit_hours = Column(Float, nullable=True)
    traffic_level = Column(String(20), nullable=True)  # LOW, MEDIUM, HIGH
    route_type = Column(String(50), nullable=True)  # HIGHWAY, MIXED, URBAN
    historical_delay_rate = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)

    __table_args__ = (
        Index("ix_route_origin_dest", "origin", "destination"),
    )


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=False, index=True)
    severity = Column(String(20), nullable=False, default=AlertSeverity.MEDIUM.value)
    title = Column(String(500), nullable=False)
    message = Column(Text, nullable=True)
    delay_probability = Column(Float, nullable=True)
    predicted_delay_hours = Column(Float, nullable=True)
    contributing_factors = Column(Text, nullable=True)  # JSON string
    is_read = Column(Boolean, default=False)
    is_resolved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)

    shipment = relationship("Shipment", back_populates="alerts")


# ============================================
# Data Warehouse Tables (Star Schema)
# ============================================
# NOTE: These ORM models mirror the ETL-created schema exactly.
# The ETL pipeline (etl/pipeline.py) drops & recreates these tables,
# so these models are only used for ORM reads / metadata reflection.
from app.core.database import active_db_url

def _wh_schema():
    return {"schema": "warehouse"} if "postgres" in active_db_url else {}

def _wh_fk(target: str) -> str:
    if "postgres" in active_db_url:
        return target
    prefix = "warehouse."
    return target[len(prefix):] if target.startswith(prefix) else target


class DimShipment(Base):
    __tablename__ = "dim_shipment"
    __table_args__ = {"extend_existing": True, **_wh_schema()}

    shipment_key = Column(Integer, primary_key=True, autoincrement=True)
    shipment_id = Column(String(50), nullable=False, index=True)
    tracking_number = Column(String(50), nullable=True, unique=True)
    shipment_type = Column(String(50), nullable=True)
    package_weight_category = Column(String(20), nullable=True)


class DimCarrier(Base):
    __tablename__ = "dim_carrier"
    __table_args__ = {"extend_existing": True, **_wh_schema()}

    carrier_key = Column(Integer, primary_key=True, autoincrement=True)
    carrier_name = Column(String(100), nullable=False, unique=True)
    carrier_code = Column(String(10), nullable=True)


class DimRoute(Base):
    __tablename__ = "dim_route"
    __table_args__ = {"extend_existing": True, **_wh_schema()}

    route_key = Column(Integer, primary_key=True, autoincrement=True)
    origin = Column(String(100), nullable=False)
    destination = Column(String(100), nullable=False)
    distance_km = Column(Float, nullable=True)


class DimWarehouse(Base):
    __tablename__ = "dim_warehouse"
    __table_args__ = {"extend_existing": True, **_wh_schema()}

    warehouse_key = Column(Integer, primary_key=True, autoincrement=True)
    warehouse_code = Column(String(50), nullable=False, unique=True)
    warehouse_name = Column(String(100), nullable=True)


class DimTime(Base):
    __tablename__ = "dim_time"
    __table_args__ = {"extend_existing": True, **_wh_schema()}

    time_key = Column(Integer, primary_key=True, autoincrement=True)
    full_date = Column(DateTime, nullable=False, unique=True, index=True)
    day = Column(Integer, nullable=True)
    month = Column(Integer, nullable=True)
    year = Column(Integer, nullable=True)
    quarter = Column(Integer, nullable=True)
    day_of_week = Column(Integer, nullable=True)
    day_name = Column(String(20), nullable=True)
    month_name = Column(String(20), nullable=True)
    week_of_year = Column(Integer, nullable=True)
    is_weekend = Column(Boolean, nullable=True)
    season = Column(String(20), nullable=True)


class DimWeather(Base):
    __tablename__ = "dim_weather"
    __table_args__ = {"extend_existing": True, **_wh_schema()}

    weather_key = Column(Integer, primary_key=True, autoincrement=True)
    condition = Column(String(50), nullable=False)
    traffic_level = Column(String(50), nullable=True)
    rainfall_level = Column(String(20), nullable=True)
    temperature_range = Column(String(20), nullable=True)


class FactShipmentEvent(Base):
    __tablename__ = "fact_shipment_events"
    __table_args__ = {"extend_existing": True, **_wh_schema()}

    fact_id = Column(Integer, primary_key=True, autoincrement=True)
    shipment_key = Column(Integer, nullable=True)
    carrier_key = Column(Integer, nullable=True)
    route_key = Column(Integer, nullable=True)
    warehouse_key = Column(Integer, nullable=True)
    time_key = Column(Integer, nullable=True)
    weather_key = Column(Integer, nullable=True)

    # Measures
    distance_km = Column(Float, nullable=True)
    delivery_duration_hours = Column(Float, nullable=True)
    delay_hours = Column(Float, nullable=True)
    is_delayed = Column(Boolean, nullable=True)
    package_weight = Column(Float, nullable=True)
    delay_probability = Column(Float, nullable=True)
    risk_level = Column(String(20), nullable=True)

