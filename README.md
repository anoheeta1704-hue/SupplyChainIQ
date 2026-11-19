# SupplyChainIQ
**Supply Chain Visibility & Shipment Delay Prediction Platform**

A production-style, cloud-ready full-stack AI/ML platform designed for real-time shipment visibility, predictive delay detection, historical logistics analytics, and proactive risk management.

## 🏗️ Architecture
- **Frontend**: Next.js (TypeScript, Tailwind CSS)
- **Analytics Dashboard**: Streamlit (Python, Plotly)
- **Backend API**: FastAPI (Python, async)
- **Database**: PostgreSQL (Operational DB & Star Schema Data Warehouse)
- **Caching & Rate Limiting**: Redis
- **Machine Learning**: XGBoost Classifier & Random Forest Regressor (Scikit-learn, Joblib)
- **Data Engineering**: Python ETL Pipeline (Pandas)
- **Orchestration**: Docker & Docker Compose

## 🚀 Quick Start (Local Development)

### 1. Start the Infrastructure
Make sure Docker is running on your machine.
```bash
# Copy the environment file
cp .env.example .env

# Start all services
docker-compose up -d
```

### 2. Generate Data & Run Pipelines
The system comes with a synthetic data generator to simulate realistic logistics data.
Open a terminal and run the following commands (requires Python 3.11+):

```bash
# Install backend requirements locally for the scripts
pip install -r backend/requirements.txt

# Seed the database with users, carriers, and warehouses
python backend/scripts/seed.py

# Generate 10,000 synthetic shipments (saved to storage/raw/shipments/)
python data-generator/generate_shipments.py

# Run the ETL pipeline to load data into the Data Warehouse Star Schema
python etl/pipeline.py

# Train the ML Models (Delay Classifier & Regressor)
python ml/training/train_model.py
```

### 3. Access the Applications

- **Next.js Dashboard**: [http://localhost:3000](http://localhost:3000)
  - Login Email: `admin@supplychainiq.com`
  - Password: `admin123`
- **Streamlit Analytics**: [http://localhost:8501](http://localhost:8501)
- **FastAPI Interactive Docs (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)

## 📁 Project Structure
```text
supplychain-iq/
├── backend/            # FastAPI Application (APIs, ORM Models, Auth)
├── frontend/           # Next.js User Dashboard
├── streamlit/          # Internal Analytics & ML Dashboard
├── ml/                 # Machine Learning Pipeline & Saved Models
├── etl/                # ETL scripts (Raw -> Data Warehouse)
├── warehouse/          # PostgreSQL Schema definitions
├── data-generator/     # Synthetic logistics data generator
├── storage/            # Local data lake (fallback for AWS S3)
└── docker-compose.yml  # Docker orchestration
```

## 🧠 Machine Learning
- **Delay Classifier**: Predicts the probability of a shipment being delayed (Risk: LOW, MEDIUM, HIGH). Uses XGBoost.
- **Delay Regressor**: Predicts the estimated delay duration in hours. Uses Random Forest.
- **Explainability**: The API calculates heuristic contributing factors (e.g., Heavy Rainfall, Route Bottlenecks) when predicting delays.

## ☁️ Cloud Deployment (AWS)
The platform is designed to be cloud-native:
- **Raw Data**: Configure AWS credentials in `.env` to switch from local `storage/` to **AWS S3**.
- **Backend/Frontend**: Deployable via AWS ECS, EKS, or Vercel/EC2.
- **Database/Cache**: AWS RDS (PostgreSQL) and Amazon ElastiCache (Redis).
