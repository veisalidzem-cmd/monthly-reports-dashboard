import streamlit as st
import pandas as pd
import plotly.express as px

GOOGLE_SHEET_ID = "1v6GS19Ib3wnl5RGpDz31KPzDJ5T1pxd6rx1aTYzy63k"

SHEETS = [
    "jan", "feb", "mar", "apr", "may", "june", "jule", 
    "aug", "sept", "oct", "nov", "dec", "gen"
]

@st.cache_data(ttl=300)
def load_sheet(sheet_name):
    url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    try:
        return pd.read_csv(url)
    except Exception as e:
        st.error(f"Не удалось загрузить лист '{sheet_name}'.")
        return pd.DataFrame()

# === СТИЛЬ В ДУХЕ LOVABLE ===
st.markdown("""
<style>
    .block-container {
        max-width: 1200px;
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    h1 {
        font-weight: 700;
        font-size: 2.1rem;
        margin-bottom: 2rem;
        color: #1e293b;
    }
    h2 {
        font-size: 1.4rem;
        font-weight: 600;
        margin-top: 2rem;
        margin-bottom: 1rem;
        color: #334155;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.7rem !important;
        font-weight: 600;
    }
    [data-testid="stMetricLabel"] {
        font-size: 1rem !important;
        color: #64748b;
    }
    .plotly-graph-div {
        background: white;
        border-radius: 12px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.03);
        padding: 8px;
    }
</style>
""", unsafe_allow_html=True)

st.title("Профессиональная визуализация данных")

def format_label(name):
    if name == "gen":
        return "📈 Годовой отчёт"
    months = {"jan": "Январь", "feb": "Февраль", "mar": "Март", "apr": "Апрель",
              "may": "Май", "june": "Июнь", "jule": "Июль", "aug": "Август",
              "sept": "Сентябрь", "oct": "Октябрь", "nov": "Ноябрь", "dec": "Декабрь"}
    return months.get(name, name.capitalize())

selected_sheet = st.selectbox("Выберите период", SHEETS, format_func=format_label)
df = load_sheet(selected_sheet)

if df.empty:
    st.info("Данные отсутствуют или лист пуст.")
else:
    period_name = "Годовой отчёт" if selected_sheet == "gen" else format_label(selected_sheet)
    st.subheader(f"Данные за {period_name}")
    st.dataframe(df, use_container_width=True)

    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    if numeric_cols:
        st.subheader("Визуализация")
        x_col = st.selectbox("Ось X", df.columns, index=0)
        y_col = st.selectbox("Ось Y", numeric_cols, index=0)

        fig = px.bar(
            df,
            x=x_col,
            y=y_col,
            color_discrete_sequence=["#4F46E5"],
            text_auto=True
        )
        fig.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            xaxis_title="",
            yaxis_title="",
            showlegend=False,
            margin=dict(t=30, b=40)
        )
        st.plotly_chart(fig, use_container_width=True)
