import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import json
import pytz

# ⬇️ Первая команда
st.set_page_config(page_title="Отчет по заявкам ЦДС водопровод", layout="wide")

# === Тема и печать ===
with st.sidebar:
    st.markdown("### 🎨 Оформление")
    theme = st.radio("Тема", ["Светлая", "Тёмная"], index=0, horizontal=True)
    st.markdown("### 🖨️ Печать")
    st.info("Для печати: Ctrl+P → «Сохранить как PDF»")

# === Исправленные имена листов ===
SHEET_NAMES = {
    "jan": "jan",
    "feb": "feb",
    "mar": "mar",
    "apr": "apr",
    "may": "may",
    "jun": "june",    # ← исправлено
    "jul": "jule",    # ← исправлено
    "aug": "aug",
    "sep": "sept",    # ← исправлено
    "oct": "oct",
    "nov": "nov",
    "dec": "dec",
    "year": "gen"
}

DISPLAY_NAMES = {
    "jan": "Январь", "feb": "Фев", "mar": "Мар", "apr": "Апр", "may": "Май",
    "jun": "Июн", "jul": "Июл", "aug": "Авг", "sep": "Сен", "oct": "Окт",
    "nov": "Ноя", "dec": "Дек", "year": "Год"
}

MONTH_KEYS = list(DISPLAY_NAMES.keys())

COLORS = {
    "primary": "#0d9488",
    "secondary": "#0ea5e9",
    "warning": "#f59e0b",
    "danger": "#ef4444",
    "light_bg": "#ffffff",  # ← белый фон для печати
    "dark_bg": "#f8fafc",
    "light_text": "#1e293b",
    "dark_text": "#1e293b"
}

# === CSS: компактный + печать ===
bg = COLORS["light_bg"]  # всегда белый для печати
text = COLORS["light_text"]

st.markdown(f"""
<style>
    .main {{ background-color: {bg}; color: {text}; padding: 10px !important; }}
    .stApp {{ background-color: {bg}; }}

    /* Заголовки — компактные */
    h1 {{ font-size: 1.8rem; margin-bottom: 0.4em; }}
    h2 {{ font-size: 1.4rem; margin-top: 1.2em; margin-bottom: 0.6em; }}

    /* Метрики — компактные */
    [data-testid="stMetricLabel"] {{ font-size: 0.9rem !important; }}
    [data-testid="stMetricValue"] {{ font-size: 1.4rem !important; }}

    /* Графики — меньше отступы */
    .plotly-graph-div {{
        border-radius: 8px !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05) !important;
        margin-bottom: 12px !important;
    }}

    /* Таблица */
    .dataframe {{
        font-size: 0.95rem;
        border-radius: 6px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.05);
        margin-bottom: 16px;
    }}
    .dataframe th, .dataframe td {{
        padding: 8px 10px !important;
    }}

    /* Кнопки месяцев — компактные */
    .stButton > button {{
        padding: 6px 10px !important;
        font-size: 0.85rem !important;
    }}

    /* Скрыть сайдбар и кнопки при печати */
    @media print {{
        .sidebar, .stSidebar, [data-testid="stSidebar"],
        .stButton, .stRadio, .stCheckbox {{
            display: none !important;
        }}
        .main {{
            padding: 0 !important;
        }}
        .plotly-graph-div {{
            box-shadow: none !important;
        }}
        body {{
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
        }}
    }}
</style>
""", unsafe_allow_html=True)

# === Заголовок ===
st.title("💧 Отчет по заявкам ЦДС водопровод")
st.subheader("2025 год – РВК")

# === Кнопки месяцев (в 2 строки для компактности) ===
row1 = MONTH_KEYS[:7]
row2 = MONTH_KEYS[7:]

st.markdown("#### Период:")
cols1 = st.columns(len(row1))
for i, key in enumerate(row1):
    with cols1[i]:
        if st.button(DISPLAY_NAMES[key], key=f"btn_{key}"):
            st.session_state.selected = key

cols2 = st.columns(len(row2))
for i, key in enumerate(row2):
    with cols2[i]:
        if st.button(DISPLAY_NAMES[key], key=f"btn2_{key}"):
            st.session_state.selected = key

selected = st.session_state.get("selected", "jan")

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

def load_data(period_key):
    client = get_client()
    sheet_name = SHEET_NAMES[period_key]
    worksheet = client.open_by_key("1v6GS19Ib3wnl5RGpDz31KPzDJ5T1pxd6rx1aTYzy63k").worksheet(sheet_name)
    values = worksheet.get("A4:F13")
    columns = ["organization", "total", "closed", "open", "cancelled", "erroneous"]
    cleaned = [row for row in values if row and str(row[0]).strip()]
    normalized = []
    for row in cleaned:
        while len(row) < len(columns):
            row.append("")
        normalized.append(row[:len(columns)])
    return pd.DataFrame(normalized, columns=columns)

# === Загрузка данных ===
try:
    df = load_data(selected)
except Exception as e:
    st.error(f"Ошибка загрузки листа '{SHEET_NAMES[selected]}': {e}")
    st.stop()

numeric_cols = ["total", "closed", "open", "cancelled", "erroneous"]
for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

# === Статистика ===
total = df["total"].sum()
closed = df["closed"].sum()
open_ = df["open"].sum()
cancelled = df["cancelled"].sum()

col1, col2, col3, col4 = st.columns(4)
with col1: st.metric("📄 Всего", total)
with col2: st.metric("✅ Закрыто", closed)
with col3: st.metric("⚠️ Открыто", open_)
with col4: st.metric("❌ Отменено", cancelled)

# === Графики ===
active = df[df["total"] > 0].copy()
if not active.empty:
    active["org_label"] = active["organization"].apply(lambda x: x[:12] + "..." if len(x) > 12 else x)
    
    g1, g2 = st.columns(2)
    with g1:
        fig1 = px.pie(active, values="total", names="organization", hole=0.4)
        fig1.update_traces(textposition="inside", textinfo="percent+label", hovertemplate="<b>%{label}</b><br>Заявок: %{value}<extra></extra>")
        fig1.update_layout(title="По организациям", title_x=0.5, showlegend=False, margin=dict(t=40, b=10, l=10, r=10), font_size=11)
        st.plotly_chart(fig1, use_container_width=True, config={"displayModeBar": False})
    
    with g2:
        active_disp = active.rename(columns={"closed": "Закрыто", "open": "Открыто", "cancelled": "Отменено"})
        fig2 = px.bar(active_disp, x="org_label", y=["Закрыто", "Открыто", "Отменено"], barmode="stack",
                      color_discrete_map={"Закрыто": COLORS["primary"], "Открыто": COLORS["warning"], "Отменено": COLORS["danger"]})
        fig2.update_layout(title="Статус заявок", title_x=0.5, xaxis_tickangle=-45, margin=dict(t=40, b=80, l=30, r=10), font_size=10, showlegend=False)
        fig2.update_traces(hovertemplate="<b>%{x}</b><br>%{series}: %{y}<extra></extra>")
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

# === Таблица ===
display_df = df.rename(columns={
    "organization": "Организация",
    "total": "Всего",
    "closed": "Закрыто",
    "open": "Открыто",
    "cancelled": "Отменено",
    "erroneous": "Ошибочно"
})
st.subheader("Детальная информация")
st.dataframe(display_df, use_container_width=True, hide_index=True)

# === Подпись ===
astana_tz = pytz.timezone("Asia/Almaty")
current_time = datetime.now(astana_tz).strftime('%d.%m.%Y %H:%M')
st.caption(f"Данные обновлены: {current_time} (Астана)")
