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
        df = pd.read_csv(url)
        # Убираем лишние пробелы в названиях колонок
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Ошибка загрузки листа '{sheet_name}': {e}")
        return pd.DataFrame()

# === СТИЛЬ КАК НА СКРИНШОТЕ ===
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
        display: flex;
        justify-content: space-between;
        align-items: center;
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

# === ЗАГОЛОВОК ===
st.title("Отчет по заявкам ЦДС водопровод")

# === ТАБЫ МЕСЯЦЕВ ===
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

        # Определяем период (если есть строка с датами)
        period_row = df[df.iloc[:, 0].astype(str).str.contains("01.", na=False)]
        if not period_row.empty:
            period_text = period_row.iloc[0, 0]  # Берём первую ячейку строки
            st.markdown(f'<div class="period">{period_text}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="period">Период не указан</div>', unsafe_allow_html=True)

        # Ищем строку с "сумма" (или последнюю строку с числами)
        # Предполагаем, что суммы находятся в последней строке
        total_row = df.iloc[-1].copy()  # Последняя строка

        # Извлекаем метрики
        total = total_row.get("Всего", 0)
        closed = total_row.get("Кол.закрытых ГИС", 0)
        open_ = total_row.get("Кол.Открытых ГИС", 0)
        canceled = total_row.get("Кол.отмененных ГИС", 0)

        # === ЧЕТЫРЕ КАРТОЧКИ ===
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Всего заявок</div>
                <div class="metric-value">{int(total)}</div>
                <div class="metric-subtitle">За отчетный период</div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Закрытых заявок</div>
                <div class="metric-value">{int(closed)}</div>
                <div class="metric-subtitle">100% выполнение</div>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Открытых заявок</div>
                <div class="metric-value">{int(open_)}</div>
                <div class="metric-subtitle">Требуют внимания</div>
            </div>
            """, unsafe_allow_html=True)

        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Отмененных заявок</div>
                <div class="metric-value">{int(canceled)}</div>
                <div class="metric-subtitle">Отменено или ошибочно</div>
            </div>
            """, unsafe_allow_html=True)

        # === ГРАФИКИ ===
        # Убираем последнюю строку (сумму) и пустые строки
        data_for_charts = df.iloc[:-1].dropna(subset=["РВК"]).copy()

        if "РВК" in data_for_charts.columns and "Всего" in data_for_charts.columns:
            # Пирог: Распределение по организациям
            st.subheader("Распределение заявок по организациям")
            pie_data = data_for_charts[["РВК", "Всего"]].copy()
            pie_data = pie_data[pie_data["Всего"] > 0]  # Только с ненулевыми значениями
            if not pie_data.empty:
                fig_pie = px.pie(pie_data, names="РВК", values="Всего", hole=0.4)
                fig_pie.update_traces(textinfo='percent+label')
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("Нет данных для построения пирога.")

            # Столбчатая диаграмма: Сравнение по организациям
            st.subheader("Сравнение заявок по организациям")
            bar_data = data_for_charts[["РВК", "Всего", "Кол.закрытых ГИС"]].copy()
            bar_data = bar_data[bar_data["Всего"] > 0]  # Только с ненулевыми значениями
            if not bar_data.empty:
                fig_bar = go.Figure()
                fig_bar.add_trace(go.Bar(x=bar_data["РВК"], y=bar_data["Всего"], name="Всего заявок", marker_color="#2563EB"))
                fig_bar.add_trace(go.Bar(x=bar_data["РВК"], y=bar_data["Кол.закрытых ГИС"], name="Закрытых", marker_color="#93C5FD"))
                fig_bar.update_layout(barmode='group', showlegend=True, xaxis_tickangle=-45)
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("Нет данных для построения столбчатой диаграммы.")
