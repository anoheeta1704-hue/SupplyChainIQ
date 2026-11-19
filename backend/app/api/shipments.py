# ============================================
# SupplyChainIQ — Shipments API
# ============================================
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_, desc, asc
from sqlalchemy.orm import selectinload
from typing import Optional
from datetime import datetime, timezone
import uuid

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.redis import RedisCache
from app.models import Shipment, ShipmentEvent, Carrier, Warehouse, Customer
from app.schemas import (
    ShipmentResponse, ShipmentDetailResponse, ShipmentListResponse,
    ShipmentCreate, ShipmentEventResponse, ShipmentEventCreate,
    CarrierResponse, WarehouseResponse, CustomerResponse,
)
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/api/shipments", tags=["Shipments"])


def _generate_tracking_number() -> str:
    return f"SH{uuid.uuid4().hex[:8].upper()}"


@router.get("", response_model=ShipmentListResponse)
async def list_shipments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    carrier_id: Optional[int] = None,
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    risk_level: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = Query("created_at", regex="^(created_at|tracking_number|status|origin|destination|delay_probability)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List shipments with filtering, sorting, and pagination."""
    query = select(Shipment).options(
        selectinload(Shipment.carrier),
        selectinload(Shipment.warehouse),
    )

    # Filters
    conditions = []
    if status:
        conditions.append(Shipment.status == status)
    if carrier_id:
        conditions.append(Shipment.carrier_id == carrier_id)
    if origin:
        conditions.append(Shipment.origin.ilike(f"%{origin}%"))
    if destination:
        conditions.append(Shipment.destination.ilike(f"%{destination}%"))
    if risk_level:
        conditions.append(Shipment.risk_level == risk_level)
    if search:
        conditions.append(
            or_(
                Shipment.tracking_number.ilike(f"%{search}%"),
                Shipment.origin.ilike(f"%{search}%"),
                Shipment.destination.ilike(f"%{search}%"),
                Shipment.current_location.ilike(f"%{search}%"),
            )
        )

    if conditions:
        query = query.where(and_(*conditions))

    # Count
    count_query = select(func.count()).select_from(Shipment)
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Sort
    sort_col = getattr(Shipment, sort_by, Shipment.created_at)
    order_func = desc if sort_order == "desc" else asc
    query = query.order_by(order_func(sort_col))

    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    shipments = result.scalars().all()

    items = []
    for s in shipments:
        resp = ShipmentResponse.model_validate(s)
        if s.carrier:
            resp.carrier = CarrierResponse.model_validate(s.carrier)
        if s.warehouse:
            resp.warehouse = WarehouseResponse.model_validate(s.warehouse)
        items.append(resp)

    pages = max(1, (total + page_size - 1) // page_size)

    return ShipmentListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/routes")
async def get_shipment_routes():
    """Get all pre-computed route waypoints for map rendering."""
    from app.services.simulator import INDIAN_ROUTES
    return INDIAN_ROUTES


@router.get("/{shipment_id}", response_model=ShipmentDetailResponse)
async def get_shipment(
    shipment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get detailed shipment information including events timeline."""
    # Try Redis cache first
    cached = await RedisCache.get_shipment_status(str(shipment_id))

    result = await db.execute(
        select(Shipment)
        .options(
            selectinload(Shipment.carrier),
            selectinload(Shipment.warehouse),
            selectinload(Shipment.customer),
            selectinload(Shipment.events),
        )
        .where(Shipment.id == shipment_id)
    )
    shipment = result.scalar_one_or_none()

    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    resp = ShipmentDetailResponse.model_validate(shipment)
    if shipment.carrier:
        resp.carrier = CarrierResponse.model_validate(shipment.carrier)
    if shipment.warehouse:
        resp.warehouse = WarehouseResponse.model_validate(shipment.warehouse)
    if shipment.customer:
        resp.customer = CustomerResponse.model_validate(shipment.customer)
    resp.events = [ShipmentEventResponse.model_validate(e) for e in shipment.events]

    # Cache the status
    await RedisCache.set_shipment_status(str(shipment_id), {
        "status": shipment.status,
        "current_location": shipment.current_location,
        "delay_probability": shipment.delay_probability,
        "risk_level": shipment.risk_level,
        "updated_at": str(shipment.updated_at),
    })

    return resp


@router.post("", response_model=ShipmentResponse, status_code=status.HTTP_201_CREATED)
async def create_shipment(
    req: ShipmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create a new shipment."""
    from app.services.simulator import simulator
    waypoints = simulator.get_route_waypoints(req.origin, req.destination)
    init_lat = waypoints[0]["lat"] if waypoints else None
    init_lng = waypoints[0]["lng"] if waypoints else None

    shipment = Shipment(
        tracking_number=req.tracking_number or _generate_tracking_number(),
        customer_id=req.customer_id,
        carrier_id=req.carrier_id,
        warehouse_id=req.warehouse_id,
        origin=req.origin,
        destination=req.destination,
        shipment_type=req.shipment_type,
        package_weight=req.package_weight,
        package_value=req.package_value,
        expected_delivery=req.expected_delivery,
        status="CREATED",
        current_location=f"{req.origin} Origin Facility",
        current_latitude=init_lat,
        current_longitude=init_lng,
        distance_km=1200.0,
        delay_probability=0.15,
        risk_level="LOW",
    )
    db.add(shipment)
    await db.flush()
    await db.refresh(shipment)


    # Create initial event
    event = ShipmentEvent(
        shipment_id=shipment.id,
        event_type="ORDER_CREATED",
        location=req.origin,
        description=f"Shipment {shipment.tracking_number} created",
        source="system",
    )
    db.add(event)

    logger.info("shipment_created", tracking_number=shipment.tracking_number)
    return ShipmentResponse.model_validate(shipment)


@router.get("/{shipment_id}/events", response_model=list[ShipmentEventResponse])
async def get_shipment_events(
    shipment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get the event timeline for a shipment."""
    result = await db.execute(
        select(ShipmentEvent)
        .where(ShipmentEvent.shipment_id == shipment_id)
        .order_by(ShipmentEvent.timestamp.asc())
    )
    events = result.scalars().all()
    return [ShipmentEventResponse.model_validate(e) for e in events]


@router.post("/{shipment_id}/events", response_model=ShipmentEventResponse, status_code=201)
async def add_shipment_event(
    shipment_id: int,
    req: ShipmentEventCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Add a tracking event to a shipment and update status."""
    # Verify shipment exists
    result = await db.execute(select(Shipment).where(Shipment.id == shipment_id))
    shipment = result.scalar_one_or_none()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    event = ShipmentEvent(
        shipment_id=shipment_id,
        event_type=req.event_type,
        location=req.location,
        latitude=req.latitude,
        longitude=req.longitude,
        description=req.description,
        source=req.source,
    )
    db.add(event)

    # Update shipment status based on event
    event_to_status = {
        "PICKED_UP": "PICKED_UP",
        "IN_TRANSIT": "IN_TRANSIT",
        "ARRIVED_WAREHOUSE": "AT_WAREHOUSE",
        "DEPARTED_WAREHOUSE": "IN_TRANSIT",
        "OUT_FOR_DELIVERY": "OUT_FOR_DELIVERY",
        "DELIVERED": "DELIVERED",
        "WEATHER_DELAY": "DELAYED",
        "TRAFFIC_DELAY": "DELAYED",
        "FAILED_DELIVERY": "DELAYED",
    }

    new_status = event_to_status.get(req.event_type)
    if new_status:
        shipment.status = new_status
    if req.location:
        shipment.current_location = req.location
    if req.latitude:
        shipment.current_latitude = req.latitude
    if req.longitude:
        shipment.current_longitude = req.longitude

    if req.event_type == "DELIVERED":
        shipment.actual_delivery = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(event)

    # Invalidate Redis cache
    await RedisCache.delete(f"shipment:{shipment_id}:status")
    await RedisCache.delete("dashboard:kpis")

    logger.info("shipment_event_added", shipment_id=shipment_id, event_type=req.event_type)
    return ShipmentEventResponse.model_validate(event)
