# ============================================
# SupplyChainIQ — ML Prediction API
# ============================================
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional
import json

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models import Shipment, Alert
from app.schemas import (
    PredictionRequest, PredictionResponse,
    BatchPredictionRequest, BatchPredictionResponse,
    ModelPerformanceResponse,
)
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/api", tags=["ML Predictions"])

# ML model will be loaded lazily
_classifier = None
_regressor = None
_model_metadata = None


def _get_risk_level(probability: float) -> str:
    if probability >= settings.DELAY_THRESHOLD_HIGH:
        return "HIGH"
    elif probability >= settings.DELAY_THRESHOLD_LOW:
        return "MEDIUM"
    return "LOW"


def _get_model_dir():
    from pathlib import Path
    candidates = [
        Path(settings.MODEL_PATH),
        Path(__file__).resolve().parent.parent.parent.parent / "ml" / "models",
        Path(__file__).resolve().parent.parent.parent / "ml" / "models",
        Path("./ml/models"),
        Path("../ml/models"),
    ]
    for p in candidates:
        if (p / "metadata.json").exists():
            return p
    return Path(settings.MODEL_PATH)


def _load_models():
    """Lazy-load ML models from disk."""
    global _classifier, _regressor, _model_metadata
    if _classifier is not None:
        return

    import joblib
    from pathlib import Path

    model_dir = _get_model_dir()

    try:
        clf_path = model_dir / "delay_classifier" / "model.joblib"
        if clf_path.exists():
            _classifier = joblib.load(clf_path)
            logger.info("ml_model_loaded", model="classifier", path=str(clf_path))
        else:
            logger.warning("ml_model_not_found", model="classifier", path=str(clf_path))

        reg_path = model_dir / "delay_regressor" / "model.joblib"
        if reg_path.exists():
            _regressor = joblib.load(reg_path)
            logger.info("ml_model_loaded", model="regressor", path=str(reg_path))

        meta_path = model_dir / "metadata.json"
        if meta_path.exists():
            _model_metadata = json.loads(meta_path.read_text())

    except Exception as e:
        logger.error("ml_model_load_error", error=str(e))


def _build_features(req: PredictionRequest) -> dict:
    """Convert a prediction request into model features."""
    import numpy as np
    from datetime import datetime

    now = datetime.now()

    features = {
        "distance_km": req.distance_km or 500.0,
        "package_weight": req.package_weight or 5.0,
        "day_of_week": req.day_of_week if req.day_of_week is not None else now.weekday(),
        "month": req.month or now.month,
        "hour": now.hour,
        "is_weekend": 1 if (req.day_of_week if req.day_of_week is not None else now.weekday()) >= 5 else 0,
        "rainfall": req.rainfall or 0.0,
        "temperature": req.temperature or 30.0,
    }

    # Encode categorical features
    carrier_map = {
        "Delhivery": 0, "BlueDart": 1, "DTDC": 2, "Ecom Express": 3,
        "XpressBees": 4, "Shadowfax": 5, "Gati": 6, "Rivigo": 7,
        "SafeExpress": 8, "Spoton": 9
    }
    features["carrier_encoded"] = carrier_map.get(req.carrier_name, 0)

    weather_map = {"Clear": 0, "Cloudy": 1, "Rainy": 2, "Foggy": 3, "Storm": 4}
    features["weather_encoded"] = weather_map.get(req.weather_condition, 0)

    traffic_map = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
    features["traffic_encoded"] = traffic_map.get(req.traffic_level, 1)

    shipment_type_map = {"ECONOMY": 0, "STANDARD": 1, "EXPRESS": 2, "SAME_DAY": 3, "FRAGILE": 4, "BULK": 5}
    features["shipment_type_encoded"] = shipment_type_map.get(req.shipment_type, 1)

    # Season
    month = features["month"]
    if month in [6, 7, 8, 9]:
        features["season_encoded"] = 2  # Monsoon
    elif month in [11, 12, 1, 2]:
        features["season_encoded"] = 3  # Winter
    elif month in [3, 4, 5]:
        features["season_encoded"] = 1  # Summer
    else:
        features["season_encoded"] = 0  # Spring

    return features


def _predict_single(req: PredictionRequest) -> PredictionResponse:
    """Run prediction for a single shipment."""
    import numpy as np

    _load_models()
    features = _build_features(req)

    # Feature vector order must match training
    feature_names = [
        "distance_km", "package_weight", "day_of_week", "month", "hour",
        "is_weekend", "rainfall", "temperature", "carrier_encoded",
        "weather_encoded", "traffic_encoded", "shipment_type_encoded",
        "season_encoded",
    ]
    X = np.array([[features[f] for f in feature_names]])

    if _classifier is not None:
        delay_prob = float(_classifier.predict_proba(X)[0][1])
        is_delayed = delay_prob >= settings.DELAY_THRESHOLD_LOW
    else:
        # Heuristic fallback when model not trained yet
        delay_prob = _heuristic_delay_probability(features)
        is_delayed = delay_prob >= settings.DELAY_THRESHOLD_LOW

    risk_level = _get_risk_level(delay_prob)

    # Predicted delay hours
    predicted_hours = None
    if _regressor is not None and is_delayed:
        predicted_hours = max(0, float(_regressor.predict(X)[0]))
    elif is_delayed:
        predicted_hours = _heuristic_delay_hours(features, delay_prob)

    # Contributing factors
    factors = _compute_contributing_factors(features, delay_prob)

    return PredictionResponse(
        delay_probability=round(delay_prob, 3),
        is_delayed=is_delayed,
        risk_level=risk_level,
        predicted_delay_hours=round(predicted_hours, 1) if predicted_hours else None,
        contributing_factors=factors,
        model_version=_model_metadata.get("version", "1.0") if _model_metadata else "1.0",
    )


def _heuristic_delay_probability(features: dict) -> float:
    """Rule-based fallback when ML model isn't trained yet."""
    prob = 0.15  # Base probability

    if features["distance_km"] > 1500:
        prob += 0.15
    elif features["distance_km"] > 800:
        prob += 0.08

    if features["rainfall"] > 50:
        prob += 0.20
    elif features["rainfall"] > 20:
        prob += 0.10

    if features["weather_encoded"] >= 3:  # Foggy or Storm
        prob += 0.15

    if features["traffic_encoded"] == 2:  # HIGH
        prob += 0.10

    if features["season_encoded"] == 2:  # Monsoon
        prob += 0.12

    if features["is_weekend"]:
        prob += 0.05

    return min(prob, 0.98)


def _heuristic_delay_hours(features: dict, prob: float) -> float:
    """Estimate delay hours from features when regressor isn't trained."""
    base = prob * 20
    if features["distance_km"] > 1500:
        base += 8
    if features["rainfall"] > 50:
        base += 6
    if features["weather_encoded"] >= 3:
        base += 5
    return max(1.0, min(base, 72.0))


def _compute_contributing_factors(features: dict, prob: float) -> list:
    """Compute which features contributed most to the prediction."""
    factors = []

    if features["rainfall"] > 20:
        impact = min(0.25, features["rainfall"] / 200)
        factors.append({"factor": "Heavy rainfall", "impact": round(impact, 2), "direction": "increases_delay"})

    if features["distance_km"] > 800:
        impact = min(0.15, features["distance_km"] / 10000)
        factors.append({"factor": "Long distance", "impact": round(impact, 2), "direction": "increases_delay"})

    if features["weather_encoded"] >= 3:
        factors.append({"factor": "Adverse weather", "impact": 0.18, "direction": "increases_delay"})

    if features["traffic_encoded"] == 2:
        factors.append({"factor": "High traffic congestion", "impact": 0.12, "direction": "increases_delay"})

    if features["season_encoded"] == 2:
        factors.append({"factor": "Monsoon season", "impact": 0.14, "direction": "increases_delay"})

    if features["is_weekend"]:
        factors.append({"factor": "Weekend processing", "impact": 0.05, "direction": "increases_delay"})

    # Sort by impact
    factors.sort(key=lambda x: x["impact"], reverse=True)
    return factors[:6]


# ---- API Endpoints ----

@router.post("/predict/delay", response_model=PredictionResponse)
async def predict_delay(
    req: PredictionRequest,
    current_user=Depends(get_current_user),
):
    """Predict delay probability for a single shipment."""
    try:
        return _predict_single(req)
    except Exception as e:
        logger.error("prediction_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


@router.post("/predict/batch", response_model=BatchPredictionResponse)
async def predict_batch(
    req: BatchPredictionRequest,
    current_user=Depends(get_current_user),
):
    """Predict delay for multiple shipments."""
    predictions = []
    for shipment in req.shipments:
        try:
            pred = _predict_single(shipment)
            predictions.append(pred)
        except Exception as e:
            logger.error("batch_prediction_error", error=str(e))
            predictions.append(PredictionResponse(
                delay_probability=0.0,
                is_delayed=False,
                risk_level="LOW",
            ))

    return BatchPredictionResponse(predictions=predictions, total=len(predictions))


@router.get("/ml/model-performance", response_model=ModelPerformanceResponse)
async def get_model_performance(
    current_user=Depends(get_current_user),
):
    """Get ML model performance metrics."""
    model_dir = _get_model_dir()
    meta_path = model_dir / "metadata.json"

    if meta_path.exists():
        metadata = json.loads(meta_path.read_text())
        return ModelPerformanceResponse(**metadata)

    # Return empty performance if no model trained yet
    return ModelPerformanceResponse(
        classifier={
            "accuracy": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "f1_score": 0.0,
            "roc_auc": 0.0,
            "confusion_matrix": [[0, 0], [0, 0]],
            "note": "Model not yet trained. Run the ML training pipeline first.",
        },
        feature_importance=[],
        model_version="untrained",
    )
