import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import json
import pytz

# ⬇️ ОБЯЗАТЕЛЬНО ПЕРВАЯ КОМАНДА
st.set_page_config(page_title="Отчет по заявкам ЦДС водопровод", layout="wide")

# === Тема: переключатель в сайдбаре ===
with st.sidebar:
    st.markdown("### 🎨 Оформление")
    theme = st.radio("Тема", ["Светлая", "Тёмная"], index=0, horizontal=True)
    show_totals = st.checkbox("Показать ИТОГО", value=True)

# === Цветовая палитра (водная тематика) ===
COLORS = {
    "primary": "#0d9488",      # бирюзовый — основной (успех)
    "secondary": "#0ea5e9",    # ярко-голубой — акцент
    "warning": "#f59e0b",      # янтарный — внимание
    "danger": "#ef4444",       # красный — ошибка
    "light_bg": "#f8fafc",
    "dark_bg": "#0f172a",
    "light_text": "#1e293b",
    "dark_text": "#f1f5f9"
}

# === CSS под тему ===
if theme == "Тёмная":
    bg = COLORS["dark_bg"]
    text = COLORS["dark_text"]
    metric_label = "#cbd5e1"
    metric_value = COLORS["dark_text"]
    table_header = "#1e293b"
    table_cell = "#1e293b"
    table_text = "#e2e8f0"
else:
    bg = COLORS["light_bg"]
    text = COLORS["light_text"]
    metric_label = "#475569"
    metric_value = COLORS["light_text"]
    table_header = "#e2e8f0"
    table_cell = "white"
    table_text = "#334155"

st.markdown(f"""
<style>
    .main {{ background-color: {bg}; color: {text}; }}
    .stApp {{ background-color: {bg}; }}
    h1, h2, h3 {{ color: {text} !important; }}
    [data-testid="stMetricLabel"] {{ color: {metric_label} !important; }}
    [data-testid="stMetricValue"] {{ color: {metric_value} !important; }}
    .dataframe {{
        font-size: 0.95rem;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
    }}
    .dataframe th {{
        background-color: {table_header} !important;
        color: {text} !important;
        font-weight: 600;
    }}
    .dataframe td {{
        background-color: {table_cell} !important;
        color: {table_text} !important;
    }}
    .stSelectbox > div > div {{
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 4px 8px;
    }}
</style>
""", unsafe_allow_html=True)

# === Заголовок с эмодзи ===
st.title("💧 Отчет по заявкам ЦДС водопровод")
st.subheader("2025 год - РВК")

# === Конфигурация ===
SHEET_ID = "1v6GS19Ib3wnl5RGpDz31KPzDJ5T1pxd6rx1aTYzy63k"

SHEET_NAMES = {
    "jan": "jan", "feb": "feb", "mar": "mar", "apr": "apr", "may": "may",
    "jun": "jun", "jul": "jul", "aug": "aug", "sep": "sep", "oct": "oct",
    "nov": "nov", "dec": "dec", "year": "gen"
}

DISPLAY_NAMES = {
    "jan": "Янв", "feb": "Фев", "mar": "Мар", "apr": "Апр", "may": "Май",
    "jun": "Июн", "jul": "Июл", "aug": "Авг", "sep": "Сен", "oct": "Окт",
    "nov": "Ноя", "dec": "Дек", "year": "Год"
}

# === Подключение к Google Sheets ===
@st.cache_resource
def get_client():
    try:
        info = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
        creds = Credentials.from_service_account_info(
            info,
            scopes=[
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive"
            ]
        )
    except KeyError:
        creds = Credentials.from_service_account_file(
            "credentials.json",
            scopes=[
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive"
            ]
        )
    return gspread.authorize(creds)

def load_data(period_key: str) -> pd.DataFrame:
    client = get_client()
    sheet_name = SHEET_NAMES[period_key]
    worksheet = client.open_by_key(SHEET_ID).worksheet(sheet_name)
    range_name = "A4:F13"
    try:
        values = worksheet.get(range_name)
    except Exception:
        values = []
    columns = ["organization", "total", "closed", "open", "cancelled", "erroneous"]
    if not values:
        return pd.DataFrame(columns=columns)
    cleaned = [row for row in values if row and str(row[0]).strip()]
    normalized = []
    for row in cleaned:
        while len(row) < len(columns):
            row.append("")
        normalized.append(row[:len(columns)])
    return pd.DataFrame(normalized, columns=columns)

# === Выбор периода ===
selected = st.selectbox(
    "Выберите период",
    options=list(DISPLAY_NAMES.keys()),
    format_func=lambda x: DISPLAY_NAMES[x],
    index=0
)

# === Загрузка данных ===
try:
    df = load_data(selected)
except Exception as e:
    st.error(f"Ошибка при загрузке листа '{SHEET_NAMES[selected]}': {e}")
    st.stop()

# === Преобразование чисел ===
numeric_cols = ["total", "closed", "open", "cancelled", "erroneous"]
for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

# === Подготовка для графиков ===
active = df[df["total"] > 0].copy()
active["org_label"] = active["organization"].apply(lambda x: x[:15] + "..." if len(x) > 15 else x)

# === Статистика ===
total = df["total"].sum()
closed = df["closed"].sum()
open_ = df["open"].sum()
cancelled = df["cancelled"].sum()

# === Карточки ===
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("📄 Всего заявок", total)
with col2:
    st.metric("✅ Закрытых", closed, delta="100%" if total == closed and total > 0 else None)
with col3:
    st.metric("⚠️ Открытых", open_, delta="Требуют внимания" if open_ > 0 else None)
with col4:
    st.metric("❌ Отменённых", cancelled)

# === Графики ===
if not active.empty:
    g1, g2 = st.columns(2)
    
    with g1:
        fig1 = px.pie(
            active,
            values="total",
            names="organization",
            title="Распределение по организациям",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig1.update_traces(textposition="inside", textinfo="percent+label")
        fig1.update_layout(
            title_x=0.5,
            showlegend=False,
            margin=dict(t=50, b=20, l=20, r=20)
        )
        st.plotly_chart(fig1, use_container_width=True)
    
    with g2:
        active_display = active.rename(columns={
            "closed": "Закрыто",
            "open": "Открыто",
            "cancelled": "Отменено"
        })
        fig2 = px.bar(
            active_display,
            x="org_label",
            y=["Закрыто", "Открыто", "Отменено"],
            title="Статус заявок",
            labels={"value": "Количество", "org_label": "Организация"},
            barmode="stack",
            color_discrete_map={
                "Закрыто": COLORS["primary"],
                "Открыто": COLORS["warning"],
                "Отменено": COLORS["danger"]
            }
        )
        fig2.update_layout(
            title_x=0.5,
            xaxis_tickangle=-45,
            margin=dict(t=50, b=100, l=40, r=20),
            legend_title_text="Статус"
        )
        st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("Нет организаций с заявками.")

# === Таблица с ИТОГО ===
display_df = df.rename(columns={
    "organization": "Организация",
    "total": "Всего",
    "closed": "Закрыто",
    "open": "Открыто",
    "cancelled": "Отменено",
    "erroneous": "Ошибочно"
})

if show_totals and len(display_df) > 0:
    total_row = pd.DataFrame([{
        "Организация": "ИТОГО",
        "Всего": display_df["Всего"].sum(),
        "Закрыто": display_df["Закрыто"].sum(),
        "Открыто": display_df["Открыто"].sum(),
        "Отменено": display_df["Отменено"].sum(),
        "Ошибочно": display_df["Ошибочно"].sum()
    }])
    display_df = pd.concat([display_df, total_row], ignore_index=True)

st.subheader("Детальная информация")
st.dataframe(display_df, use_container_width=True)

# === Время в Астане ===
astana_tz = pytz.timezone("Asia/Almaty")
current_time = datetime.now(astana_tz).strftime('%d.%m.%Y %H:%M')
st.caption(f"Данные обновлены: {current_time}")
