# ============================================
# SupplyChainIQ — Pydantic Schemas
# ============================================
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from enum import Enum


# ---- Auth ----

class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: str
    password: str = Field(..., min_length=6)
    role: str = "operations_analyst"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ---- Customer ----

class CustomerResponse(BaseModel):
    id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None

    class Config:
        from_attributes = True


# ---- Carrier ----

class CarrierResponse(BaseModel):
    id: int
    name: str
    code: str
    service_type: Optional[str] = None
    rating: Optional[float] = None
    on_time_rate: Optional[float] = None
    avg_delay_hours: Optional[float] = None
    total_shipments: int = 0
    is_active: bool = True

    class Config:
        from_attributes = True


class CarrierAnalytics(BaseModel):
    carrier: CarrierResponse
    total_shipments: int
    delayed_shipments: int
    delay_rate: float
    avg_delay_hours: float
    on_time_rate: float


# ---- Warehouse ----

class WarehouseResponse(BaseModel):
    id: int
    name: str
    code: str
    city: str
    state: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    capacity: int = 1000
    current_utilization: float = 0.5
    is_active: bool = True

    class Config:
        from_attributes = True


class WarehouseAnalytics(BaseModel):
    warehouse: WarehouseResponse
    total_shipments: int
    delayed_shipments: int
    avg_processing_hours: float
    utilization_pct: float


# ---- Route ----

class RouteResponse(BaseModel):
    id: int
    origin: str
    destination: str
    distance_km: float
    avg_transit_hours: Optional[float] = None
    traffic_level: Optional[str] = None
    route_type: Optional[str] = None
    historical_delay_rate: float = 0.0

    class Config:
        from_attributes = True


class RouteAnalytics(BaseModel):
    route: RouteResponse
    total_shipments: int
    delayed_shipments: int
    delay_rate: float
    avg_delay_hours: float


# ---- Shipment Event ----

class ShipmentEventResponse(BaseModel):
    id: int
    shipment_id: int
    event_type: str
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timestamp: datetime
    description: Optional[str] = None
    source: Optional[str] = None

    class Config:
        from_attributes = True


class ShipmentEventCreate(BaseModel):
    event_type: str
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    description: Optional[str] = None
    source: Optional[str] = "manual"


# ---- Shipment ----

class ShipmentCreate(BaseModel):
    tracking_number: Optional[str] = None
    customer_id: Optional[int] = None
    carrier_id: Optional[int] = None
    warehouse_id: Optional[int] = None
    origin: str
    destination: str
    shipment_type: str = "STANDARD"
    package_weight: Optional[float] = None
    package_value: Optional[float] = None
    expected_delivery: Optional[datetime] = None


class ShipmentResponse(BaseModel):
    id: int
    tracking_number: str
    customer_id: Optional[int] = None
    carrier_id: Optional[int] = None
    warehouse_id: Optional[int] = None
    origin: str
    destination: str
    shipment_type: Optional[str] = None
    package_weight: Optional[float] = None
    package_value: Optional[float] = None
    expected_delivery: Optional[datetime] = None
    actual_delivery: Optional[datetime] = None
    status: str
    current_location: Optional[str] = None
    current_latitude: Optional[float] = None
    current_longitude: Optional[float] = None
    distance_km: Optional[float] = None
    delay_probability: Optional[float] = None
    predicted_delay_hours: Optional[float] = None
    risk_level: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    # Nested
    carrier: Optional[CarrierResponse] = None
    warehouse: Optional[WarehouseResponse] = None

    class Config:
        from_attributes = True


class ShipmentDetailResponse(ShipmentResponse):
    events: List[ShipmentEventResponse] = []
    customer: Optional[CustomerResponse] = None
    prediction_explanation: Optional[dict] = None


class ShipmentListResponse(BaseModel):
    items: List[ShipmentResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ---- Dashboard ----

class DashboardKPIs(BaseModel):
    total_shipments: int = 0
    active_shipments: int = 0
    in_transit: int = 0
    delivered: int = 0
    delayed: int = 0
    high_risk: int = 0
    avg_delivery_hours: float = 0.0
    on_time_rate: float = 0.0
    active_carriers: int = 0
    active_warehouses: int = 0
    avg_delay_hours: float = 0.0
    shipments_today: int = 0


class StatusDistribution(BaseModel):
    status: str
    count: int


class DashboardResponse(BaseModel):
    kpis: DashboardKPIs
    status_distribution: List[StatusDistribution] = []
    recent_alerts: List["AlertResponse"] = []
    delay_trend: List[dict] = []
    carrier_performance: List[dict] = []


# ---- Alerts ----

class AlertResponse(BaseModel):
    id: int
    shipment_id: int
    severity: str
    title: str
    message: Optional[str] = None
    delay_probability: Optional[float] = None
    predicted_delay_hours: Optional[float] = None
    contributing_factors: Optional[str] = None
    is_read: bool = False
    is_resolved: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class AlertListResponse(BaseModel):
    items: List[AlertResponse]
    total: int
    page: int
    page_size: int


# ---- ML Prediction ----

class PredictionRequest(BaseModel):
    carrier_id: Optional[int] = None
    carrier_name: Optional[str] = None
    origin: str
    destination: str
    distance_km: Optional[float] = None
    warehouse_id: Optional[int] = None
    package_weight: Optional[float] = None
    weather_condition: Optional[str] = None
    rainfall: Optional[float] = None
    temperature: Optional[float] = None
    traffic_level: Optional[str] = None
    day_of_week: Optional[int] = None
    month: Optional[int] = None
    shipment_type: Optional[str] = "STANDARD"


class PredictionResponse(BaseModel):
    delay_probability: float
    is_delayed: bool
    risk_level: str  # LOW, MEDIUM, HIGH
    predicted_delay_hours: Optional[float] = None
    contributing_factors: List[dict] = []
    model_version: str = "1.0"


class BatchPredictionRequest(BaseModel):
    shipments: List[PredictionRequest]


class BatchPredictionResponse(BaseModel):
    predictions: List[PredictionResponse]
    total: int


class ModelPerformanceResponse(BaseModel):
    classifier: dict  # accuracy, precision, recall, f1, roc_auc, confusion_matrix
    regressor: Optional[dict] = None  # mae, rmse, r2
    models_comparison: Optional[List[dict]] = None
    champion_model: Optional[str] = None
    feature_importance: List[dict] = []
    training_date: Optional[str] = None
    training_samples: Optional[int] = None
    model_version: str = "1.0"


# ---- Analytics ----

class AnalyticsFilter(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    carrier_id: Optional[int] = None
    origin: Optional[str] = None
    destination: Optional[str] = None
    status: Optional[str] = None


# ---- Pagination ----

class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 20
    sort_by: str = "created_at"
    sort_order: str = "desc"
