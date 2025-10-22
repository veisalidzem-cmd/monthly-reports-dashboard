import streamlit as st

# === АУТЕНТИФИКАЦИЯ (оставлена без изменений, только вынес оформление) ===
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

# === GLOBAL CSS / STYLE (в стиле первого дашборда) ===
st.markdown(
    """
    <style>
    :root{
      --accent:#0ea5e9;
      --muted:#6b7280;
      --card-bg: #ffffff;
      --surface:#f8fafc;
      --primary:#1e3a8a;
      --success:#10b981;
      --shadow: 0 6px 18px rgba(15, 23, 42, 0.06);
    }
    /* page */
    .main { background-color: var(--surface); padding: 28px 36px !important; }

    /* header */
    .dash-title {
      display:flex;
      gap:12px;
      align-items:center;
      margin-bottom:6px;
    }
    .dash-title h1{
      font-size:28px;
      margin:0;
      color:var(--primary);
      font-weight:800;
    }
    .dash-title .subtitle{
      color:var(--muted);
      font-size:14px;
      margin-top:4px;
    }

    /* metric cards row */
    .metrics-row { display:flex; gap:18px; margin-top:18px; margin-bottom:20px; flex-wrap:wrap; }
    .metric-card {
      background: var(--card-bg);
      border-radius:12px;
      padding:18px;
      width:100%;
      box-shadow: var(--shadow);
      border: 1px solid rgba(15,23,42,0.03);
    }
    @media (min-width: 900px){
        .metric-card { width: 24%; }
    }
    .metric-label { color:var(--muted); font-size:13px; margin-bottom:6px; }
    .metric-value { font-size:26px; font-weight:800; color: #0f172a; }
    .metric-delta { font-size:12px; color:var(--success); margin-top:6px; }

    /* cards container for charts */
    .card { background:var(--card-bg); padding:18px; border-radius:12px; box-shadow: var(--shadow); border: 1px solid rgba(15,23,42,0.03); }
    .card-title { font-weight:700; color:#0f172a; margin-bottom:8px; font-size:15px; }
    .card-sub { color:var(--muted); font-size:12px; margin-bottom:12px; }

    /* table header */
    .detail-title { margin-top:18px; font-size:18px; font-weight:700; color:#0f172a; margin-bottom:10px; }

    /* small helper */
    .small-muted { color:var(--muted); font-size:12px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# === HEADER ===
st.markdown(
    """
    <div class="dash-title">
      <div style="font-size:32px; color:var(--accent);">💧</div>
      <div>
        <h1>Отчет по заявкам ЦДС водопровод</h1>
        <div class="subtitle">2025 год – РВК</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

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

# === Кнопки месяцев — аккуратно в ряд, стильные ===
st.markdown("<div class='small-muted'>Период:</div>", unsafe_allow_html=True)
month_cols = st.columns(6)
months = list(DISPLAY_NAMES.items())
for i, (key, name) in enumerate(months):
    col = month_cols[i % 6]
    if col.button(name, key=f"btn_{key}", use_container_width=True):
        st.session_state.selected = key

selected = st.session_state.get("selected", "year")

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
            if hasattr(e, "response") and getattr(e.response, "status_code", None) == 500 and attempt < 2:
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

# === Основные показатели (с карточками) ===
total = int(df["total"].sum())
closed = int(df["closed"].sum())
open_ = int(df["open"].sum())
cancelled = int(df["cancelled"].sum())

# Рендер карточек вручную через HTML для полного контроля дизайна
def render_metric_card(label: str, value: int, delta_text: str = "", accent: str = ""):
    delta_html = f'<div class="metric-delta">{delta_text}</div>' if delta_text else ""
    return f"""
    <div class="metric-card">
      <div class="metric-label">{label}</div>
      <div class="metric-value">{value}</div>
      {delta_html}
    </div>
    """

cards_html = (
    render_metric_card("Всего заявок", total, "", "blue") +
    render_metric_card("Закрытых заявок", closed, "100% выполнение" if total>0 and closed==total else "") +
    render_metric_card("Открытых заявок", open_, "Требуют внимания" if open_>0 else "") +
    render_metric_card("Отмененных заявок", cancelled, "Ошибочно или отменено" if cancelled>0 else "")
)

st.markdown(f'<div class="metrics-row">{cards_html}</div>', unsafe_allow_html=True)

# === Графики (лево: пирог, право: столбцы) в карточках ===
active = df[df["total"] > 0].copy()
if active.empty:
    st.info("Нет данных для построения графиков по выбранному периоду.")
else:
    chart_data = active[["organization", "total", "closed"]].rename(columns={
        "organization": "Организация",
        "total": "Всего",
        "closed": "Закрыто"
    })

    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        st.markdown('<div class="card"><div class="card-title">Распределение заявок по организациям</div>', unsafe_allow_html=True)
        fig1 = px.pie(
            chart_data,
            values="Всего",
            names="Организация",
            hole=0.45,
            color_discrete_sequence=px.colors.sequential.Blues
        )
        fig1.update_traces(textposition="inside", textinfo="percent+label",
                           hovertemplate="<b>%{label}</b><br>Заявок: %{value}<extra></extra>")
        fig1.update_layout(margin=dict(t=10, b=10, l=10, r=10), showlegend=True, legend=dict(orientation="h", y=-0.12, x=0.5))
        st.plotly_chart(fig1, use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    with col_right:
        st.markdown('<div class="card"><div class="card-title">Сравнение заявок по организациям</div><div class="card-sub">Всего vs Закрыто</div>', unsafe_allow_html=True)
        bar_data = chart_data.melt(id_vars="Организация", value_vars=["Всего", "Закрыто"])
        COLOR_MAP = {"Всего": "#3b82f6", "Закрыто": "#10b981"}
        fig2 = px.bar(
            bar_data,
            x="Организация",
            y="value",
            color="variable",
            barmode="group",
            color_discrete_map=COLOR_MAP,
            labels={"value": "Количество", "Организация": ""}
        )
        fig2.update_layout(margin=dict(t=6, b=80, l=10, r=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        fig2.update_traces(hovertemplate="<b>%{x}</b><br>%{y}<extra></extra>")
        fig2.update_xaxes(tickangle=-45)
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

# === Детальная таблица в минималистичном виде ===
st.markdown('<div class="detail-title">Детальная информация</div>', unsafe_allow_html=True)

display_df = df.rename(columns={
    "organization": "Организация",
    "total": "Всего",
    "closed": "Закрыто",
    "open": "Открыто",
    "cancelled": "Отменено",
    "erroneous": "Ошибочно"
})

# Отобразим таблицу с минимальными стилями Streamlit, внутри карточки
st.markdown('<div class="card">', unsafe_allow_html=True)
st.dataframe(display_df, use_container_width=True, hide_index=True)
st.markdown('</div>', unsafe_allow_html=True)

# === Подпись с последним обновлением ===
astana_tz = pytz.timezone("Asia/Almaty")
current_time = datetime.now(astana_tz).strftime('%d.%m.%Y %H:%M')
st.markdown(f'<div style="margin-top:10px;" class="small-muted">Данные обновлены: {current_time} (Астана)</div>', unsafe_allow_html=True)
