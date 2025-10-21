import streamlit as st
    st.metric("⚠️ Открытых", open_, delta="Требуют внимания" if open_ > 0 else None)
with col4:
    st.metric("❌ Отменённых", cancelled)

# Графики
if not active.empty:
    g1, g2 = st.columns(2)
    
    with g1:
        fig1 = px.pie(
            active,
            values="total",
            names="organization",
            title="Распределение по организациям",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig1.update_traces(textposition="inside", textinfo="percent+label")
        fig1.update_layout(
            title_x=0.5,
            showlegend=False,
            margin=dict(t=50, b=20, l=20, r=20)
        )
        st.plotly_chart(fig1, use_container_width=True)
    
    with g2:
        active_display = active.rename(columns={
            "closed": "Закрыто",
            "open": "Открыто",
            "cancelled": "Отменено"
        })
        fig2 = px.bar(
            active_display,
            x="org_label",
            y=["Закрыто", "Открыто", "Отменено"],
            title="Статус заявок",
            labels={"value": "Количество", "org_label": "Организация"},
            barmode="stack",
            color_discrete_map={
                "Закрыто": "#4ade80",
                "Открыто": "#fbbf24",
                "Отменено": "#f87171"
            }
        )
        fig2.update_layout(
            title_x=0.5,
            xaxis_tickangle=-45,
            margin=dict(t=50, b=100, l=40, r=20),
            legend_title_text="Статус"
        )
        st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("Нет организаций с заявками.")

# Таблица с русскими заголовками
display_df = df.rename(columns={
    "organization": "Организация",
    "total": "Всего",
    "closed": "Закрыто",
    "open": "Открыто",
    "cancelled": "Отменено",
    "erroneous": "Ошибочно"
})
st.subheader("Детальная информация")
st.dataframe(display_df, use_container_width=True)

# Время в Астане
astana_tz = pytz.timezone("Asia/Almaty")
current_time = datetime.now(astana_tz).strftime('%d.%m.%Y %H:%M')
st.caption(f"Данные обновлены: {current_time}")
