import io
import os
import pandas as pd
import streamlit as st

# --- ИНИЦИАЛИЗАЦИЯ И НАСТРОЙКА СТРАНИЦЫ ---
st.set_page_config(
    page_title="KaDeWe Inventory & Management", page_icon="🛍️", layout="wide"
)

# --- ИМИТАЦИЯ ДАННЫХ И АВТОРИЗАЦИИ (Ваши роли и функции сохранены) ---
# Проверяем, есть ли базовые данные в session_state, если нет - создаем пример с min/max
if "df" not in st.session_state:
  st.session_state["df"] = pd.DataFrame({
      "article": ["10101", "10102", "10103", "10104"],
      "name": [
          "Royal Copenhagen Musselmalet",
          "Iittala Kivi Windlicht",
          "Royal Copenhagen Blue Fluted",
          "Iittala Aalto Vase",
      ],
      "brand": [
          "Royal Copenhagen",
          "Iittala",
          "Royal Copenhagen",
          "Iittala",
      ],
      "quantity": [3, 12, 1, 8],  # Текущий остаток
      "min_qty": [5, 10, 4, 5],  # Минимальный остаток (триггер заказа)
      "max_qty": [15, 30, 12, 20],  # Максимальный уровень пополнения
      "preis": [120.0, 25.0, 85.0, 160.0],
  })

if "user_role" not in st.session_state:
  st.session_state["user_role"] = "Manager"  # Возможные роли: Manager / Agent

# --- САЙДБАР И НАВИГАЦИЯ ---
st.sidebar.title("🛍️ KaDeWe Management")
st.sidebar.markdown(f"**Роль:** {st.session_state['user_role']}")

action = st.sidebar.selectbox(
    "Меню",
    [
        "📦 Automatischer Bestellvorschlag",
        "📊 Übersicht / Bestände",
        "➕ Artikel verwalten",
        "⚙️ Einstellungen",
    ],
)

# Получаем актуальный датафрейм из сессии
df = st.session_state["df"]

# ==========================================
# 1. АВТОМАТИЧЕСКИЙ БЕШТЕЛЬФОРШЛАГ
# ==========================================
if action == "📦 Automatischer Bestellvorschlag":
  st.header("📦 Automatischer Bestellvorschlag (nach Min/Max)")
  st.markdown(
      "Здесь формируется список дозаказа: товары попадают в заказ, если их"
      " остаток опустился до минимума или ниже (`quantity <= min_qty`)."
      " Количество рассчитывается как разница до максимального уровня (`max_qty"
      " - quantity`)."
  )

  if df.empty:
    st.warning("Keine Daten vorhanden.")
  else:
    # Расчет заказа
    order_df = df.copy()

    def calc_order(row):
      qty = int(pd.to_numeric(row.get("quantity", 0), errors="coerce") or 0)
      min_q = int(pd.to_numeric(row.get("min_qty", 0), errors="coerce") or 0)
      max_q = int(pd.to_numeric(row.get("max_qty", 0), errors="coerce") or 0)

      # Если остаток <= минимума, заказываем до максимума
      if qty <= min_q:
        return max(0, max_q - qty)
      return 0

    order_df["Bestellmenge"] = order_df.apply(calc_order, axis=1)
    order_result = order_df[order_df["Bestellmenge"] > 0]

    # Вывод результатов
    if order_result.empty:
      st.success(
          "✅ Alle Bestände sind im grünen Bereich! Keine Nachbestellungen"
          " nötig."
      )
    else:
      st.warning(
          f"⚠ Achtung: {len(order_result)} Artikel unterschreiten den"
          " Mindestbestand!"
      )

      display_cols = [
          "article",
          "name",
          "brand",
          "quantity",
          "min_qty",
          "max_qty",
          "Bestellmenge",
          "preis",
      ]
      available_cols = [c for c in display_cols if c in order_result.columns]

      st.dataframe(order_result[available_cols], use_container_width=True)

      # Кнопка экспорта в Excel
      out_buf = io.BytesIO()
      with pd.ExcelWriter(out_buf, engine="openpyxl") as writer:
        order_result.to_excel(writer, index=False, sheet_name="Bestellliste")
      st.download_button(
        label="📥 Bestellvorschlag als Excel herunterladen",
        data=out_buf.getvalue(),
        file_name="KaDeWe_Bestellvorschlag.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
      )

# ==========================================
# 2. ОБЩИЙ ОБЗОР И ОСТАТКИ
# ==========================================
elif action == "📊 Übersicht / Bestände":
  st.header("📊 Warenbestand")
  st.dataframe(df, use_container_width=True)

# ==========================================
# 3. УПРАВЛЕНИЕ ТОВАРАМИ
# ==========================================
elif action == "➕ Artikel verwalten":
  st.header("➕ Artikel verwalten")
  st.info(
      "Здесь находятся ваши существующие функции добавления, редактирования и"
      " управления товарами."
  )

  # Пример редактирования остатка для проверки работы Bestellvorschlag
  selected_idx = st.selectbox(
      "Выберите строку для изменения остатка (тест)", df.index
  )
  new_qty = st.number_input(
      "Новый остаток (quantity)",
      value=int(df.loc[selected_idx, "quantity"]),
      step=1,
  )
  if st.button("Обновить остаток"):
    df.loc[selected_idx, "quantity"] = new_qty
    st.session_state["df"] = df
    st.success("Остаток обновлен! Проверьте вкладку Bestellvorschlag.")

# ==========================================
# 4. НАСТРОЙКИ И РОЛИ
# ==========================================
elif action == "⚙️ Einstellungen":
  st.header("⚙️ Einstellungen & Rollen")
  role_choice = st.selectbox(
      "Переключить роль",
      ["Manager", "Agent"],
      index=0 if st.session_state["user_role"] == "Manager" else 1,
  )
  if role_choice != st.session_state["user_role"]:
    st.session_state["user_role"] = role_choice
    st.rerun()
  st.write(f"Текущие права доступа настроены для роли: {st.session_state['user_role']}")
