import streamlit as st

# === АУТЕНТИФИКАЦИЯ ===
def check_password():
    def login_form():
        st.markdown("### 🔒 Доступ для руководства")
        with st.form("login"):
            st.text_input("Логин", key="username")
            st.text_input("Пароль", type="password", key="password")
            if st.form_submit_button("Войти"):
                if (
                    st.session_state.username == st.secrets["AUTH_USERNAME"]
                    and st.session_state.password == st.secrets["AUTH_PASSWORD"]
                ):
                    st.session_state.authenticated = True
                    del st.session_state.username
                    del st.session_state.password
                    st.rerun()
                else:
                    st.error("❌ Неверный логин или пароль")
    
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        login_form()
        st.stop()

check_password()

# === ОСНОВНОЙ КОД ===
import pandas as pd
import plotly.express as px
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import json
import pytz
import time

st.set_page_config(page_title="Отчет по заявкам ЦДС водопровод", layout="wide")

# === СТИЛЬ ВТОРОГО ДАШБОРДА ===
st.markdown("""
<style>
    :root {
        --primary: #2563eb;
        --success: #10b981;
        --warning: #f59e0b;
        --danger: #ef4444;
        --bg: #f8fafc;
        --card-bg: white;
        --text: #1e293b;
        --text-light: #64748b;
        --shadow: 0 4px 12px rgba(0,0,0,0.05);
    }

    .main { background-color: var(--bg); padding: 20px !important; }
    .stApp { background-color: var(--bg); }

    h1 {
        font-size: 2.2rem !important;
        color: var(--text);
        font-weight: 700;
        margin-bottom: 0.5em;
    }
    h2 {
        font-size: 1.6rem !important;
        color: var(--text);
        margin-top: 1.5em;
        margin-bottom: 0.8em;
    }

    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 700;
        color: var(--text);
    }
    [data-testid="stMetricLabel"] {
        font-size: 1.1rem !important;
        color: var(--text-light);
    }

    .dataframe {
        font-size: 1.05rem;
        border-radius: 10px;
        box-shadow: var(--shadow);
    }

    .stButton > button {
        height: 44px !important;
        font-size: 0.95rem !important;
        font-weight: 500;
        border-radius: 6px;
    }

    @media print {
        @page { size: A4; margin: 1cm; }
        * { zoom: 0.85 !important; }
    }
</style>
""", unsafe_allow_html=True)

st.title("Отчет по заявкам ЦДС водопровод")
st.subheader("2025 год – РВК")

# === Конфигурация листов ===
SHEET_NAMES = {
    "jan": "jan", "feb": "feb", "mar": "mar", "apr": "apr", "may": "may",
    "jun": "june", "jul": "jule", "aug": "aug", "sep": "sept", "oct": "oct",
    "nov": "nov", "dec": "dec", "year": "gen"
}

DISPLAY_NAMES = {
    "jan": "Янв", "feb": "Фев", "mar": "Мар", "apr": "Апр", "may": "Май",
    "jun": "Июн", "jul": "Июл", "aug": "Авг", "sep": "Сен", "oct": "Окт",
    "nov": "Ноя", "dec": "Дек", "year": "Год"
}

# === Кнопки месяцев ===
st.markdown("#### Период:")
months = list(DISPLAY_NAMES.items())
for i in range(0, len(months), 6):
    row = months[i:i+6]
    cols = st.columns(len(row))
    for j, (key, name) in enumerate(row):
        with cols[j]:
            if st.button(name, key=f"btn_{key}", use_container_width=True):
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

def load_data(period_key: str) -> pd.DataFrame:
    client = get_client()
    sheet_name = SHEET_NAMES[period_key]
    for attempt in range(3):
        try:
            worksheet = client.open_by_key("1v6GS19Ib3wnl5RGpDz31KPzDJ5T1pxd6rx1aTYzy63k").worksheet(sheet_name)
            values = worksheet.get("A4:F13")
            break
        except gspread.exceptions.APIError as e:
            if e.response.status_code == 500 and attempt < 2:
                time.sleep(1.5 ** attempt)
                continue
            else:
                raise
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

# === Загрузка данных ===
try:
    df = load_data(selected)
except Exception as e:
    st.error(f"Ошибка загрузки листа '{SHEET_NAMES[selected]}': {e}")
    st.stop()

numeric_cols = ["total", "closed", "open", "cancelled", "erroneous"]
for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

# === Статистика (как во втором дашборде) ===
total = df["total"].sum()
closed = df["closed"].sum()
open_ = df["open"].sum()
cancelled = df["cancelled"].sum()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Всего заявок", total)
with col2:
    st.metric("Закрытых заявок", closed, delta="100% выполнение" if total > 0 and closed == total else None)
with col3:
    st.metric("Открытых заявок", open_, delta="Требуют внимания" if open_ > 0 else None)
with col4:
    st.metric("Отмененных заявок", cancelled, delta="Ошибочно или отменено" if cancelled > 0 else None)

# === Графики (в стиле второго дашборда) ===
active = df[df["total"] > 0].copy()
if not active.empty:
    # Подготовка данных: только "Всего" и "Закрыто"
    chart_data = active[["organization", "total", "closed"]].rename(columns={
        "organization": "Организация",
        "total": "Всего",
        "closed": "Закрыто"
    })
    
    g1, g2 = st.columns(2)
    with g1:
        fig1 = px.pie(
            chart_data,
            values="Всего",
            names="Организация",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig1.update_traces(
            textposition="inside",
            textinfo="percent+label",
            hovertemplate="<b>%{label}</b><br>Заявок: %{value}<extra></extra>"
        )
        fig1.update_layout(
            title="Распределение по организациям",
            title_x=0.5,
            showlegend=False,
            margin=dict(t=40, b=20, l=20, r=20),
            font_size=12
        )
        st.plotly_chart(fig1, use_container_width=True, config={"displayModeBar": False})
    
    with g2:
        fig2 = px.bar(
            chart_data.melt(id_vars="Организация", value_vars=["Всего", "Закрыто"]),
            x="Организация",
            y="value",
            color="variable",
            barmode="group",
            color_discrete_map={"Всего": "#2563eb", "Закрыто": "#10b981"}
        )
        fig2.update_layout(
            title="Всего vs Закрыто",
            title_x=0.5,
            xaxis_tickangle=-45,
            margin=dict(t=40, b=100, l=40, r=20),
            legend_title_text="",
            font_size=11
        )
        fig2.update_traces(hovertemplate="<b>%{x}</b><br>%{y}<extra></extra>")
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

# === Время Астаны ===
astana_tz = pytz.timezone("Asia/Almaty")
current_time = datetime.now(astana_tz).strftime('%d.%m.%Y %H:%M')
st.caption(f"Данные обновлены: {current_time} (Астана)")
