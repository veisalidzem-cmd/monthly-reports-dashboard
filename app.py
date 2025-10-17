import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

GOOGLE_SHEET_ID = "1v6GS19Ib3wnl5RGpDz31KPzDJ5T1pxd6rx1aTYzy63k"
SHEETS = ["jan", "feb", "mar", "apr", "may", "june", "jule", "aug", "sept", "oct", "nov", "dec", "gen"]

@st.cache_data(ttl=300)
def load_sheet(sheet_name):
    url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    try:
        # Читаем без заголовков — все строки как есть
        df = pd.read_csv(url, header=None)
        return df
    except Exception as e:
        st.error(f"Ошибка загрузки листа '{sheet_name}': {e}")
        return pd.DataFrame()

def safe_int(val):
    try:
        if pd.isna(val) or val == "" or str(val).strip() == "":
            return 0
        return int(float(str(val).replace(" ", "").replace(",", ".")))
    except (ValueError, TypeError):
        return 0

# === СТИЛЬ КАК НА LOVABLE ===
st.markdown("""
<style>
    .block-container {
        max-width: 1200px;
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    h1 {
        font-size: 2.2rem;
        font-weight: 700;
        color: #3B82F6;
        margin-bottom: 0.5rem;
    }
    .period {
        font-size: 1rem;
        color: #6B7280;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        height: 100%;
    }
    .metric-title {
        font-size: 0.85rem;
        color: #6B7280;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 600;
        color: #111827;
        margin: 0.5rem 0;
    }
    .metric-subtitle {
        font-size: 0.75rem;
        color: #3B82F6;
    }
</style>
""", unsafe_allow_html=True)

# Убираем общий заголовок — он будет внутри табов
tabs = st.tabs([
    "Янв", "Фев", "Мар", "Апр", "Май", "Июн",
    "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек", "Год"
])

for i, tab in enumerate(tabs):
    with tab:
        sheet_name = SHEETS[i]
        df = load_sheet(sheet_name)

        if df.empty:
            st.info("Нет данных.")
            continue

        # Проверяем, достаточно ли строк
        if len(df) < 14:
            st.warning("Лист содержит меньше 14 строк. Данные не могут быть прочитаны.")
            continue

        # === ОПРЕДЕЛЕНИЕ ПЕРИОДА ===
        period_text = "Период не указан"
        first_row = df.iloc[0].astype(str).str.strip()
        for cell in first_row:
            if "01." in cell and "-" in cell and len(cell) > 10:
                period_text = f"Период {cell}"
                break

        st.markdown(f'<div class="period">{period_text}</div>', unsafe_allow_html=True)

        # === ИЗВЛЕЧЕНИЕ МЕТРИК ИЗ СТРОКИ 14 (индекс 13) ===
        total_row = df.iloc[13]  # Строка 14 (индекс 13)

        total = safe_int(total_row[1])  # B14 — Всего
        closed = safe_int(total_row[2])  # C14 — Закрытых
        open_ = safe_int(total_row[3])  # D14 — Открытых
        canceled = safe_int(total_row[4])  # E14 — Отмененных
        erroneous = safe_int(total_row[5])  # F14 — Ошибочных

        # === КАРТОЧКИ ===
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Всего заявок</div>
                <div class="metric-value">{total}</div>
                <div class="metric-subtitle">За отчетный период</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Закрытых заявок</div>
                <div class="metric-value">{closed}</div>
                <div class="metric-subtitle">100% выполнение</div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Открытых заявок</div>
                <div class="metric-value">{open_}</div>
                <div class="metric-subtitle">Требуют внимания</div>
            </div>
            """, unsafe_allow_html=True)
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Отмененных заявок</div>
                <div class="metric-value">{canceled}</div>
                <div class="metric-subtitle">Отменено или ошибочно</div>
            </div>
            """, unsafe_allow_html=True)

        # === ПОДГОТОВКА ДАННЫХ ДЛЯ ГРАФИКОВ ===
        # Данные по организациям: строки 4-13 (индексы 3-12), колонки 0-5
        data_rows = df.iloc[3:13, :6]  # A4:F13

        # Переименовываем колонки для удобства
        data_rows.columns = ["РВК", "Всего", "Кол.закрытых ГИС", "Кол.Открытых ГИС", "Кол.отмененных ГИС", "Кол.ошибочных ГИС"]

        # Убираем строки, где РВК пустой
        data_for_charts = data_rows.dropna(subset=["РВК"])
        data_for_charts = data_for_charts[data_for_charts["РВК"].astype(str).str.strip() != ""]

        if data_for_charts.empty:
            st.info("Нет данных по организациям для визуализации.")
            continue

        # --- Пирог ---
        pie_data = data_for_charts[["РВК", "Всего"]].copy()
        pie_data["Всего"] = pd.to_numeric(pie_data["Всего"], errors="coerce").fillna(0)
        pie_data = pie_data[pie_data["Всего"] > 0]

        if not pie_data.empty:
            st.subheader("Распределение заявок по организациям")
            fig_pie = px.pie(pie_data, names="РВК", values="Всего", hole=0.4)
            fig_pie.update_traces(textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)

        # --- Столбчатая диаграмма ---
        bar_data = data_for_charts[["РВК", "Всего", "Кол.закрытых ГИС"]].copy()
        bar_data["Всего"] = pd.to_numeric(bar_data["Всего"], errors="coerce").fillna(0)
        bar_data["Кол.закрытых ГИС"] = pd.to_numeric(bar_data["Кол.закрытых ГИС"], errors="coerce").fillna(0)
        bar_data = bar_data[(bar_data["Всего"] > 0) | (bar_data["Кол.закрытых ГИС"] > 0)]

        if not bar_data.empty:
            st.subheader("Сравнение заявок по организациям")
            fig_bar = go.Figure()
            fig_bar.add_trace(go.Bar(x=bar_data["РВК"], y=bar_data["Всего"], name="Всего заявок", marker_color="#2563EB"))
            fig_bar.add_trace(go.Bar(x=bar_data["РВК"], y=bar_data["Кол.закрытых ГИС"], name="Закрытых", marker_color="#93C5FD"))
            fig_bar.update_layout(barmode='group', xaxis_tickangle=-45, plot_bgcolor="white", paper_bgcolor="white")
            st.plotly_chart(fig_bar, use_container_width=True)
