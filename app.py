import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import json

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
        # Streamlit Cloud
        info = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
        creds = Credentials.from_service_account_info(
            info,
            scopes=[
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive"
            ]
        )
    except KeyError:
        # Локально
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
    
    all_values = worksheet.get_all_values()
    
    # Если нет данных или только шапка — возвращаем пустой DF
    if len(all_values) <= 1:
        return pd.DataFrame(columns=["organization", "total", "closed", "open", "cancelled", "erroneous"])
    
    # Пропускаем первую строку (шапку), берём всё остальное
    data_rows = all_values[1:]
    
    # Жёстко заданные колонки — порядок должен совпадать с таблицей
    columns = ["organization", "total", "closed", "open", "cancelled", "erroneous"]
    
    # Нормализуем строки до нужной длины
    normalized_rows = []
    for row in data_rows:
        # Дополняем пустыми значениями, если не хватает колонок
        while len(row) < len(columns):
            row.append("")
        # Обрезаем лишнее
        normalized_rows.append(row[:len(columns)])
    
    df = pd.DataFrame(normalized_rows, columns=columns)
    return df

# === Streamlit UI ===
st.set_page_config(page_title="Отчет по заявкам ЦДС водопровод", layout="wide")
st.title("Отчет по заявкам ЦДС водопровод")
st.subheader("2025 год - РВК")

selected = st.selectbox(
    "Выберите период",
    options=list(DISPLAY_NAMES.keys()),
    format_func=lambda x: DISPLAY_NAMES[x],
    index=0
)

# Загрузка и обработка данных
try:
    df = load_data(selected)
except Exception as e:
    st.error(f"Ошибка при загрузке листа '{SHEET_NAMES[selected]}': {e}")
    st.stop()

# Преобразуем числовые поля
numeric_cols = ["total", "closed", "open", "cancelled", "erroneous"]
for col in numeric_cols:
    if col in df.columns:
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

# Активные организации
active = df[df["total"] > 0].copy()

# Графики
if not active.empty:
    g1, g2 = st.columns(2)
    
    with g1:
        fig1 = px.pie(
            active,
            values="total",
            names="organization",
            title="Распределение по организациям"
        )
        fig1.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig1, use_container_width=True)
    
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
    st.info("Нет организаций с заявками.")

# Таблица
st.subheader("Детальная информация")
st.dataframe(df, use_container_width=True)

st.caption(f"Данные обновлены: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
