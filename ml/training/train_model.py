import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime
import joblib

from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, mean_absolute_error,
    mean_squared_error, r2_score
)
import xgboost as xgb

# Add the backend directory to python path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))
sys.path.append(os.path.join(root_dir, "backend"))
from app.core.config import settings

def train_pipeline(input_csv: str = None):
    print("=" * 60)
    print("🚀 Starting SupplyChainIQ ML Training Pipeline")
    print("=" * 60)
    
    if input_csv is None:
        input_csv = os.path.join(root_dir, "storage", "raw", "shipments", "synthetic_shipments.csv")

    # 1. Load Data
    print(f"Loading raw dataset from {input_csv}...")
    if not os.path.exists(input_csv):
        print(f"Error: {input_csv} not found. Generating fresh data...")
        from data_generator.generate_shipments import generate_data
        generate_data(10000)

    df = pd.read_csv(input_csv)
    print(f"Total extracted records: {len(df)}")

    # Parse dates
    df['created_at'] = pd.to_datetime(df['created_at'])
    df['expected_delivery'] = pd.to_datetime(df['expected_delivery'])
    df['actual_delivery'] = pd.to_datetime(df['actual_delivery'])

    # Target variables
    df['is_delayed'] = (df['status'].isin(['DELAYED', 'DELIVERED'])) & (df['actual_delivery'] > df['expected_delivery'])
    df['delay_hours'] = (df['actual_delivery'] - df['expected_delivery']).dt.total_seconds() / 3600.0
    df['delay_hours'] = df['delay_hours'].fillna(0).apply(lambda x: max(0, x))

    # Keep completed/labeled shipments for model training
    df_train = df.dropna(subset=['actual_delivery']).copy()
    print(f"Using {len(df_train)} completed shipments for model training & cross-validation.")

    # 2. Feature Engineering
    print("Engineering features & encoding variables...")
    features = pd.DataFrame()
    features['distance_km'] = df_train['distance_km']
    features['package_weight'] = df_train['package_weight']
    features['day_of_week'] = df_train['created_at'].dt.dayofweek
    features['month'] = df_train['created_at'].dt.month
    features['hour'] = df_train['created_at'].dt.hour
    features['is_weekend'] = features['day_of_week'].isin([5, 6]).astype(int)
    features['rainfall'] = df_train['rainfall']
    features['temperature'] = df_train['temperature']

    # Encode categoricals
    carrier_map = {"Delhivery": 0, "BlueDart": 1, "DTDC": 2, "Ecom Express": 3, "XpressBees": 4, "Shadowfax": 5}
    features['carrier_encoded'] = df_train['carrier'].map(carrier_map).fillna(0)

    weather_map = {"Clear": 0, "Cloudy": 1, "Rainy": 2, "Foggy": 3, "Storm": 4}
    features['weather_encoded'] = df_train['weather_condition'].map(weather_map).fillna(0)

    traffic_map = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
    features['traffic_encoded'] = df_train['traffic_level'].map(traffic_map).fillna(1)

    shipment_type_map = {"ECONOMY": 0, "STANDARD": 1, "EXPRESS": 2, "SAME_DAY": 3, "FRAGILE": 4}
    features['shipment_type_encoded'] = df_train['shipment_type'].map(shipment_type_map).fillna(1)

    # Season mapping (0: Spring, 1: Summer, 2: Monsoon, 3: Winter)
    features['season_encoded'] = features['month'].apply(
        lambda m: 2 if m in [6, 7, 8, 9] else (3 if m in [11, 12, 1, 2] else (1 if m in [3, 4, 5] else 0))
    )

    X = features
    y_cls = df_train['is_delayed'].astype(int)
    y_reg = df_train['delay_hours']

    # 3. Train/Test Split (80/20) without data leakage
    X_train, X_test, y_cls_train, y_cls_test, y_reg_train, y_reg_test = train_test_split(
        X, y_cls, y_reg, test_size=0.2, random_state=42, stratify=y_cls
    )

    # -------------------------------------------------------------
    # 4. MODEL 1: Logistic Regression (Baseline)
    # -------------------------------------------------------------
    print("\n--- Training Model 1: Logistic Regression (Baseline) ---")
    lr = LogisticRegression(max_iter=1000, random_state=42)
    lr.fit(X_train, y_cls_train)
    y_lr_pred = lr.predict(X_test)
    y_lr_prob = lr.predict_proba(X_test)[:, 1]
    
    lr_metrics = {
        "model_name": "Logistic Regression (Baseline)",
        "accuracy": round(accuracy_score(y_cls_test, y_lr_pred), 3),
        "precision": round(precision_score(y_cls_test, y_lr_pred, zero_division=0), 3),
        "recall": round(recall_score(y_cls_test, y_lr_pred, zero_division=0), 3),
        "f1_score": round(f1_score(y_cls_test, y_lr_pred, zero_division=0), 3),
        "roc_auc": round(roc_auc_score(y_cls_test, y_lr_prob), 3),
        "confusion_matrix": confusion_matrix(y_cls_test, y_lr_pred).tolist()
    }
    print(f"Logistic Regression: Accuracy={lr_metrics['accuracy']}, Precision={lr_metrics['precision']}, Recall={lr_metrics['recall']}, F1={lr_metrics['f1_score']}")

    # -------------------------------------------------------------
    # 5. MODEL 2: Random Forest Classifier
    # -------------------------------------------------------------
    print("\n--- Training Model 2: Random Forest Classifier ---")
    rf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
    rf.fit(X_train, y_cls_train)
    y_rf_pred = rf.predict(X_test)
    y_rf_prob = rf.predict_proba(X_test)[:, 1]

    rf_metrics = {
        "model_name": "Random Forest Classifier",
        "accuracy": round(accuracy_score(y_cls_test, y_rf_pred), 3),
        "precision": round(precision_score(y_cls_test, y_rf_pred, zero_division=0), 3),
        "recall": round(recall_score(y_cls_test, y_rf_pred, zero_division=0), 3),
        "f1_score": round(f1_score(y_cls_test, y_rf_pred, zero_division=0), 3),
        "roc_auc": round(roc_auc_score(y_cls_test, y_rf_prob), 3),
        "confusion_matrix": confusion_matrix(y_cls_test, y_rf_pred).tolist()
    }
    print(f"Random Forest: Accuracy={rf_metrics['accuracy']}, Precision={rf_metrics['precision']}, Recall={rf_metrics['recall']}, F1={rf_metrics['f1_score']}")

    # -------------------------------------------------------------
    # 6. MODEL 3: XGBoost Classifier (Champion)
    # -------------------------------------------------------------
    print("\n--- Training Model 3: XGBoost Classifier (Champion) ---")
    xgb_clf = xgb.XGBClassifier(
        n_estimators=120,
        max_depth=5,
        learning_rate=0.08,
        eval_metric='logloss',
        random_state=42
    )
    xgb_clf.fit(X_train, y_cls_train)
    y_xgb_pred = xgb_clf.predict(X_test)
    y_xgb_prob = xgb_clf.predict_proba(X_test)[:, 1]

    xgb_metrics = {
        "model_name": "XGBoost Classifier",
        "accuracy": round(accuracy_score(y_cls_test, y_xgb_pred), 3),
        "precision": round(precision_score(y_cls_test, y_xgb_pred, zero_division=0), 3),
        "recall": round(recall_score(y_cls_test, y_xgb_pred, zero_division=0), 3),
        "f1_score": round(f1_score(y_cls_test, y_xgb_pred, zero_division=0), 3),
        "roc_auc": round(roc_auc_score(y_cls_test, y_xgb_prob), 3),
        "confusion_matrix": confusion_matrix(y_cls_test, y_xgb_pred).tolist()
    }
    print(f"XGBoost Classifier: Accuracy={xgb_metrics['accuracy']}, Precision={xgb_metrics['precision']}, Recall={xgb_metrics['recall']}, F1={xgb_metrics['f1_score']}")

    # -------------------------------------------------------------
    # 7. REGRESSION MODEL: Delay Duration in Hours
    # -------------------------------------------------------------
    print("\n--- Training Model 4: Delay Duration Regressor (RandomForest) ---")
    mask_delayed_train = y_cls_train == 1
    mask_delayed_test = y_cls_test == 1

    reg = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)
    if mask_delayed_train.sum() > 30:
        reg.fit(X_train[mask_delayed_train], y_reg_train[mask_delayed_train])
        y_reg_pred = reg.predict(X_test[mask_delayed_test])
        y_reg_true = y_reg_test[mask_delayed_test]

        reg_metrics = {
            "mae": round(mean_absolute_error(y_reg_true, y_reg_pred), 2),
            "rmse": round(mean_squared_error(y_reg_true, y_reg_pred) ** 0.5, 2),
            "r2": round(r2_score(y_reg_true, y_reg_pred), 3)
        }
    else:
        reg_metrics = {"mae": 0, "rmse": 0, "r2": 0}

    print(f"Regressor Metrics: MAE={reg_metrics['mae']} hrs, RMSE={reg_metrics['rmse']} hrs, R2={reg_metrics['r2']}")

    # -------------------------------------------------------------
    # 8. Feature Importance
    # -------------------------------------------------------------
    importance_df = pd.DataFrame({
        'feature': X.columns,
        'importance': [round(float(v), 4) for v in xgb_clf.feature_importances_]
    }).sort_values('importance', ascending=False)
    feature_importance = importance_df.to_dict('records')

    # -------------------------------------------------------------
    # 9. Save Models and Metadata
    # -------------------------------------------------------------
    print("\nSaving champion models and benchmark metadata to disk...")
    models_dir = os.path.join(root_dir, "ml", "models")
    clf_dir = os.path.join(models_dir, "delay_classifier")
    reg_dir = os.path.join(models_dir, "delay_regressor")

    os.makedirs(clf_dir, exist_ok=True)
    os.makedirs(reg_dir, exist_ok=True)

    joblib.dump(xgb_clf, os.path.join(clf_dir, "model.joblib"))
    joblib.dump(reg, os.path.join(reg_dir, "model.joblib"))

    metadata = {
        "training_date": datetime.now().isoformat(),
        "training_samples": len(df_train),
        "test_samples": len(X_test),
        "model_version": "2.4.0-xgb",
        "champion_model": "XGBoost Classifier",
        "classifier": xgb_metrics,
        "models_comparison": [
            lr_metrics,
            rf_metrics,
            xgb_metrics
        ],
        "regressor": reg_metrics,
        "feature_importance": feature_importance
    }

    with open(os.path.join(models_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=4)

    print("=" * 60)
    print("✅ ML Training Pipeline completed successfully! Models saved to ml/models/")
    print("=" * 60)
    return metadata

if __name__ == "__main__":
    train_pipeline()
