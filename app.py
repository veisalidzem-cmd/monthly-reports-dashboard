import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import json
import pytz
import time

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

# === НАСТРОЙКА СТРАНИЦЫ ===
st.set_page_config(page_title="Отчет по заявкам ЦДС водопровод", layout="wide")

# === СТИЛИ ===
st.markdown("""
<style>
:root {
  --primary:#1e3a8a;
  --accent:#0284c7;
  --success:#10b981;
  --muted:#6b7280;
  --surface:#f8fafc;
  --card:#ffffff;
  --shadow:0 4px 10px rgba(0,0,0,0.05);
}
.main {
  background-color:var(--surface);
  padding:20px 30px !important;
}
h1 {
  font-size:2rem;
  font-weight:800;
  color:var(--primary);
  margin-bottom:0.3em;
}
h2 {
  font-size:1.3rem;
  font-weight:600;
  color:var(--primary);
  margin-bottom:0.4em;
  margin-top:1em;
}
.metric-container {
  display:flex;
  flex-wrap:wrap;
  gap:18px;
  margin-bottom:1.2em;
}
.metric-card {
  background:var(--card);
  flex:1;
  min-width:180px;
  padding:16px 20px;
  border-radius:12px;
  box-shadow:var(--shadow);
  border:1px solid rgba(0,0,0,0.02);
}
.metric-label {
  font-size:0.95rem;
  color:var(--muted);
  margin-bottom:4px;
}
.metric-value {
  font-size:1.8rem;
  font-weight:800;
  color:#0f172a;
}
.metric-delta {
  font-size:0.8rem;
  color:var(--success);
  margin-top:3px;
}
.section-card {
  background:var(--card);
  border-radius:12px;
  box-shadow:var(--shadow);
  padding:18px 22px;
  margin-top:10px;
  border:1px solid rgba(0,0,0,0.02);
}
.section-title {
  font-size:1rem;
  font-weight:700;
  color:#0f172a;
  margin-bottom:0.5em;
}
.dataframe {
  font-size:0.9rem;
}
.small-muted {
  color:var(--muted);
  font-size:0.8rem;
}
</style>
""", unsafe_allow_html=True)

# === ЗАГОЛОВОК ===
st.markdown("## 💧 Отчет по заявкам ЦДС водопровод")
st.markdown("### 2025 год – РВК")

# === МЕСЯЦЫ ===
SHEET_NAMES = {
    "jan": "jan","feb": "feb","mar": "mar","apr": "apr","may": "may",
    "jun": "june","jul": "jule","aug": "aug","sep": "sept","oct": "oct",
    "nov": "nov","dec": "dec","year": "gen"
}
DISPLAY_NAMES = {
    "jan": "Янв","feb": "Фев","mar": "Мар","apr": "Апр","may": "Май",
    "jun": "Июн","jul": "Июл","aug": "Авг","sep": "Сен","oct": "Окт",
    "nov": "Ноя","dec": "Дек","year": "Год"
}
st.markdown("**Период:**")
cols = st.columns(6)
for i, (key, name) in enumerate(list(DISPLAY_NAMES.items())):
    if cols[i%6].button(name, key=f"btn_{key}", use_container_width=True):
        st.session_state.selected = key
selected = st.session_state.get("selected", "jan")

# === GOOGLE SHEETS ===
@st.cache_resource
def get_client():
    try:
        info = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
        creds = Credentials.from_service_account_info(info, scopes=[
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"])
    except KeyError:
        creds = Credentials.from_service_account_file("credentials.json", scopes=[
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"])
    return gspread.authorize(creds)

def load_data(period_key: str) -> pd.DataFrame:
    client = get_client()
    sheet_name = SHEET_NAMES[period_key]
    for attempt in range(3):
        try:
            ws = client.open_by_key("1v6GS19Ib3wnl5RGpDz31KPzDJ5T1pxd6rx1aTYzy63k").worksheet(sheet_name)
            values = ws.get("A4:F13")
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
    cleaned = [r for r in values if r and str(r[0]).strip()]
    normalized = [r + [""]*(len(columns)-len(r)) for r in cleaned]
    return pd.DataFrame(normalized, columns=columns)

# === ЗАГРУЗКА ===
try:
    df = load_data(selected)
except Exception as e:
    st.error(f"Ошибка загрузки листа '{SHEET_NAMES[selected]}': {e}")
    st.stop()

for col in ["total","closed","open","cancelled","erroneous"]:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

# === МЕТРИКИ ===
total, closed, open_, cancelled = df["total"].sum(), df["closed"].sum(), df["open"].sum(), df["cancelled"].sum()
delta_closed = "100% выполнение" if total and closed == total else ""
delta_open = "Требуют внимания" if open_ > 0 else ""
delta_cancel = "Ошибочно или отменено" if cancelled > 0 else ""

st.markdown("<div class='metric-container'>", unsafe_allow_html=True)
for label, val, delta in [
    ("Всего заявок", total, ""),
    ("Закрытых заявок", closed, delta_closed),
    ("Открытых заявок", open_, delta_open),
    ("Отмененных заявок", cancelled, delta_cancel),
]:
    st.markdown(f"""
    <div class='metric-card'>
      <div class='metric-label'>{label}</div>
      <div class='metric-value'>{val}</div>
      <div class='metric-delta'>{delta}</div>
    </div>
    """, unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# === ГРАФИКИ ===
active = df[df["total"] > 0].copy()
if not active.empty:
    chart_data = active[["organization","total","closed"]].rename(
        columns={"organization":"Организация","total":"Всего","closed":"Закрыто"})

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<div class='section-card'><div class='section-title'>Распределение по организациям</div>", unsafe_allow_html=True)
        fig1 = px.pie(chart_data, values="Всего", names="Организация",
                      hole=0.45, color_discrete_sequence=px.colors.sequential.Blues)
        fig1.update_traces(textposition="inside", textinfo="percent+label", hovertemplate="<b>%{label}</b><br>Заявок: %{value}<extra></extra>")
        fig1.update_layout(showlegend=True, legend=dict(orientation="h", y=-0.15, x=0.5), margin=dict(t=10,b=10,l=10,r=10))
        st.plotly_chart(fig1, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown("<div class='section-card'><div class='section-title'>Всего vs Закрыто</div>", unsafe_allow_html=True)
        bar_data = chart_data.melt(id_vars="Организация", value_vars=["Всего","Закрыто"])
        fig2 = px.bar(bar_data, x="Организация", y="value", color="variable",
                      barmode="group", color_discrete_map={"Всего":"#3b82f6","Закрыто":"#10b981"})
        fig2.update_layout(legend=dict(orientation="h", y=1.05, x=1), margin=dict(t=10,b=60,l=10,r=10))
        fig2.update_xaxes(tickangle=-45)
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

# === ТАБЛИЦА ===
st.markdown("<div class='section-card'><div class='section-title'>Детальная информация</div>", unsafe_allow_html=True)
display_df = df.rename(columns={
    "organization":"Организация","total":"Всего","closed":"Закрыто",
    "open":"Открыто","cancelled":"Отменено","erroneous":"Ошибочно"})
st.dataframe(display_df, use_container_width=True, hide_index=True)
st.markdown("</div>", unsafe_allow_html=True)

# === ОБНОВЛЕНИЕ ===
astana_tz = pytz.timezone("Asia/Almaty")
current_time = datetime.now(astana_tz).strftime('%d.%m.%Y %H:%M')
st.markdown(f"<div class='small-muted'>Данные обновлены: {current_time} (Астана)</div>", unsafe_allow_html=True)
