import streamlit as st
import pandas as pd
import plotly.express as px

# === НАСТРОЙКИ ===
GOOGLE_SHEET_ID = "1v6GS19Ib3wnl5RGpDz31KPzDJ5T1pxd6rx1aTYzy63k"

# Названия листов — точно как в твоей таблице
SHEETS = [
    "jan", "feb", "mar", "apr", "may", "june", "jule", 
    "aug", "sept", "oct", "nov", "dec", "gen"
]

@st.cache_data(ttl=300)  # обновление каждые 5 минут
def load_sheet(sheet_name):
    url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    try:
        return pd.read_csv(url)
    except Exception as e:
        st.error(f"Не удалось загрузить лист '{sheet_name}'. Убедитесь, что он существует и таблица открыта для просмотра.")
        return pd.DataFrame()

# === ИНТЕРФЕЙС ===
st.set_page_config(page_title="📊 Месячные отчёты", layout="wide")
st.title("📊 Визуализация данных по месяцам и году")

# Красивое форматирование названий
def format_label(name):
    if name == "gen":
        return "📈 Годовой отчёт"
    months = {
        "jan": "Январь", "feb": "Февраль", "mar": "Март", "apr": "Апрель",
        "may": "Май", "june": "Июнь", "jule": "Июль", "aug": "Август",
        "sept": "Сентябрь", "oct": "Октябрь", "nov": "Ноябрь", "dec": "Декабрь"
    }
    return months.get(name, name.capitalize())

selected_sheet = st.selectbox(
    "Выберите период",
    options=SHEETS,
    format_func=format_label
)

df = load_sheet(selected_sheet)

if df.empty:
    st.info("Данные отсутствуют или лист пуст.")
else:
    period_name = "Годовой отчёт" if selected_sheet == "gen" else format_label(selected_sheet)
    st.subheader(f"Данные за {period_name}")
    st.dataframe(df, use_container_width=True)

    # Автоматическое построение графика, если есть числовые данные
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    if numeric_cols:
        st.subheader("Визуализация")
        x_options = df.columns.tolist()
        y_options = numeric_cols

        col1, col2 = st.columns(2)
        with col1:
            x_col = st.selectbox("Категория (ось X)", x_options, index=0)
        with col2:
            y_col = st.selectbox("Значение (ось Y)", y_options, index=0)

        if x_col and y_col:
            fig = px.bar(
                df,
                x=x_col,
                y=y_col,
                color_discrete_sequence=["#4A90E2"],
                title=f"{y_col} по {x_col}"
            )
            fig.update_layout(
                xaxis_title=x_col,
                yaxis_title=y_col,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig, use_container_width=True)
