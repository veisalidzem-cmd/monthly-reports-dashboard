import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import json

# === Конфигурация ===
SHEET_ID = "1v6GS19Ib3wnl5RGpDz31KPzDJ5T1pxd6rx1aTYzy63k"

# Сопоставление: ключ выбора → имя листа в Google Sheets
SHEET_NAMES = {
    "jan": "jan",
    "feb": "feb",
    "mar": "mar",
    "apr": "apr",
    "may": "may",
    "jun": "jun",
    "jul": "jul",
    "aug": "aug",
    "sep": "sep",
    "oct": "oct",
    "nov": "nov",
    "dec": "dec",
    "year": "gen",  # ← годовой отчёт на листе "gen"
}

# Отображаемые названия месяцев
DISPLAY_NAMES = {
    "jan": "Янв", "feb": "Фев", "mar": "Мар", "apr": "Апр", "may": "Май",
    "jun": "Июн", "jul": "Июл", "aug": "Авг", "sep": "Сен", "oct": "Окт",
    "nov": "Ноя", "dec": "Дек", "year": "Год"
}

# === Подключение к Google Sheets ===
@st.cache_resource
def get_client():
    try:
        # Для Streamlit Cloud
        info = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
        creds = Credentials.from_service_account_info(
            info,
            scopes=[
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive"
            ]
        )
    except KeyError:
        # Для локального запуска (credentials.json в корне)
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
    sheet = client.open_by_key(SHEET_ID).worksheet(sheet_name)
    records = sheet.get_all_records()
    return pd.DataFrame(records)

# === UI ===
st.set_page_config(page_title="Отчет по заявкам ЦДС водопровод", layout="wide")
st.title("Отчет по заявкам ЦДС водопровод")
st.subheader("2025 год - РВК")

# Выбор периода
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
    st.error(f"Не удалось загрузить данные из листа '{SHEET_NAMES[selected]}': {str(e)}")
    st.stop()

# Проверка структуры
required = ["organization", "total", "closed", "open", "cancelled"]
if not all(col in df.columns for col in required):
    st.error(f"Таблица должна содержать колонки: {', '.join(required)}")
    st.stop()

# Приведение к числу
for col in required[1:]:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

# Статистика
total = df["total"].sum()
closed = df["closed"].sum()
open_ = df["open"].sum()
cancelled = df["cancelled"].sum()

# Карточки
col1, col2, col3, col4 = st.columns(4)
col1.metric("Всего заявок", total)
col2.metric("Закрытых", closed, delta="100%" if total == closed and total > 0 else None)
col3.metric("Открытых", open_, delta="Требуют внимания" if open_ > 0 else None)
col4.metric("Отменённых", cancelled)

# Фильтр активных
active = df[df["total"] > 0].copy()

# Графики
if not active.empty:
    g1, g2 = st.columns(2)

    # Круговая диаграмма
    with g1:
        fig1 = px.pie(
            active,
            values="total",
            names="organization",
            title="Распределение по организациям"
        )
        fig1.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig1, use_container_width=True)

    # Столбчатая диаграмма
    with g2:
        active["org_label"] = active["organization"].apply(
            lambda x: x[:15] + "..." if len(x) > 15 else x
        )
        fig2 = px.bar(
            active,
            x="org_label",
            y=["closed", "open", "cancelled"],
            title="Статус заявок",
            labels={"value": "Кол-во", "org_label": "Организация"},
            barmode="stack"
        )
        st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("Нет данных для отображения.")

# Таблица
st.subheader("Детальная информация")
st.dataframe(df, use_container_width=True)

st.caption(f"Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
