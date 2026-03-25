# app.py
import os
import re
import json
import math
from datetime import datetime, timedelta, date

import boto3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from botocore.exceptions import NoCredentialsError, ProfileNotFound, ClientError

# ===================================
# Configuración de página
# ===================================
st.set_page_config(page_title="SecurityHub CSPM Dashboard", layout="wide")
st.title("SecurityHub CSPM — Dashboard")
st.caption(
    "Lee JSON diarios desde S3 (perfil AWS CLI: security) y genera resumen, timeline, tendencias, baseline y analítica avanzada."
)

# ===================================
# Parámetros (Sidebar)
# ===================================
st.sidebar.header("Conexión y Filtros")

# Bucket desde variable de entorno con override
bucket_env = os.getenv("SECURITYHUB_BUCKET", "")
bucket = st.sidebar.text_input(
    "Bucket S3 (ENV: SECURITYHUB_BUCKET)",
    value=bucket_env if bucket_env else "tu-bucket",
    help="Se pre-carga desde SECURITYHUB_BUCKET; estructura esperada: s3://<bucket>/securityhub-cspm/YYYY/MM/DD/…"
)

# Prefijo raíz fijo dentro del bucket
ROOT_PREFIX = "securityhub-cspm/"

profile = st.sidebar.text_input("Perfil AWS CLI", value="security", help="Perfil en ~/.aws/credentials")

hoy = date.today()
target_date = st.sidebar.date_input("Fecha base (día)", value=hoy, min_value=date(2020, 1, 1))
rango = st.sidebar.radio("Rango Timeline", options=["Semanal (7 días)", "Mensual (30 días)"], index=0)
top_n = st.sidebar.slider("Top N (Tendencias)", min_value=3, max_value=25, value=10, step=1)
vista_vpc = st.sidebar.selectbox("Alcance (Tendencias)", options=["Agregado (VPC1+VPC2)", "VPC1", "VPC2"], index=0)
st.sidebar.markdown("---")
st.sidebar.caption("Cache de datos: 1 hora")

# ===================================
# Utilidades y Parsing
# ===================================

FILENAME_RE = re.compile(
    r"^control_status_(?P<vpc>[^_]+)_(?P<fecha>\d{8})_(?P<hora>\d{6})\.json$"
)
# Ej.: control_status_VPC1_20260227_220535.json

def parse_from_key(key: str):
    """Devuelve (vpc, dt, momento, day_str) o (None, None, None, None) si no matchea patrón."""
    filename = key.split("/")[-1]
    m = FILENAME_RE.match(filename)
    if not m:
        return None, None, None, None
    vpc = m.group("vpc")
    dt = datetime.strptime(m.group("fecha") + m.group("hora"), "%Y%m%d%H%M%S")
    momento = "mañana" if dt.hour < 12 else "tarde"
    day_str = dt.strftime("%Y-%m-%d")
    return vpc, dt, momento, day_str

def compliance_to_emoji(status_str: str, comp_status: str):
    """
    Emoji + etiqueta amigable:
    - DISABLED: ⚪ Disabled
    - Passed: 🟢 Passed
    - Failed: 🔴 Failed
    - Warning: 🟠 Warning
    - No data/Unknown: ⚫ No data
    """
    s = (status_str or "").strip().lower()
    cs = (comp_status or "").strip().lower()
    if s == "disabled":
        return "⚪ Disabled"
    if cs == "passed":
        return "🟢 Passed"
    if cs == "failed":
        return "🔴 Failed"
    if cs == "warning":
        return "🟠 Warning"
    if cs in ("no_data", "unknown", "no data"):
        return "⚫ No data"
    return "⚫ N/A"

def safe_int(x):
    try:
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return 0
        return int(x)
    except Exception:
        try:
            return int(float(x))
        except Exception:
            return 0

def normalize_score(score_raw):
    """Acepta '64%' o 64 o 64.0. Devuelve float 0-100 o None."""
    if isinstance(score_raw, str) and score_raw.endswith("%"):
        try:
            return float(score_raw.strip("%"))
        except Exception:
            return None
    if isinstance(score_raw, (int, float)):
        return float(score_raw)
    return None

def control_family(control_id: str):
    """Retorna el prefijo de familia del control (antes del primer punto)."""
    if not control_id or "." not in control_id:
        return control_id
    return control_id.split(".")[0]

# ===================================
# Conexión S3 y Cache
# ===================================

@st.cache_data(show_spinner=False, ttl=3600)
def get_s3_client_cached(profile_name: str):
    """Verifica credenciales (cachea booleano)."""
    try:
        session = boto3.Session(profile_name=profile_name) if profile_name else boto3.Session()
        s3 = session.client("s3")
        _ = s3.list_buckets()
        return True
    except ProfileNotFound as e:
        return f"Perfil AWS no encontrado: {e}"
    except NoCredentialsError:
        return "No se encontraron credenciales. Configura AWS CLI o variables de entorno."
    except ClientError as e:
        return f"Error de cliente AWS: {e}"
    except Exception as e:
        return f"Error creando cliente S3: {e}"

def get_s3_client(profile_name: str):
    """Cliente S3 (no cache)."""
    session = boto3.Session(profile_name=profile_name) if profile_name else boto3.Session()
    return session.client("s3")

@st.cache_data(show_spinner=False, ttl=3600)
def list_keys_for_date(bucket: str, day: date) -> list:
    """
    Lista keys .json bajo prefijo:
      s3://<bucket>/securityhub-cspm/YYYY/MM/DD/
    """
    s3 = get_s3_client(profile)
    prefix = ROOT_PREFIX + day.strftime("%Y/%m/%d/")  # securityhub-cspm/2026/02/27/
    keys = []
    token = None
    while True:
        params = {"Bucket": bucket, "Prefix": prefix}
        if token:
            params["ContinuationToken"] = token
        resp = s3.list_objects_v2(**params)
        for obj in resp.get("Contents", []):
            k = obj["Key"]
            if k.endswith(".json"):
                keys.append(k)
        if resp.get("IsTruncated"):
            token = resp.get("NextContinuationToken")
        else:
            break
    return keys

@st.cache_data(show_spinner=False, ttl=3600)
def get_object_json(bucket: str, key: str) -> dict:
    """Descarga y parsea JSON desde S3 (cacheado)."""
    s3 = get_s3_client(profile)
    obj = s3.get_object(Bucket=bucket, Key=key)
    return json.loads(obj["Body"].read())

@st.cache_data(show_spinner=True, ttl=3600)
def load_data_for_range(bucket: str, start_day: date, end_day: date):
    """
    Carga datos (General + Controls) para el rango [start_day, end_day].
    Devuelve: df_general, df_controls
    """
    rows_general = []
    rows_controls = []
    day = start_day
    while day <= end_day:
        keys = list_keys_for_date(bucket, day)
        for key in keys:
            vpc, ts, momento, day_str = parse_from_key(key)
            if not vpc:
                continue
            try:
                payload = get_object_json(bucket, key)
            except Exception as e:
                st.warning(f"Error leyendo {key}: {e}")
                continue

            general = payload.get("General", {}) or {}
            score_raw = general.get("SecurityScore")
            score = normalize_score(score_raw)

            rows_general.append({
                "bucket_key": key,
                "date": day_str,
                "timestamp": ts,
                "momento": momento,
                "vpc": vpc,
                "SecurityScoreRaw": score_raw,
                "SecurityScorePct": score,
                "TotalEnabled": general.get("TotalEnabled"),
                "TotalDisabled": general.get("TotalDisabled"),
                "TotalNoData": general.get("TotalNoData"),
                "TotalSumControls": general.get("TotalSumControls"),
                "TotalPassed": general.get("TotalPassed"),
                "TotalFailed": general.get("TotalFailed"),
                "TotalUnknown": general.get("TotalUnknown"),
                "TotalControls": general.get("TotalControls"),
            })

            controls = payload.get("Controls", {}) or {}
            for ctrl_id, meta in controls.items():
                status = meta.get("status")
                severity = meta.get("severity")
                standard = meta.get("standard")
                title = meta.get("title")

                results = meta.get("results", {}) or {}
                comp = results.get("ComplianceStatus")
                c_passed = safe_int(results.get("passed"))
                c_failed = safe_int(results.get("failed"))
                c_warning = safe_int(results.get("warning"))
                c_no_data = safe_int(results.get("no_data"))

                rows_controls.append({
                    "bucket_key": key,
                    "date": day_str,
                    "timestamp": ts,
                    "momento": momento,
                    "vpc": vpc,
                    "control_id": ctrl_id,
                    "title": title,
                    "status": status,
                    "severity": severity,
                    "standard": standard,
                    "ComplianceStatus": comp,
                    "passed": c_passed,
                    "failed": c_failed,
                    "warning": c_warning,
                    "no_data": c_no_data,
                })
        day += timedelta(days=1)

    df_general = pd.DataFrame(rows_general) if rows_general else pd.DataFrame(columns=[
        "bucket_key","date","timestamp","momento","vpc","SecurityScoreRaw","SecurityScorePct",
        "TotalEnabled","TotalDisabled","TotalNoData","TotalSumControls","TotalPassed",
        "TotalFailed","TotalUnknown","TotalControls"
    ])
    df_controls = pd.DataFrame(rows_controls) if rows_controls else pd.DataFrame(columns=[
        "bucket_key","date","timestamp","momento","vpc","control_id","title","status","severity",
        "standard","ComplianceStatus","passed","failed","warning","no_data"
    ])

    if not df_general.empty:
        df_general = df_general.sort_values(["date", "vpc", "timestamp"]).reset_index(drop=True)
    if not df_controls.empty:
        df_controls = df_controls.sort_values(["date", "vpc", "control_id", "timestamp"]).reset_index(drop=True)

    return df_general, df_controls

def last_snapshot_per_day(df, by_cols):
    """Para cada combinación en by_cols toma la fila con timestamp más reciente."""
    if df.empty:
        return df
    idx = df.groupby(by_cols)["timestamp"].idxmax()
    return df.loc[idx].sort_values(by_cols).reset_index(drop=True)

# ===================================
# Conexión verificada
# ===================================
check = get_s3_client_cached(profile)
if check is not True:
    st.error(check if isinstance(check, str) else "Error desconocido creando cliente S3")
    st.stop()

# ===================================
# Rango para timeline
# ===================================
if "Semanal" in rango:
    start_range = target_date - timedelta(days=6)
else:
    start_range = target_date - timedelta(days=29)
end_range = target_date

# ===================================
# Carga de datos
# ===================================
with st.spinner(f"Cargando datos desde s3://{bucket}/{ROOT_PREFIX}{start_range:%Y/%m/%d} ... {end_range:%Y/%m/%d}"):
    df_general, df_controls = load_data_for_range(bucket, start_range, end_range)

if df_general.empty:
    st.warning("No se encontraron datos en el rango seleccionado.")
    st.stop()

# Último snapshot del día por VPC / Control
dfg_last = last_snapshot_per_day(df_general, by_cols=["date", "vpc"])
dfc_last = last_snapshot_per_day(df_controls, by_cols=["date", "vpc", "control_id"])

# Filtrar conjuntos para el día base
dfg_today = dfg_last[dfg_last["date"] == target_date.strftime("%Y-%m-%d")].copy()
dfc_today = dfc_last[dfc_last["date"] == target_date.strftime("%Y-%m-%d")].copy()

# ===================================
# UI con pestañas
# ===================================
tab_resumen, tab_timeline, tab_tendencias, tab_baseline, tab_advanced = st.tabs(
    ["📊 Resumen General", "📈 Timeline Score", "🚦 Top de Tendencias", "🧱 Línea base de Seguridad", "🔬 Analítica Avanzada"]
)

# ===================================
# 1) Resumen General
# ===================================
with tab_resumen:
    st.subheader(f"Resumen general — {target_date:%Y-%m-%d} (último snapshot del día por VPC)")
    if dfg_today.empty:
        st.info("No hay snapshots para el día seleccionado.")
    else:
        # KPIs
        cols = st.columns(2)
        for i, vpc in enumerate(sorted(dfg_today["vpc"].unique())):
            sub = dfg_today[dfg_today["vpc"] == vpc]
            if sub.empty:
                continue
            r = sub.iloc[0]
            with cols[i % 2]:
                st.metric(
                    label=f"{vpc} • SecurityScore",
                    value=f"{(r['SecurityScorePct'] or 0):.0f}%",
                    help=f"Snapshot: {r['timestamp']:%Y-%m-%d %H:%M:%S} ({r['momento']})"
                )
                k1, k2, k3 = st.columns(3)
                k1.metric("TotalPassed", int(r.get("TotalPassed") or 0))
                k2.metric("TotalFailed", int(r.get("TotalFailed") or 0))
                k3.metric("TotalEnabled", int(r.get("TotalEnabled") or 0))

        st.markdown("---")
        # Pie charts por VPC
        pie_cols = st.columns(2)
        for i, vpc in enumerate(sorted(dfg_today["vpc"].unique())):
            r = dfg_today[dfg_today["vpc"] == vpc].iloc[0]
            pie_df = pd.DataFrame({
                "Estado": ["Passed", "Failed", "Unknown"],
                "Cantidad": [r["TotalPassed"], r["TotalFailed"], r["TotalUnknown"]]
            })
            fig_pie = px.pie(pie_df, names="Estado", values="Cantidad",
                             title=f"Distribución de controles — {vpc}",
                             hole=0.3)
            fig_pie.update_traces(textposition="inside", textinfo="percent+label")
            pie_cols[i % 2].plotly_chart(fig_pie, use_container_width=True)

# ===================================
# 2) Timeline Score semanal / mensual
# ===================================
with tab_timeline:
    st.subheader(f"Timeline del SecurityScore — {'últimos 7 días' if 'Semanal' in rango else 'últimos 30 días'}")
    dfg_range = dfg_last[(dfg_last["date"] >= start_range.strftime("%Y-%m-%d")) &
                         (dfg_last["date"] <= end_range.strftime("%Y-%m-%d"))].copy()
    if dfg_range.empty or dfg_range["SecurityScorePct"].dropna().empty:
        st.info("No hay SecurityScore numérico para graficar en el rango.")
    else:
        dfg_range["date_dt"] = pd.to_datetime(dfg_range["date"]).dt.date
        fig = px.line(
            dfg_range.sort_values(["date_dt", "vpc"]),
            x="date_dt",
            y="SecurityScorePct",
            color="vpc",
            markers=True,
            hover_data=["SecurityScoreRaw", "bucket_key", "timestamp", "momento"],
            labels={"date_dt": "Fecha", "SecurityScorePct": "SecurityScore (%)", "vpc": "VPC"},
            title="SecurityScore diario (último snapshot por día)"
        )
        fig.update_layout(yaxis=dict(range=[0, 100]))
        st.plotly_chart(fig, use_container_width=True)

# ===================================
# 3) Top de Tendencias (failed/passed ↑)
# ===================================
with tab_tendencias:
    st.subheader("Tendencias de Controles (incrementos)")
    st.caption("Se comparan los **últimos snapshots del día** por control.")

    # Ventanas de comparación
    day_str_today = target_date.strftime("%Y-%m-%d")
    day_str_prev = (target_date - timedelta(days=1)).strftime("%Y-%m-%d")
    day_str_prev7 = (target_date - timedelta(days=7)).strftime("%Y-%m-%d")

    curr = dfc_last[dfc_last["date"] == day_str_today].copy()
    prev = dfc_last[dfc_last["date"] == day_str_prev].copy()
    prev7 = dfc_last[dfc_last["date"] == day_str_prev7].copy()

    if vista_vpc == "VPC1":
        curr = curr[curr["vpc"] == "VPC1"]; prev = prev[prev["vpc"] == "VPC1"]; prev7 = prev7[prev7["vpc"] == "VPC1"]
    elif vista_vpc == "VPC2":
        curr = curr[curr["vpc"] == "VPC2"]; prev = prev[prev["vpc"] == "VPC2"]; prev7 = prev7[prev7["vpc"] == "VPC2"]

    def aggregate_controls(df):
        if df.empty:
            return df
        last_meta = df.sort_values("timestamp").groupby("control_id").tail(1)
        sums = df.groupby("control_id")[["passed", "failed", "warning", "no_data"]].sum().reset_index()
        out = pd.merge(
            sums,
            last_meta[["control_id","title","status","severity","ComplianceStatus","vpc"]],
            on="control_id", how="left"
        )
        return out

    agg_curr = aggregate_controls(curr)
    agg_prev = aggregate_controls(prev)
    agg_prev7 = aggregate_controls(prev7)

    def deltas(curr_df, base_df, metric: str):
        if curr_df.empty:
            return pd.DataFrame(columns=["control_id","title","severity","status","ComplianceStatus","curr","base","delta","vpc"])
        left = curr_df[["control_id","title","severity","status","ComplianceStatus","vpc",metric]].rename(columns={metric:"curr"})
        right = base_df[["control_id",metric]].rename(columns={metric:"base"}) if not base_df.empty else pd.DataFrame(columns=["control_id","base"])
        merged = pd.merge(left, right, on="control_id", how="left")
        merged["base"] = merged["base"].fillna(0).astype(int)
        merged["curr"] = merged["curr"].fillna(0).astype(int)
        merged["delta"] = merged["curr"] - merged["base"]
        out = merged[merged["delta"] > 0].sort_values("delta", ascending=False)
        return out

    st.markdown("#### Aumentos de **Failed**")
    col_day, col_week = st.columns(2)

    with col_day:
        st.write(f"**Último día**: {day_str_prev} → {day_str_today}")
        df_failed_day = deltas(agg_curr, agg_prev, "failed").head(top_n)
        if df_failed_day.empty:
            st.info("Sin incrementos en failed para el último día.")
        else:
            dfv = df_failed_day.copy()
            dfv["ComplianceStatus (emoji)"] = [
                compliance_to_emoji(cs, cs) for cs in dfv["ComplianceStatus"].fillna("No data")
            ]
            dfv = dfv[["control_id","title","severity","status","ComplianceStatus (emoji)","base","curr","delta"]]
            st.dataframe(dfv, use_container_width=True)

    with col_week:
        st.write(f"**Última semana**: {day_str_prev7} → {day_str_today}")
        df_failed_week = deltas(agg_curr, agg_prev7, "failed").head(top_n)
        if df_failed_week.empty:
            st.info("Sin incrementos en failed para la última semana.")
        else:
            dfw = df_failed_week.copy()
            dfw["ComplianceStatus (emoji)"] = [
                compliance_to_emoji(cs, cs) for cs in dfw["ComplianceStatus"].fillna("No data")
            ]
            dfw = dfw[["control_id","title","severity","status","ComplianceStatus (emoji)","base","curr","delta"]]
            st.dataframe(dfw, use_container_width=True)

    st.markdown("---")
    st.markdown("#### Aumentos de **Passed**")
    col_day2, col_week2 = st.columns(2)

    with col_day2:
        st.write(f"**Último día**: {day_str_prev} → {day_str_today}")
        df_passed_day = deltas(agg_curr, agg_prev, "passed").head(top_n)
        if df_passed_day.empty:
            st.info("Sin incrementos en passed para el último día.")
        else:
            dfv = df_passed_day.copy()
            dfv["ComplianceStatus (emoji)"] = [
                compliance_to_emoji(cs, cs) for cs in dfv["ComplianceStatus"].fillna("No data")
            ]
            dfv = dfv[["control_id","title","severity","status","ComplianceStatus (emoji)","base","curr","delta"]]
            st.dataframe(dfv, use_container_width=True)

    with col_week2:
        st.write(f"**Última semana**: {day_str_prev7} → {day_str_today}")
        df_passed_week = deltas(agg_curr, agg_prev7, "passed").head(top_n)
        if df_passed_week.empty:
            st.info("Sin incrementos en passed para la última semana.")
        else:
            dfw = df_passed_week.copy()
            dfw["ComplianceStatus (emoji)"] = [
                compliance_to_emoji(cs, cs) for cs in dfw["ComplianceStatus"].fillna("No data")
            ]
            dfw = dfw[["control_id","title","severity","status","ComplianceStatus (emoji)","base","curr","delta"]]
            st.dataframe(dfw, use_container_width=True)

    # ----- Descarga CSV (Tendencias) -----
    trends_parts = []
    if 'df_failed_day' in locals() and not df_failed_day.empty:
        t = df_failed_day.copy(); t["window"] = "day"; t["metric"] = "failed"; trends_parts.append(t)
    if 'df_failed_week' in locals() and not df_failed_week.empty:
        t = df_failed_week.copy(); t["window"] = "week"; t["metric"] = "failed"; trends_parts.append(t)
    if 'df_passed_day' in locals() and not df_passed_day.empty:
        t = df_passed_day.copy(); t["window"] = "day"; t["metric"] = "passed"; trends_parts.append(t)
    if 'df_passed_week' in locals() and not df_passed_week.empty:
        t = df_passed_week.copy(); t["window"] = "week"; t["metric"] = "passed"; trends_parts.append(t)

    if trends_parts:
        trends_export = pd.concat(trends_parts, ignore_index=True)
        trends_export = trends_export[["metric","window","control_id","title","severity","status","base","curr","delta"]]
        st.download_button(
            label="⬇️ Descargar CSV de Tendencias",
            data=trends_export.to_csv(index=False).encode("utf-8"),
            file_name=f"tendencias_{target_date:%Y%m%d}.csv",
            mime="text/csv"
        )

# ===================================
# 4) Línea base de Seguridad
# ===================================
with tab_baseline:
    st.subheader(f"Línea base — {target_date:%Y-%m-%d} (último snapshot por VPC)")
    if dfc_today.empty:
        st.info("No hay datos de controles para el día seleccionado.")
    else:
        vpcs = sorted(dfc_today["vpc"].unique())
        subtabs = st.tabs(vpcs)
        for idx, v in enumerate(vpcs):
            with subtabs[idx]:
                sub = dfc_today[dfc_today["vpc"] == v].copy()
                sub = sub.sort_values("timestamp").groupby("control_id").tail(1)
                sub["Compliance (emoji)"] = [
                    compliance_to_emoji(row["ComplianceStatus"], row["status"])
                    for _, row in sub.iterrows()
                ]
                show = sub[["control_id","title","status","severity","Compliance (emoji)","passed","failed"]]
                show = show.sort_values(["severity","control_id"])
                st.dataframe(show, use_container_width=True)

        # Descarga CSV Baseline
        baseline_export = dfc_today.sort_values("timestamp").groupby(["vpc","control_id"]).tail(1).copy()
        baseline_export["Compliance (emoji)"] = [
            compliance_to_emoji(row["ComplianceStatus"], row["status"])
            for _, row in baseline_export.iterrows()
        ]
        baseline_export = baseline_export[["vpc","control_id","title","status","severity","Compliance (emoji)","passed","failed"]]
        st.download_button(
            label="⬇️ Descargar CSV de Baseline",
            data=baseline_export.to_csv(index=False).encode("utf-8"),
            file_name=f"baseline_{target_date:%Y%m%d}.csv",
            mime="text/csv"
        )

# ===================================
# 5) Analítica Avanzada (6 métricas/gráficos)
# ===================================
with tab_advanced:
    st.subheader("Analítica Avanzada")

    # Rango de trabajo para analítica: usar dfg_last/dfc_last en [start_range, end_range]
    dfg_range = dfg_last[(dfg_last["date"] >= start_range.strftime("%Y-%m-%d")) &
                         (dfg_last["date"] <= end_range.strftime("%Y-%m-%d"))].copy()
    dfc_range = dfc_last[(dfc_last["date"] >= start_range.strftime("%Y-%m-%d")) &
                         (dfc_last["date"] <= end_range.strftime("%Y-%m-%d"))].copy()

    # ---------- 1) Coverage Gap ----------
    st.markdown("### 1) Coverage Gap (Enabled vs Disabled vs NoData)")
    if dfg_today.empty:
        st.info("Sin datos del día para calcular cobertura.")
    else:
        cov_rows = []
        for vpc in sorted(dfg_today["vpc"].unique()):
            r = dfg_today[dfg_today["vpc"] == vpc].iloc[0]
            cov_rows.append({
                "vpc": vpc,
                "Enabled": int(r.get("TotalEnabled") or 0),
                "Disabled": int(r.get("TotalDisabled") or 0),
                "NoData": int(r.get("TotalNoData") or 0),
                "TotalControls": int(r.get("TotalControls") or 0),
            })
        cov_df = pd.DataFrame(cov_rows)
        cov_long = cov_df.melt(id_vars=["vpc","TotalControls"], value_vars=["Enabled","Disabled","NoData"],
                               var_name="Estado", value_name="Cantidad")
        fig_cov = px.bar(cov_long, x="vpc", y="Cantidad", color="Estado", barmode="stack",
                         title=f"Coverage Gap — {target_date:%Y-%m-%d}")
        st.plotly_chart(fig_cov, use_container_width=True)
        st.download_button(
            "⬇️ CSV Coverage Gap (día)",
            data=cov_long.to_csv(index=False).encode("utf-8"),
            file_name=f"coverage_gap_{target_date:%Y%m%d}.csv",
            mime="text/csv"
        )

    # Coverage trend (% habilitado)
    if dfg_range.empty:
        st.info("Sin datos en el rango para cobertura temporal.")
    else:
        cov_tr = dfg_range.copy()
        cov_tr["coverage_pct"] = (cov_tr["TotalEnabled"].astype(float) / cov_tr["TotalControls"].astype(float) * 100.0)
        cov_tr["date_dt"] = pd.to_datetime(cov_tr["date"]).dt.date
        fig_cov_tr = px.line(cov_tr, x="date_dt", y="coverage_pct", color="vpc", markers=True,
                             labels={"date_dt":"Fecha","coverage_pct":"Cobertura habilitada (%)","vpc":"VPC"},
                             title="Cobertura habilitada en el tiempo (último snapshot por día)")
        fig_cov_tr.update_layout(yaxis=dict(range=[0, 100]))
        st.plotly_chart(fig_cov_tr, use_container_width=True)
        st.download_button(
            "⬇️ CSV Coverage Trend",
            data=cov_tr[["vpc","date","coverage_pct","TotalEnabled","TotalControls"]].to_csv(index=False).encode("utf-8"),
            file_name=f"coverage_trend_{start_range:%Y%m%d}_{end_range:%Y%m%d}.csv",
            mime="text/csv"
        )

    st.divider()

    # ---------- 2) Tasa de Fallo Efectiva ----------
    st.markdown("### 2) Tasa de fallo efectiva")
    if dfg_range.empty:
        st.info("Sin datos en el rango para tasa de fallo.")
    else:
        fr = dfg_range.copy()
        denom = (fr["TotalPassed"].fillna(0).astype(float) + fr["TotalFailed"].fillna(0).astype(float))
        fr["fail_rate_pct"] = (fr["TotalFailed"].fillna(0).astype(float) / denom.replace(0, pd.NA) * 100.0)
        fr["date_dt"] = pd.to_datetime(fr["date"]).dt.date
        fig_fr = px.line(fr, x="date_dt", y="fail_rate_pct", color="vpc", markers=True,
                         labels={"date_dt":"Fecha","fail_rate_pct":"Tasa de fallo efectiva (%)","vpc":"VPC"},
                         title="Tasa de fallo entre controles evaluados (último snapshot por día)")
        fig_fr.update_layout(yaxis=dict(range=[0, 100]))
        st.plotly_chart(fig_fr, use_container_width=True)
        st.download_button(
            "⬇️ CSV Tasa de fallo",
            data=fr[["vpc","date","TotalPassed","TotalFailed","fail_rate_pct"]].to_csv(index=False).encode("utf-8"),
            file_name=f"fail_rate_{start_range:%Y%m%d}_{end_range:%Y%m%d}.csv",
            mime="text/csv"
        )

    st.divider()

    # ---------- 3) Treemap por severidad y familia ----------
    st.markdown("### 3) Treemap de fallos por severidad y familia")
    if dfc_today.empty:
        st.info("Sin datos del día para treemap.")
    else:
        tm = dfc_today.copy()
        tm["family"] = tm["control_id"].apply(control_family)
        tm_grp = tm.groupby(["family","severity"], as_index=False)["failed"].sum()
        if tm_grp["failed"].sum() == 0:
            st.info("No hay fallos para treemap en el día.")
        else:
            fig_tm = px.treemap(
                tm_grp, path=["family","severity"], values="failed",
                title=f"Fallos por familia y severidad — {target_date:%Y-%m-%d}",
                color="severity", color_discrete_map={
                    "CRITICAL":"#8B0000","HIGH":"#E74C3C","MEDIUM":"#F39C12","LOW":"#27AE60","INFORMATIONAL":"#3498DB", None:"#95A5A6"
                }
            )
            st.plotly_chart(fig_tm, use_container_width=True)
            st.download_button(
                "⬇️ CSV Treemap (día)",
                data=tm_grp.to_csv(index=False).encode("utf-8"),
                file_name=f"treemap_failed_{target_date:%Y%m%d}.csv",
                mime="text/csv"
            )

    st.divider()

    # ---------- 4) Heatmap de ΔFailed ----------
    st.markdown("### 4) Heatmap de cambio diario en fallos (ΔFailed)")
    if dfc_range.empty:
        st.info("Sin datos de controles en el rango.")
    else:
        # failed por control y fecha (agregado VPC1+VPC2 para claridad de calor)
        failed_daily = dfc_range.groupby(["control_id","date"], as_index=False)["failed"].sum()
        # pivot a fechas
        pvt = failed_daily.pivot(index="control_id", columns="date", values="failed").sort_index()
        # calcular delta respecto al día previo por fila
        pvt_delta = pvt.diff(axis=1).fillna(0).astype(int)
        # conservar top N por suma de |delta| para visual
        pvt_delta["abs_change"] = pvt_delta.abs().sum(axis=1)
        pvt_top = pvt_delta.sort_values("abs_change", ascending=False).head(max(top_n, 10)).drop(columns=["abs_change"])
        if pvt_top.empty:
            st.info("No hay cambios significativos para heatmap.")
        else:
            fig_hm = px.imshow(
                pvt_top,
                labels=dict(x="Fecha", y="Control", color="ΔFailed"),
                title=f"ΔFailed por control (día a día) — {start_range:%Y-%m-%d} → {end_range:%Y-%m-%d}",
                aspect="auto", color_continuous_scale="RdBu", origin="upper"
            )
            st.plotly_chart(fig_hm, use_container_width=True)
            # Export
            hm_export = pvt_top.reset_index()
            st.download_button(
                "⬇️ CSV Heatmap ΔFailed",
                data=hm_export.to_csv(index=False).encode("utf-8"),
                file_name=f"heatmap_delta_failed_{start_range:%Y%m%d}_{end_range:%Y%m%d}.csv",
                mime="text/csv"
            )

    st.divider()

    # ---------- 5) Top “Flapping” Controls ----------
    st.markdown("### 5) Controles 'flapping' (cambios frecuentes de estado)")
    if dfc_range.empty:
        st.info("Sin datos de controles en el rango.")
    else:
        # Tomar ComplianceStatus por control y VPC (para capturar cambios por cuenta)
        fl = dfc_range.sort_values(["vpc","control_id","date"]).copy()
        fl["ComplianceStatus_norm"] = fl["ComplianceStatus"].fillna("No data")
        # contar transiciones por (vpc, control_id)
        transitions = []
        for (vpc, cid), grp in fl.groupby(["vpc","control_id"], as_index=False):
            seq = grp["ComplianceStatus_norm"].tolist()
            changes = sum(1 for i in range(1, len(seq)) if seq[i] != seq[i-1])
            transitions.append({"control_id": cid, "vpc": vpc, "transitions": changes})
        fl_df = pd.DataFrame(transitions)
        if fl_df.empty or fl_df["transitions"].sum() == 0:
            st.info("No se detectaron cambios de estado.")
        else:
            # Agregar por control (suma de transiciones entre VPCs)
            fl_top = fl_df.groupby("control_id", as_index=False)["transitions"].sum().sort_values("transitions", ascending=False) # type: ignore
            fl_top = fl_top.head(max(top_n, 10))
            fig_fl = px.bar(fl_top, x="control_id", y="transitions", title="Top controles por cambios de estado", labels={"control_id":"Control","transitions":"#Cambios"})
            st.plotly_chart(fig_fl, use_container_width=True)
            st.download_button(
                "⬇️ CSV Flapping Controls",
                data=fl_top.to_csv(index=False).encode("utf-8"),
                file_name=f"flapping_controls_{start_range:%Y%m%d}_{end_range:%Y%m%d}.csv",
                mime="text/csv"
            )

    st.divider()

    # ---------- 6) Pareto de Fallos ----------
    st.markdown("### 6) Pareto de fallos")
    if dfc_range.empty:
        st.info("Sin datos para Pareto.")
    else:
        par = dfc_range.groupby("control_id", as_index=False)["failed"].sum().sort_values("failed", ascending=False) # type: ignore
        par["accum"] = par["failed"].cumsum()
        total_failed = par["failed"].sum()
        if total_failed == 0:
            st.info("No hay fallos acumulados para construir Pareto.")
        else:
            par["accum_pct"] = par["accum"] / total_failed * 100.0
            # Gráfico combinado
            fig_par = go.Figure()
            fig_par.add_trace(go.Bar(x=par["control_id"], y=par["failed"], name="Fallos"))
            fig_par.add_trace(go.Scatter(x=par["control_id"], y=par["accum_pct"], mode="lines+markers", name="% acumulado", yaxis="y2"))
            fig_par.update_layout(
                title="Pareto de fallos por control",
                xaxis_title="Control",
                yaxis=dict(title="Fallos"),
                yaxis2=dict(title="% acumulado", overlaying="y", side="right", range=[0, 100]),
                legend=dict(orientation="h", y=-0.2)
            )
            st.plotly_chart(fig_par, use_container_width=True)
            # Export
            st.download_button(
                "⬇️ CSV Pareto de Fallos",
                data=par[["control_id","failed","accum","accum_pct"]].to_csv(index=False).encode("utf-8"),
                file_name=f"pareto_failed_{start_range:%Y%m%d}_{end_range:%Y%m%d}.csv",
                mime="text/csv"
            )

# ===================================
# Notas
# ===================================
st.markdown(
    f"""
**Notas:**
- Se usa el **último snapshot del día** para KPIs, Timeline por día y comparaciones de tendencias.
- Si un control está **DISABLED** o no posee `results`, sus contadores se tratan como 0 en deltas y analítica.
- Estructura esperada en S3: `s3://<bucket>/{ROOT_PREFIX}YYYY/MM/DD/control_status_VPCX_YYYYMMDD_HHMMSS.json`.
- Ejemplo: `{bucket}/{ROOT_PREFIX}2026/02/27/control_status_VPC1_20260227_220535.json`
- El bucket se toma de `ENV SECURITYHUB_BUCKET`; puedes sobreescribirlo en la barra lateral.
    """
)