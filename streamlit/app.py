import os
import sys
import json
import requests
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sqlalchemy import create_engine, text

# ---- Config ----
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
from app.core.database import active_sync_url

st.set_page_config(
    page_title="SupplyChainIQ Analytics",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

API_URL = os.environ.get("API_URL", "http://localhost:8000/api")

# ---- DB ----
@st.cache_resource
def get_engine():
    kwargs = {}
    if "sqlite" in active_sync_url:
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(active_sync_url, **kwargs)

# ---- API helpers ----
@st.cache_data(ttl=300)
def fetch_json(endpoint):
    try:
        r = requests.get(f"{API_URL}/{endpoint}", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

# ---- Warehouse queries ----
@st.cache_data(ttl=120)
def query_warehouse(sql):
    try:
        engine = get_engine()
        return pd.read_sql(sql, engine)
    except Exception as e:
        st.error(f"Warehouse query error: {e}")
        return pd.DataFrame()

# ==============================
# PAGES
# ==============================

def main():
    st.sidebar.title("📦 SupplyChainIQ")
    st.sidebar.markdown("**Analytics & Intelligence Hub**")

    pages = [
        "Executive Overview",
        "Carrier Analytics",
        "Warehouse Bottlenecks",
        "Data Warehouse Explorer",
        "ML Model Benchmarks",
        "Route Intelligence",
    ]
    choice = st.sidebar.radio("Navigate", pages)

    st.sidebar.markdown("---")
    st.sidebar.markdown("**System Status**")
    kpis = fetch_json("dashboard/kpis")
    if kpis:
        st.sidebar.success("✅ Backend Connected")
        st.sidebar.metric("Active Shipments", kpis['kpis'].get('active_shipments', 0))
        st.sidebar.metric("Delayed", kpis['kpis'].get('delayed', 0))
    else:
        st.sidebar.warning("⚠️ Backend Offline — using warehouse DB directly")

    # Warehouse health
    engine = get_engine()
    try:
        with engine.connect() as conn:
            fact_count = conn.execute(text("SELECT COUNT(*) FROM fact_shipment_events")).scalar()
        st.sidebar.metric("Warehouse Records", f"{fact_count:,}")
    except Exception:
        st.sidebar.error("Warehouse tables not loaded")

    if choice == "Executive Overview":
        page_executive(kpis)
    elif choice == "Carrier Analytics":
        page_carrier()
    elif choice == "Warehouse Bottlenecks":
        page_warehouse()
    elif choice == "Data Warehouse Explorer":
        page_dw_explorer()
    elif choice == "ML Model Benchmarks":
        page_ml_benchmarks()
    elif choice == "Route Intelligence":
        page_routes()


# ---- PAGE 1: Executive Overview ----
def page_executive(kpis):
    st.title("📊 Executive Overview")

    if not kpis:
        st.warning("Backend not reachable. Showing warehouse summary instead.")
        df = query_warehouse("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN is_delayed=1 THEN 1 ELSE 0 END) as delayed,
                   AVG(delay_hours) as avg_delay,
                   AVG(delivery_duration_hours) as avg_duration
            FROM fact_shipment_events
        """)
        if not df.empty:
            r = df.iloc[0]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Shipments", f"{int(r['total']):,}")
            c2.metric("Delayed", int(r['delayed']))
            c3.metric("Avg Delay (hrs)", f"{r['avg_delay']:.1f}")
            c4.metric("Avg Duration (hrs)", f"{r['avg_duration']:.1f}")
        return

    kd = kpis['kpis']
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Shipments", f"{kd['total_shipments']:,}")
    c2.metric("On-Time Rate", f"{kd['on_time_rate']*100:.1f}%")
    c3.metric("Avg Delivery", f"{kd['avg_delivery_hours']:.1f}h")
    c4.metric("Delayed", kd['delayed'])
    c5.metric("High Risk", kd['high_risk'])

    st.markdown("---")
    col_l, col_r = st.columns([2, 1])

    with col_l:
        st.subheader("Delay Trend (30 Days)")
        if kpis.get('delay_trend'):
            df_trend = pd.DataFrame(kpis['delay_trend'])
            fig = px.area(df_trend, x='date', y=['total', 'delayed'],
                         labels={'value': 'Shipments', 'variable': 'Category'},
                         color_discrete_map={'total': '#3b82f6', 'delayed': '#ef4444'})
            fig.update_layout(height=350, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.subheader("Status Distribution")
        if kpis.get('status_distribution'):
            df_s = pd.DataFrame(kpis['status_distribution'])
            fig = px.pie(df_s, names='status', values='count', hole=0.45,
                        color_discrete_sequence=px.colors.qualitative.Set2)
            fig.update_layout(height=350, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig, use_container_width=True)

    st.subheader("🚨 Recent Alerts")
    if kpis.get('recent_alerts'):
        for a in kpis['recent_alerts'][:5]:
            sev = a.get('severity', '')
            icon = "🔴" if sev in ['HIGH', 'CRITICAL'] else "🟡" if sev == 'MEDIUM' else "🟢"
            st.markdown(f"**{icon} {a['title']}** — {a.get('created_at', '')[:10]}  \n{a.get('message', '')}")
    else:
        st.info("No active alerts.")


# ---- PAGE 2: Carrier Analytics ----
def page_carrier():
    st.title("🚚 Carrier Performance Analytics")

    # Try API first, then fall back to warehouse
    carriers = fetch_json("analytics/carriers")
    if carriers:
        df = pd.json_normalize(carriers)
        df.columns = [c.replace('carrier.', '') for c in df.columns]
    else:
        df = query_warehouse("""
            SELECT c.carrier_name as name, c.carrier_code as code,
                   COUNT(f.fact_id) as total_shipments,
                   SUM(CASE WHEN f.is_delayed=1 THEN 1 ELSE 0 END) as delayed_shipments,
                   AVG(f.delay_hours) as avg_delay_hours
            FROM fact_shipment_events f
            JOIN dim_carrier c ON f.carrier_key = c.carrier_key
            GROUP BY c.carrier_name, c.carrier_code
        """)
        if not df.empty:
            df['delay_rate'] = df['delayed_shipments'] / df['total_shipments'].clip(lower=1)
            df['on_time_rate'] = 1 - df['delay_rate']

    if df.empty:
        st.warning("No carrier data available.")
        return

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Delay Rate by Carrier")
        fig = px.bar(df.sort_values('delay_rate', ascending=False),
                    x='name', y='delay_rate', color='delay_rate',
                    color_continuous_scale='Reds', text_auto='.1%')
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("Avg Delay (Hours)")
        fig = px.bar(df.sort_values('avg_delay_hours', ascending=False),
                    x='name', y='avg_delay_hours', color='avg_delay_hours',
                    color_continuous_scale='Oranges')
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Carrier Comparison Matrix")
    display_cols = [c for c in ['name', 'total_shipments', 'delayed_shipments', 'delay_rate', 'on_time_rate', 'avg_delay_hours'] if c in df.columns]
    st.dataframe(df[display_cols], use_container_width=True)


# ---- PAGE 3: Warehouse Bottlenecks ----
def page_warehouse():
    st.title("🏭 Warehouse Analytics")

    whs = fetch_json("analytics/warehouses")
    if whs:
        df = pd.json_normalize(whs)
        df.columns = [c.replace('warehouse.', '') for c in df.columns]
    else:
        df = query_warehouse("""
            SELECT w.warehouse_name as name, w.warehouse_code as code,
                   COUNT(f.fact_id) as total_shipments,
                   SUM(CASE WHEN f.is_delayed=1 THEN 1 ELSE 0 END) as delayed_shipments,
                   AVG(f.delay_hours) as avg_processing_hours
            FROM fact_shipment_events f
            JOIN dim_warehouse w ON f.warehouse_key = w.warehouse_key
            GROUP BY w.warehouse_name, w.warehouse_code
        """)

    if df.empty:
        st.warning("No warehouse data available.")
        return

    if 'utilization_pct' not in df.columns:
        df['utilization_pct'] = (df['total_shipments'] / df['total_shipments'].max() * 100).round(1)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Warehouse Utilization")
        fig = px.bar(df.sort_values('utilization_pct', ascending=False),
                    x='name', y='utilization_pct', color='utilization_pct',
                    color_continuous_scale='RdYlGn_r', text_auto='.1f')
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("Shipments per Warehouse")
        fig = px.bar(df.sort_values('total_shipments', ascending=False),
                    x='name', y='total_shipments', color='delayed_shipments',
                    color_continuous_scale='Reds')
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(df, use_container_width=True)


# ---- PAGE 4: Data Warehouse Explorer ----
def page_dw_explorer():
    st.title("🗄️ Data Warehouse Explorer")
    st.markdown("Query the star-schema warehouse directly. 10,000 synthetic shipment records loaded.")

    tab1, tab2, tab3 = st.tabs(["Delay Analysis", "Time Trends", "Custom SQL"])

    with tab1:
        st.subheader("Delays by Weather × Traffic")
        df = query_warehouse("""
            SELECT w.condition as weather, w.traffic_level,
                   COUNT(f.fact_id) as shipments,
                   SUM(CASE WHEN f.is_delayed=1 THEN 1 ELSE 0 END) as delayed,
                   ROUND(AVG(f.delay_hours), 1) as avg_delay_hrs
            FROM fact_shipment_events f
            JOIN dim_weather w ON f.weather_key = w.weather_key
            GROUP BY w.condition, w.traffic_level
            ORDER BY delayed DESC
        """)
        if not df.empty:
            df['delay_rate'] = (df['delayed'] / df['shipments'] * 100).round(1)
            fig = px.scatter(df, x='weather', y='traffic_level', size='shipments',
                           color='delay_rate', color_continuous_scale='RdYlGn_r',
                           hover_data=['avg_delay_hrs', 'delayed'],
                           title="Bubble: shipment count | Color: delay rate %")
            fig.update_layout(height=450)
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df, use_container_width=True)

    with tab2:
        st.subheader("Monthly Shipment Volumes & Delays")
        df = query_warehouse("""
            SELECT t.month_name, t.month, t.season,
                   COUNT(f.fact_id) as shipments,
                   SUM(CASE WHEN f.is_delayed=1 THEN 1 ELSE 0 END) as delayed,
                   ROUND(AVG(f.delay_hours), 1) as avg_delay
            FROM fact_shipment_events f
            JOIN dim_time t ON f.time_key = t.time_key
            GROUP BY t.month_name, t.month, t.season
            ORDER BY t.month
        """)
        if not df.empty:
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Bar(x=df['month_name'], y=df['shipments'], name='Shipments',
                                marker_color='#3b82f6'), secondary_y=False)
            fig.add_trace(go.Scatter(x=df['month_name'], y=df['delayed'], name='Delayed',
                                    mode='lines+markers', line=dict(color='#ef4444', width=3)),
                         secondary_y=True)
            fig.update_layout(height=400, title="Monthly Volume vs Delays")
            fig.update_yaxes(title_text="Total Shipments", secondary_y=False)
            fig.update_yaxes(title_text="Delayed", secondary_y=True)
            st.plotly_chart(fig, use_container_width=True)

            # Season breakdown
            st.subheader("Season Impact")
            season_df = df.groupby('season').agg(
                shipments=('shipments', 'sum'),
                delayed=('delayed', 'sum'),
                avg_delay=('avg_delay', 'mean')
            ).reset_index()
            season_df['delay_rate'] = (season_df['delayed'] / season_df['shipments'] * 100).round(1)
            fig2 = px.bar(season_df, x='season', y='delay_rate', color='season',
                         text_auto='.1f', title="Delay Rate by Season (%)",
                         color_discrete_map={'Monsoon': '#ef4444', 'Winter': '#3b82f6',
                                           'Summer': '#f59e0b', 'Spring': '#10b981'})
            fig2.update_layout(height=350)
            st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        st.subheader("Run Custom SQL")
        st.markdown("Tables: `fact_shipment_events`, `dim_carrier`, `dim_route`, `dim_warehouse`, `dim_weather`, `dim_time`, `dim_shipment`")
        default_sql = """SELECT c.carrier_name, r.origin, r.destination,
       COUNT(*) as total, SUM(f.is_delayed) as delayed,
       ROUND(AVG(f.delay_hours), 1) as avg_delay
FROM fact_shipment_events f
JOIN dim_carrier c ON f.carrier_key = c.carrier_key
JOIN dim_route r ON f.route_key = r.route_key
GROUP BY c.carrier_name, r.origin, r.destination
ORDER BY delayed DESC
LIMIT 20"""
        sql = st.text_area("SQL Query", value=default_sql, height=180)
        if st.button("▶ Run Query"):
            result = query_warehouse(sql)
            if not result.empty:
                st.success(f"Returned {len(result)} rows")
                st.dataframe(result, use_container_width=True)
            else:
                st.warning("No results.")


# ---- PAGE 5: ML Model Benchmarks ----
def page_ml_benchmarks():
    st.title("🤖 ML Model Performance Benchmarks")

    # Load metadata directly for reliability
    meta_path = os.path.join(os.path.dirname(__file__), "..", "ml", "models", "metadata.json")
    perf = None
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            perf = json.load(f)
    else:
        perf = fetch_json("ml/model-performance")

    if not perf or perf.get('model_version') == 'untrained':
        st.warning("ML models not trained. Run the training pipeline first.")
        return

    st.markdown(f"**Model Version:** `{perf['model_version']}` | **Training Date:** {perf.get('training_date', 'N/A')[:10]} | **Training Samples:** {perf.get('training_samples', 'N/A'):,}")

    st.info("⚠️ These metrics are from **synthetic data** with weak feature-label correlation by design. Real-world performance would differ with genuine shipment data.")

    # ---- 3-Model Comparison ----
    st.subheader("🏆 3-Model Comparison")
    models = perf.get('models_comparison', [])
    if models:
        comp_df = pd.DataFrame(models)
        metrics = ['accuracy', 'precision', 'recall', 'f1_score', 'roc_auc']
        fig = go.Figure()
        colors = ['#3b82f6', '#10b981', '#f59e0b']
        for i, row in comp_df.iterrows():
            fig.add_trace(go.Bar(
                name=row['model_name'],
                x=metrics,
                y=[row[m] for m in metrics],
                marker_color=colors[i % len(colors)],
                text=[f"{row[m]:.3f}" for m in metrics],
                textposition='outside'
            ))
        fig.update_layout(barmode='group', height=450, title="Classifier Metrics Comparison",
                         yaxis_range=[0, 1.05])
        st.plotly_chart(fig, use_container_width=True)

        # Champion highlight
        champion = perf.get('champion_model', 'XGBoost Classifier')
        st.success(f"🏆 Champion Model: **{champion}** — selected for highest recall on delayed class")

        # Confusion matrices side-by-side
        st.subheader("Confusion Matrices")
        cols = st.columns(len(models))
        for i, model in enumerate(models):
            with cols[i]:
                cm = model.get('confusion_matrix', [[0, 0], [0, 0]])
                fig_cm = px.imshow(cm, labels=dict(x="Predicted", y="Actual", color="Count"),
                                  x=['On-Time', 'Delayed'], y=['On-Time', 'Delayed'],
                                  text_auto=True, color_continuous_scale='Blues',
                                  title=model['model_name'].split('(')[0].strip())
                fig_cm.update_layout(height=300, margin=dict(l=0, r=0, t=40, b=0))
                st.plotly_chart(fig_cm, use_container_width=True)

    # ---- Feature Importance ----
    st.subheader("Feature Importance (XGBoost)")
    fi = perf.get('feature_importance', [])
    if fi:
        df_fi = pd.DataFrame(fi)
        fig_fi = px.bar(df_fi.sort_values('importance', ascending=True),
                       x='importance', y='feature', orientation='h',
                       color='importance', color_continuous_scale='Viridis')
        fig_fi.update_layout(height=400)
        st.plotly_chart(fig_fi, use_container_width=True)

    # ---- Regressor ----
    if perf.get('regressor'):
        st.markdown("---")
        st.subheader("Delay Duration Regressor (RandomForest)")
        reg = perf['regressor']
        c1, c2, c3 = st.columns(3)
        c1.metric("MAE (Hours)", f"{reg.get('mae', 0):.2f}")
        c2.metric("RMSE", f"{reg.get('rmse', 0):.2f}")
        c3.metric("R² Score", f"{reg.get('r2', 0):.3f}")
        if reg.get('r2', 0) < 0:
            st.warning("Negative R² indicates the regressor performs worse than mean baseline on synthetic data. This is expected — real shipment data with true delay labels would yield meaningful regression.")


# ---- PAGE 6: Route Intelligence ----
def page_routes():
    st.title("🗺️ Route Intelligence")

    df = query_warehouse("""
        SELECT r.origin, r.destination, r.distance_km,
               COUNT(f.fact_id) as shipments,
               SUM(CASE WHEN f.is_delayed=1 THEN 1 ELSE 0 END) as delayed,
               ROUND(AVG(f.delay_hours), 1) as avg_delay,
               ROUND(AVG(f.delivery_duration_hours), 1) as avg_duration
        FROM fact_shipment_events f
        JOIN dim_route r ON f.route_key = r.route_key
        GROUP BY r.origin, r.destination, r.distance_km
        HAVING shipments >= 5
        ORDER BY delayed DESC
    """)

    if df.empty:
        st.warning("No route data available.")
        return

    df['delay_rate'] = (df['delayed'] / df['shipments'] * 100).round(1)
    df['route'] = df['origin'] + " → " + df['destination']

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Top Delayed Routes")
        top = df.nlargest(15, 'delayed')
        fig = px.bar(top, x='route', y='delay_rate', color='delay_rate',
                    color_continuous_scale='Reds', text_auto='.1f')
        fig.update_layout(height=450, xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("Distance vs Delay")
        fig = px.scatter(df, x='distance_km', y='avg_delay', size='shipments',
                        color='delay_rate', color_continuous_scale='RdYlGn_r',
                        hover_data=['origin', 'destination'])
        fig.update_layout(height=450)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Full Route Table")
    st.dataframe(df[['route', 'distance_km', 'shipments', 'delayed', 'delay_rate', 'avg_delay', 'avg_duration']]
                .sort_values('delay_rate', ascending=False), use_container_width=True)


if __name__ == "__main__":
    main()
