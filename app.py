import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import json
import pytz

st.set_page_config(page_title="Отчет по заявкам ЦДС водопровод", layout="wide")

# === Кастомные стили ===
st.markdown("""
<style>
    .main { background-color: #f8fafc; }
    .stApp { background-color: #f8fafc; }
    h1 {
        color: #0f172a;
        font-weight: 700;
        margin-bottom: 0.3em;
    }
    h2 {
        color: #1e293b;
        font-weight: 600;
        margin-top: 1.5em;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 700;
    }
    [data-testid="stMetricLabel"] {
        font-size: 1rem !important;
        color: #475569;
    }
    .dataframe {
        font-size: 0.95rem;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
    }
    .dataframe th {
        background-color: #e2e8f0 !important;
        color: #1e293b !important;
        font-weight: 600;
    }
    .dataframe td {
        background-color: white !important;
        color: #334155 !important;
    }
    .stSelectbox > div > div {
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 4px 8px;
    }
</style>
""", unsafe_allow_html=True)

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

# === UI ===
st.set_page_config(page_title="Отчет по заявкам ЦДС водопровод", layout="wide")

st.title("Отчет по заявкам ЦДС водопровод")
st.subheader("2025 год - РВК")

selected = st.selectbox(
    "Выберите период",
    options=list(DISPLAY_NAMES.keys()),
    format_func=lambda x: DISPLAY_NAMES[x],
    index=0
)

# Загрузка данных
try:
    df = load_data(selected)
except Exception as e:
    st.error(f"Ошибка при загрузке листа '{SHEET_NAMES[selected]}': {e}")
    st.stop()

# Преобразование в числа
numeric_cols = ["total", "closed", "open", "cancelled", "erroneous"]
for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

# Подготовка для графиков
active = df[df["total"] > 0].copy()
active["org_label"] = active["organization"].apply(lambda x: x[:15] + "..." if len(x) > 15 else x)

# Статистика
total = df["total"].sum()
closed = df["closed"].sum()
open_ = df["open"].sum()
cancelled = df["cancelled"].sum()

# Карточки с эмодзи
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("📄 Всего заявок", total)
with col2:
    st.metric("✅ Закрытых", closed, delta="100%" if total == closed and total > 0 else None)
with col3:
    st.metric("⚠️ Открытых", open_, delta="Требуют внимания" if open_ > 0 else None)
with col4:
    st.metric("❌ Отменённых", cancelled)

# Графики
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
                "Закрыто": "#4ade80",
                "Открыто": "#fbbf24",
                "Отменено": "#f87171"
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

# Таблица с русскими заголовками
display_df = df.rename(columns={
    "organization": "Организация",
    "total": "Всего",
    "closed": "Закрыто",
    "open": "Открыто",
    "cancelled": "Отменено",
    "erroneous": "Ошибочно"
})
st.subheader("Детальная информация")
st.dataframe(display_df, use_container_width=True)

# Время в Астане
astana_tz = pytz.timezone("Asia/Almaty")
current_time = datetime.now(astana_tz).strftime('%d.%m.%Y %H:%M')
st.caption(f"Данные обновлены: {current_time}")
