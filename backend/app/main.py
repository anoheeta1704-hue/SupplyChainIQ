# ============================================
# SupplyChainIQ — Main FastAPI Application
# ============================================
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog
import time

import asyncio
from app.core.config import settings
from app.core.database import init_db
from app.core.redis import get_redis, close_redis, RedisCache
from app.api import auth, shipments, dashboard, predictions, tracking_ws
from app.services.simulator import simulator

logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("startup", app_name=settings.APP_NAME, env=settings.APP_ENV)
    
    # Initialize DB tables
    await init_db()
    logger.info("db_initialized")
    
    # Warm up Redis connection
    await get_redis()
    logger.info("redis_connected")

    # Start simulation loop in background
    sim_task = asyncio.create_task(simulator.loop())
    logger.info("simulator_loop_started")
    
    yield
    
    # Shutdown
    sim_task.cancel()
    await close_redis()
    logger.info("shutdown")


app = FastAPI(
    title=settings.APP_NAME,
    description="Supply Chain Visibility & Delay Prediction Platform API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate Limiting Middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    
    # Skip rate limiting for static assets, health checks, simulator endpoints, or in development for localhost
    if request.url.path.startswith("/api/"):
        is_dev_local = settings.APP_ENV != "production" and client_ip in ["127.0.0.1", "localhost", "::1", "unknown"]
        is_sim = request.url.path.startswith("/api/simulator")
        if not is_dev_local and not is_sim:
            allowed = await RedisCache.check_rate_limit(
                client_ip, 
                limit=settings.RATE_LIMIT_PER_MINUTE,
                window=60
            )
            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Please try again later."},
                )
            
    # Time the request
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    # Simple access log (structlog is better configured in production)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        logger.info(
            "request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration=round(process_time * 1000, 2),
            ip=client_ip
        )
        
    return response

# Include Routers
app.include_router(auth.router)
app.include_router(shipments.router)
app.include_router(dashboard.router)
app.include_router(predictions.router)
app.include_router(tracking_ws.router)


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.APP_ENV}
