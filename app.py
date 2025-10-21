import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import json
import pytz

# ⬇️ Первая команда Streamlit
st.set_page_config(page_title="Отчет по заявкам ЦДС водопровод", layout="wide")

# === Скрываем панель инструментов Plotly и делаем графики статичными ===
st.markdown("""
<style>
    .plotly-graph-div .modebar {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

# === Автоматическая тема по ширине экрана ===
st.markdown("""
<script>
    const isMobile = window.innerWidth < 768;
    const savedTheme = localStorage.getItem('theme');
    const defaultTheme = savedTheme || (isMobile ? 'dark' : 'light');
    
    if (defaultTheme === 'dark') {
        document.documentElement.style.setProperty('--bg-color', '#0f172a');
        document.documentElement.style.setProperty('--text-color', '#f1f5f9');
        document.documentElement.style.setProperty('--metric-label', '#cbd5e1');
        document.documentElement.style.setProperty('--metric-value', '#f1f5f9');
        document.documentElement.style.setProperty('--table-header', '#1e293b');
        document.documentElement.style.setProperty('--table-cell', '#1e293b');
        document.documentElement.style.setProperty('--table-text', '#e2e8f0');
        document.documentElement.style.setProperty('--shadow', '0 4px 12px rgba(0,0,0,0.4)');
        document.documentElement.style.setProperty('--hover-shadow', '0 6px 16px rgba(0,0,0,0.5)');
    } else {
        document.documentElement.style.setProperty('--bg-color', '#ffffff');
        document.documentElement.style.setProperty('--text-color', '#1e293b');
        document.documentElement.style.setProperty('--metric-label', '#475569');
        document.documentElement.style.setProperty('--metric-value', '#1e293b');
        document.documentElement.style.setProperty('--table-header', '#e2e8f0');
        document.documentElement.style.setProperty('--table-cell', 'white');
        document.documentElement.style.setProperty('--table-text', '#334155');
        document.documentElement.style.setProperty('--shadow', '0 4px 12px rgba(0,0,0,0.08)');
        document.documentElement.style.setProperty('--hover-shadow', '0 6px 16px rgba(0,0,0,0.12)');
    }

    window.toggleTheme = () => {
        const current = localStorage.getItem('theme') || (isMobile ? 'dark' : 'light');
        const newTheme = current === 'dark' ? 'light' : 'dark';
        localStorage.setItem('theme', newTheme);
        location.reload();
    };
</script>

<style>
    :root {
        --bg-color: #ffffff;
        --text-color: #1e293b;
        --metric-label: #475569;
        --metric-value: #1e293b;
        --table-header: #e2e8f0;
        --table-cell: white;
        --table-text: #334155;
        --shadow: 0 4px 12px rgba(0,0,0,0.08);
        --hover-shadow: 0 6px 16px rgba(0,0,0,0.12);
    }

    .main { background-color: var(--bg-color); color: var(--text-color); padding: 10px !important; }
    .stApp { background-color: var(--bg-color); }

    h1, h2, h3 { color: var(--text-color) !important; }

    [data-testid="stMetricLabel"] { color: var(--metric-label) !important; }
    [data-testid="stMetricValue"] { color: var(--metric-value) !important; }

    .dataframe th { background-color: var(--table-header) !important; color: var(--text-color) !important; }
    .dataframe td { background-color: var(--table-cell) !important; color: var(--table-text) !important; }

    .plotly-graph-div {
        box-shadow: var(--shadow) !important;
        border-radius: 8px !important;
    }
    .plotly-graph-div:hover {
        box-shadow: var(--hover-shadow) !important;
    }

    #theme-toggle {
        position: fixed;
        top: 10px;
        right: 10px;
        z-index: 100;
        background: var(--table-cell);
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 0.85rem;
        cursor: pointer;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    #theme-toggle:hover {
        background: #f1f5f9;
    }

    @media print {
        #theme-toggle { display: none !important; }
        body {
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
        }
        .main {
            padding: 0 !important;
            font-size: 0.9rem !important;
        }
        h1 { font-size: 1.4rem !important; }
        h2 { font-size: 1.2rem !important; }
        [data-testid="stMetricValue"] { font-size: 1.2rem !important; }
        .dataframe {
            font-size: 0.85rem !important;
            margin-bottom: 10px !important;
        }
        .dataframe th, .dataframe td {
            padding: 6px 8px !important;
        }
        .plotly-graph-div {
            margin-bottom: 10px !important;
        }
        @page {
            size: A4 portrait;
            margin: 1cm;
        }
        * {
            zoom: 0.85 !important;
        }
    }
</style>

<button id="theme-toggle" onclick="toggleTheme()">🌓 Тема</button>
""", unsafe_allow_html=True)

# === Заголовок ===
st.title("💧 Отчет по заявкам ЦДС водопровод")
st.subheader("2025 год – РВК")

# === Конфигурация листов ===
SHEET_NAMES = {
    "jan": "jan",
    "feb": "feb",
    "mar": "mar",
    "apr": "apr",
    "may": "may",
    "jun": "june",    # исправлено
    "jul": "jule",    # исправлено
    "aug": "aug",
    "sep": "sept",    # исправлено
    "oct": "oct",
    "nov": "nov",
    "dec": "dec",
    "year": "gen"
}

DISPLAY_NAMES = {
    "jan": "Янв", "feb": "Фев", "mar": "Мар", "apr": "Апр", "may": "Май",
    "jun": "Июн", "jul": "Июл", "aug": "Авг", "sep": "Сен", "oct": "Окт",
    "nov": "Ноя", "dec": "Дек", "year": "Год"
}

# === Кнопки месяцев (адаптивные) ===
st.markdown("#### Период:")
months = list(DISPLAY_NAMES.items())
for i in range(0, len(months), 4):
    row = months[i:i+4]
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

def load_data(period_key):
    client = get_client()
    sheet_name = SHEET_NAMES[period_key]
    worksheet = client.open_by_key("1v6GS19Ib3wnl5RGpDz31KPzDJ5T1pxd6rx1aTYzy63k").worksheet(sheet_name)
    try:
        values = worksheet.get("A4:F13")
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

# === Загрузка данных ===
try:
    df = load_data(selected)
except Exception as e:
    st.error(f"Ошибка загрузки листа '{SHEET_NAMES[selected]}': {e}")
    st.stop()

# === Преобразование чисел ===
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

# === Графики (статичные, без интерактивности) ===
active = df[df["total"] > 0].copy()
if not active.empty:
    active["org_label"] = active["organization"].apply(lambda x: x[:12] + "..." if len(x) > 12 else x)
    
    g1, g2 = st.columns(2)
    with g1:
        fig1 = px.pie(
            active,
            values="total",
            names="organization",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig1.update_traces(hovertemplate="<b>%{label}</b><br>Заявок: %{value}<extra></extra>")
        fig1.update_layout(
            title="По организациям",
            title_x=0.5,
            showlegend=False,
            margin=dict(t=40, b=10, l=10, r=10),
            font_size=11
        )
        st.plotly_chart(fig1, use_container_width=True, config={
            "staticPlot": True,
            "displayModeBar": False,
            "scrollZoom": False,
            "displaylogo": False
        })
    
    with g2:
        active_disp = active.rename(columns={
            "closed": "Закрыто",
            "open": "Открыто",
            "cancelled": "Отменено"
        })
        fig2 = px.bar(
            active_disp,
            x="org_label",
            y=["Закрыто", "Открыто", "Отменено"],
            barmode="stack",
            color_discrete_map={
                "Закрыто": "#0d9488",
                "Открыто": "#f59e0b",
                "Отменено": "#ef4444"
            }
        )
        fig2.update_layout(
            title="Статус заявок",
            title_x=0.5,
            xaxis_tickangle=-45,
            margin=dict(t=40, b=80, l=30, r=10),
            font_size=10,
            showlegend=False
        )
        fig2.update_traces(hovertemplate="<b>%{x}</b><br>%{series}: %{y}<extra></extra>")
        st.plotly_chart(fig2, use_container_width=True, config={
            "staticPlot": True,
            "displayModeBar": False,
            "scrollZoom": False,
            "displaylogo": False
        })

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
