# ============================================
# SupplyChainIQ — Dashboard & Analytics API
# ============================================
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, and_, extract, cast, Date
from typing import Optional
from datetime import datetime, timedelta, timezone

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.redis import RedisCache
from app.models import Shipment, Carrier, Warehouse, ShipmentEvent, Alert
from app.schemas import (
    DashboardKPIs, DashboardResponse, StatusDistribution,
    AlertResponse, CarrierAnalytics, CarrierResponse,
    RouteAnalytics, RouteResponse, WarehouseAnalytics, WarehouseResponse,
)
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/api", tags=["Dashboard & Analytics"])


@router.get("/dashboard/kpis", response_model=DashboardResponse)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get dashboard KPIs, status distribution, recent alerts, and trends."""
    # Try cache
    cached = await RedisCache.get_dashboard_kpis()
    if cached:
        return DashboardResponse(**cached)

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Total shipments
    total = (await db.execute(select(func.count(Shipment.id)))).scalar() or 0

    # Status counts
    status_counts = {}
    result = await db.execute(
        select(Shipment.status, func.count(Shipment.id))
        .group_by(Shipment.status)
    )
    for row in result:
        status_counts[row[0]] = row[1]

    active_statuses = {"CREATED", "PICKED_UP", "IN_TRANSIT", "AT_WAREHOUSE", "OUT_FOR_DELIVERY", "DELAYED"}
    active = sum(status_counts.get(s, 0) for s in active_statuses)
    in_transit = status_counts.get("IN_TRANSIT", 0)
    delivered = status_counts.get("DELIVERED", 0)
    delayed = status_counts.get("DELAYED", 0)

    # High risk shipments
    high_risk = (await db.execute(
        select(func.count(Shipment.id)).where(Shipment.risk_level == "HIGH")
    )).scalar() or 0

    # Average delivery time (for delivered shipments)
    avg_delivery = (await db.execute(
        select(func.avg(
            extract("epoch", Shipment.actual_delivery - Shipment.created_at) / 3600
        )).where(
            and_(
                Shipment.status == "DELIVERED",
                Shipment.actual_delivery.isnot(None),
            )
        )
    )).scalar() or 0.0

    # On-time rate
    delivered_total = max(delivered, 1)
    on_time_count = (await db.execute(
        select(func.count(Shipment.id)).where(
            and_(
                Shipment.status == "DELIVERED",
                Shipment.actual_delivery <= Shipment.expected_delivery,
            )
        )
    )).scalar() or 0
    on_time_rate = on_time_count / delivered_total if delivered_total > 0 else 0.0

    # Active carriers and warehouses
    active_carriers = (await db.execute(
        select(func.count(Carrier.id)).where(Carrier.is_active == True)
    )).scalar() or 0

    active_warehouses = (await db.execute(
        select(func.count(Warehouse.id)).where(Warehouse.is_active == True)
    )).scalar() or 0

    # Average delay hours for delayed shipments
    avg_delay = (await db.execute(
        select(func.avg(Shipment.predicted_delay_hours)).where(
            Shipment.status == "DELAYED"
        )
    )).scalar() or 0.0

    # Shipments today
    shipments_today = (await db.execute(
        select(func.count(Shipment.id)).where(Shipment.created_at >= today_start)
    )).scalar() or 0

    kpis = DashboardKPIs(
        total_shipments=total,
        active_shipments=active,
        in_transit=in_transit,
        delivered=delivered,
        delayed=delayed,
        high_risk=high_risk,
        avg_delivery_hours=round(float(avg_delivery), 1),
        on_time_rate=round(float(on_time_rate), 3),
        active_carriers=active_carriers,
        active_warehouses=active_warehouses,
        avg_delay_hours=round(float(avg_delay), 1),
        shipments_today=shipments_today,
    )

    # Status distribution
    status_dist = [
        StatusDistribution(status=s, count=c)
        for s, c in status_counts.items()
    ]

    # Recent alerts
    alert_result = await db.execute(
        select(Alert)
        .order_by(Alert.created_at.desc())
        .limit(10)
    )
    recent_alerts = [AlertResponse.model_validate(a) for a in alert_result.scalars().all()]

    # Delay trend (last 30 days)
    delay_trend = []
    for i in range(30, -1, -1):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        day_total = (await db.execute(
            select(func.count(Shipment.id)).where(
                and_(Shipment.created_at >= day_start, Shipment.created_at < day_end)
            )
        )).scalar() or 0

        day_delayed = (await db.execute(
            select(func.count(Shipment.id)).where(
                and_(
                    Shipment.created_at >= day_start,
                    Shipment.created_at < day_end,
                    Shipment.risk_level.in_(["HIGH", "MEDIUM"]),
                )
            )
        )).scalar() or 0

        delay_trend.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "total": day_total,
            "delayed": day_delayed,
        })

    # Carrier performance summary
    carrier_perf_result = await db.execute(
        select(
            Carrier.name,
            func.count(Shipment.id).label("total"),
            func.sum(case((Shipment.status == "DELAYED", 1), else_=0)).label("delayed"),
        )
        .join(Shipment, Shipment.carrier_id == Carrier.id)
        .group_by(Carrier.name)
        .order_by(func.count(Shipment.id).desc())
        .limit(10)
    )
    carrier_performance = []
    for row in carrier_perf_result:
        t = row[1] or 1
        carrier_performance.append({
            "carrier": row[0],
            "total": row[1],
            "delayed": row[2] or 0,
            "delay_rate": round((row[2] or 0) / t, 3),
        })

    response = DashboardResponse(
        kpis=kpis,
        status_distribution=status_dist,
        recent_alerts=recent_alerts,
        delay_trend=delay_trend,
        carrier_performance=carrier_performance,
    )

    # Cache for 2 minutes
    await RedisCache.set_dashboard_kpis(response.model_dump())

    return response


# ---- Carrier Analytics ----

@router.get("/carriers", response_model=list[CarrierResponse])
async def list_carriers(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(Carrier).order_by(Carrier.name))
    return [CarrierResponse.model_validate(c) for c in result.scalars().all()]


@router.get("/analytics/carriers", response_model=list[CarrierAnalytics])
async def get_carrier_analytics(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get performance analytics for all carriers."""
    result = await db.execute(
        select(
            Carrier,
            func.count(Shipment.id).label("total"),
            func.sum(case((Shipment.status == "DELAYED", 1), else_=0)).label("delayed"),
            func.avg(Shipment.predicted_delay_hours).label("avg_delay"),
        )
        .outerjoin(Shipment, Shipment.carrier_id == Carrier.id)
        .group_by(Carrier.id)
        .order_by(func.count(Shipment.id).desc())
    )

    analytics = []
    for row in result:
        carrier = row[0]
        total = row[1] or 0
        delayed = row[2] or 0
        avg_delay = float(row[3] or 0)
        delay_rate = delayed / max(total, 1)

        analytics.append(CarrierAnalytics(
            carrier=CarrierResponse.model_validate(carrier),
            total_shipments=total,
            delayed_shipments=delayed,
            delay_rate=round(delay_rate, 3),
            avg_delay_hours=round(avg_delay, 1),
            on_time_rate=round(1 - delay_rate, 3),
        ))

    return analytics


# ---- Warehouse Analytics ----

@router.get("/warehouses", response_model=list[WarehouseResponse])
async def list_warehouses(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(Warehouse).order_by(Warehouse.name))
    return [WarehouseResponse.model_validate(w) for w in result.scalars().all()]


@router.get("/analytics/warehouses", response_model=list[WarehouseAnalytics])
async def get_warehouse_analytics(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get performance analytics for all warehouses."""
    result = await db.execute(
        select(
            Warehouse,
            func.count(Shipment.id).label("total"),
            func.sum(case((Shipment.status == "DELAYED", 1), else_=0)).label("delayed"),
        )
        .outerjoin(Shipment, Shipment.warehouse_id == Warehouse.id)
        .group_by(Warehouse.id)
        .order_by(func.count(Shipment.id).desc())
    )

    analytics = []
    for row in result:
        wh = row[0]
        total = row[1] or 0
        delayed = row[2] or 0

        analytics.append(WarehouseAnalytics(
            warehouse=WarehouseResponse.model_validate(wh),
            total_shipments=total,
            delayed_shipments=delayed,
            avg_processing_hours=round(wh.current_utilization * 12, 1),
            utilization_pct=round(wh.current_utilization * 100, 1),
        ))

    return analytics


# ---- Route Analytics ----

@router.get("/routes")
async def list_routes(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from app.models import RouteData
    result = await db.execute(select(RouteData).order_by(RouteData.origin))
    routes = result.scalars().all()
    return [
        {
            "id": r.id,
            "origin": r.origin,
            "destination": r.destination,
            "distance_km": r.distance_km,
            "avg_transit_hours": r.avg_transit_hours,
            "traffic_level": r.traffic_level,
            "route_type": r.route_type,
            "historical_delay_rate": r.historical_delay_rate,
        }
        for r in routes
    ]


@router.get("/analytics/routes")
async def get_route_analytics(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get delay analytics by route."""
    result = await db.execute(
        select(
            Shipment.origin,
            Shipment.destination,
            func.count(Shipment.id).label("total"),
            func.sum(case((Shipment.status == "DELAYED", 1), else_=0)).label("delayed"),
            func.avg(Shipment.predicted_delay_hours).label("avg_delay"),
            func.avg(Shipment.distance_km).label("avg_distance"),
        )
        .group_by(Shipment.origin, Shipment.destination)
        .having(func.count(Shipment.id) >= 5)
        .order_by(func.count(Shipment.id).desc())
        .limit(50)
    )

    routes = []
    for row in result:
        total = row[2] or 1
        delayed = row[3] or 0
        routes.append({
            "origin": row[0],
            "destination": row[1],
            "total_shipments": total,
            "delayed_shipments": delayed,
            "delay_rate": round(delayed / total, 3),
            "avg_delay_hours": round(float(row[4] or 0), 1),
            "avg_distance_km": round(float(row[5] or 0), 0),
        })

    return routes


# ---- Alerts ----

@router.get("/alerts")
async def list_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    severity: Optional[str] = None,
    is_resolved: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List alerts with filtering and pagination."""
    query = select(Alert)

    conditions = []
    if severity:
        conditions.append(Alert.severity == severity)
    if is_resolved is not None:
        conditions.append(Alert.is_resolved == is_resolved)
    if conditions:
        query = query.where(and_(*conditions))

    total = (await db.execute(
        select(func.count(Alert.id)).where(and_(*conditions)) if conditions
        else select(func.count(Alert.id))
    )).scalar() or 0

    query = query.order_by(Alert.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    items = [AlertResponse.model_validate(a) for a in result.scalars().all()]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
