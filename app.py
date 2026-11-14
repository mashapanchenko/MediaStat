import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from io import BytesIO

st.set_page_config(page_title="MediaStat", page_icon="📊", layout="wide")

st.markdown("""
<style>
.stApp { background: #faf7f2; }
h1, h2, h3 { color: #51453d; }
div[data-testid="stMetric"] { background: #eee6dc; padding: 14px; border-radius: 12px; }
</style>
""", unsafe_allow_html=True)

REQUIRED = ["Дата", "Платформа", "Публикация", "Охват", "Лайки", "Комментарии", "Репосты", "Сохранения"]
NUMERIC = ["Охват", "Лайки", "Комментарии", "Репосты", "Сохранения"]

st.title("📊 MediaStat")
st.caption("Анализ эффективности публикаций в социальных сетях")
st.write("Загрузите Excel- или CSV-файл с метриками публикаций. Исходный файл не изменяется.")

uploaded = st.file_uploader("Выберите таблицу", type=["xlsx", "xls", "csv"])

def make_excel(data):
    summary = pd.DataFrame({
        "Показатель": ["Количество публикаций", "Суммарный охват", "Всего взаимодействий", "Средний ER, %"],
        "Значение": [len(data), int(data["Охват"].sum()), int(data["Взаимодействия"].sum()),
                     round(float(data["ER, %"].mean()), 2)]
    })
    top = data.sort_values("ER, %", ascending=False).head(10)
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="Сводка", index=False)
        data.to_excel(writer, sheet_name="Все публикации", index=False)
        top.to_excel(writer, sheet_name="Топ публикаций", index=False)
    buffer.seek(0)
    return buffer.getvalue()

if uploaded is not None:
    try:
        with st.spinner("Читаю и анализирую таблицу…"):
            if uploaded.name.lower().endswith(".csv"):
                df = pd.read_csv(uploaded)
            else:
                df = pd.read_excel(uploaded)
            df.columns = [str(c).strip() for c in df.columns]
            missing = [c for c in REQUIRED if c not in df.columns]
            if missing:
                st.error("Не найдены обязательные столбцы: " + ", ".join(missing))
                st.info("Требуемые столбцы: " + ", ".join(REQUIRED))
                st.stop()
            for col in NUMERIC:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
                if (df[col] < 0).any():
                    st.error(f"В столбце «{col}» обнаружены отрицательные значения.")
                    st.stop()
            interactions = df[["Лайки", "Комментарии", "Репосты", "Сохранения"]].sum(axis=1)
            df["Взаимодействия"] = interactions
            df["ER, %"] = (interactions / df["Охват"].replace(0, pd.NA) * 100).fillna(0).round(2)

        st.success(f"Анализ завершён! Обработано публикаций: {len(df)}")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Публикации", f"{len(df):,}")
        c2.metric("Суммарный охват", f"{int(df['Охват'].sum()):,}")
        c3.metric("Взаимодействия", f"{int(df['Взаимодействия'].sum()):,}")
        c4.metric("Средний ER", f"{df['ER, %'].mean():.2f}%")

        st.subheader("Таблица публикаций")
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.subheader("Топ-10 публикаций по ER")
        top = df.sort_values("ER, %", ascending=False).head(10)
        chart_df = top[["Публикация", "ER, %"]].set_index("Публикация")
        st.bar_chart(chart_df)

        st.subheader("Статистика по платформам")
        platform = df.groupby("Платформа", as_index=False).agg(
            Публикаций=("Публикация", "count"),
            Охват=("Охват", "sum"),
            Взаимодействия=("Взаимодействия", "sum")
        )
        platform["ER, %"] = (platform["Взаимодействия"] / platform["Охват"].replace(0, pd.NA) * 100).fillna(0).round(2)
        st.dataframe(platform, use_container_width=True, hide_index=True)

        report = make_excel(df)
        st.download_button("📥 Скачать итоговый Excel-отчёт", data=report,
                           file_name="MediaStat_отчет.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        st.error(f"Не удалось обработать файл: {e}")
else:
    st.info("Для демонстрации можно загрузить файл «Пример_таблицы_MediaStat.xlsx».")
    st.markdown("**Формат таблицы:** " + " · ".join(REQUIRED))
