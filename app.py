import streamlit as st
import pandas as pd
import datetime

# --- Настройка страницы ---
st.set_page_config(
    page_title="KaDeWe - Iittala & Royal Copenhagen Management",
    page_icon="🛍️",
    layout="wide"
)

# --- Инициализация состояния сессии (Mock / Supabase симуляция) ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "role" not in st.session_state:
    st.session_state.role = None

# Пример базы данных товаров (включая Min/Max для нового функционала заказов)
if "inventory_df" not in st.session_state:
    st.session_state.inventory_df = pd.DataFrame([
        {
            "Article": "1005231", 
            "Name": "Teema Teller flach 26cm weiß", 
            "Brand": "Iittala", 
            "Quantity": 12, 
            "Min_Stock": 15, 
            "Max_Stock": 40, 
            "Price": 24.99, 
            "Barcode": "6411920012345"
        },
        {
            "Article": "1028345", 
            "Name": "Aalto Vase 160mm klar", 
            "Brand": "Iittala", 
            "Quantity": 3, 
            "Min_Stock": 5, 
            "Max_Stock": 12, 
            "Price": 169.00, 
            "Barcode": "6411920987654"
        },
        {
            "Article": "1016890", 
            "Name": "Blue Fluted Plain Becher mit Henkel", 
            "Brand": "Royal Copenhagen", 
            "Quantity": 8, 
            "Min_Stock": 10, 
            "Max_Stock": 30, 
            "Price": 45.00, 
            "Barcode": "5705140123456"
        },
        {
            "Article": "1016892", 
            "Name": "Blue Fluted Plain Teller tief 21cm", 
            "Brand": "Royal Copenhagen", 
            "Quantity": 4, 
            "Min_Stock": 8, 
            "Max_Stock": 25, 
            "Price": 65.00, 
            "Barcode": "5705140654321"
        }
    ])

if "orders_history" not in st.session_state:
    st.session_state.orders_history = []

# --- Авторизация по PIN-коду ---
st.sidebar.title("🔐 Авторизация (KaDeWe)")
if not st.session_state.authenticated:
    pin = st.sidebar.text_input("Введите PIN-код", type="password")
    if st.sidebar.button("Войти"):
        # Простой пример пин-кодов: Менеджер (Мария) или Продавец
        if pin == "1972":  # Пример личного PIN
            st.session_state.authenticated = True
            st.session_state.role = "Менеджер"
            st.rerun()
        elif pin == "1234":
            st.session_state.authenticated = True
            st.session_state.role = "Продавец"
            st.rerun()
        else:
            st.sidebar.error("Неверный PIN-код")
    st.stop()
else:
    st.sidebar.success(f"Вход выполнен ({st.session_state.role})")
    if st.sidebar.button("Выйти"):
        st.session_state.authenticated = False
        st.session_state.role = None
        st.rerun()

# --- Главное меню ---
st.title("🏬 KaDeWe: Управление складом и магазином")
st.subheader("Бренды: Iittala & Royal Copenhagen (5-й этаж)")

tab_stock, tab_order_prep, tab_labels, tab_reports = st.tabs([
    "📦 Остатки и каталог", 
    "📋 Заказ со склада (Min/Max)", 
    "🏷️ Печать ценников", 
    "📊 Отчеты и продажи"
])

# --- Вкладка 1: Остатки и каталог (Старая функция) ---
with tab_stock:
    st.header("Текущие товарные остатки")
    
    brand_filter = st.selectbox("Фильтр по бренду", ["Все", "Iittala", "Royal Copenhagen"])
    df = st.session_state.inventory_df
    
    if brand_filter != "Все":
        df = df[df["Brand"] == brand_filter]
        
    st.dataframe(df, use_container_width=True)
    
    if st.session_state.role == "Менеджер":
        st.markdown("---")
        st.subheader("Редактирование / Добавление товара (Менеджер)")
        with st.form("add_item_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                new_art = st.text_input("Артикул")
                new_name = st.text_input("Название")
            with col2:
                new_brand = st.selectbox("Бренд", ["Iittala", "Royal Copenhagen"])
                new_qty = st.number_input("Текущий остаток", min_value=0, value=10)
            with col3:
                new_min = st.number_input("Мин. остаток (Min)", min_value=0, value=5)
                new_max = st.number_input("Макс. остаток (Max)", min_value=0, value=25)
                new_price = st.number_input("Цена (€)", min_value=0.0, value=20.0)
            
            submitted = st.form_submit_button("Сохранить товар")
            if submitted and new_art:
                # Добавление в состояние
                new_row = pd.DataFrame([{
                    "Article": new_art,
                    "Name": new_name,
                    "Brand": new_brand,
                    "Quantity": new_qty,
                    "Min_Stock": new_min,
                    "Max_Stock": new_max,
                    "Price": new_price,
                    "Barcode": f"6411920{new_art}"
                }])
                st.session_state.inventory_df = pd.concat([st.session_state.inventory_df, new_row], ignore_index=True)
                st.success(f"Товар {new_name} успешно добавлен!")
                st.rerun()

# --- Вкладка 2: Подготовка заказов (Min/Max + 30 дней) — НОВЫЙ ФУНКЦИОНАЛ ---
with tab_order_prep:
    st.header("📋 Автоматическая подготовка заказов (Min / Max)")
    st.markdown(
        "Этот инструмент анализирует текущие остатки на складе и рассчитывает необходимые объемы "
        "пополнения с учетом **прогноза поставки на 30 дней вперед**."
    )
    
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        lead_time_days = st.number_input("Расчетный срок доставки (дней)", min_value=1, value=30)
    with col_opt2:
        order_filter_brand = st.selectbox("Бренд для заказа", ["Все", "Iittala", "Royal Copenhagen"], key="order_brand")

    # Расчет потребности
    df_inv = st.session_state.inventory_df.copy()
    if order_filter_brand != "Все":
        df_inv = df_inv[df_inv["Brand"] == order_filter_brand]

    # Логика: если Quantity <= Min_Stock, заказываем до Max_Stock
    # Учитываем условный коэффициент оборачиваемости на 30 дней (можно расширить)
    order_list = []
    for idx, row in df_inv.iterrows():
        current_qty = row["Quantity"]
        min_s = row["Min_Stock"]
        max_s = row["Max_Stock"]
        
        if current_qty <= min_s:
            suggested_qty = max_s - current_qty
        else:
            suggested_qty = 0  # Заказ не требуется
            
        order_list.append({
            "Article": row["Article"],
            "Name": row["Name"],
            "Brand": row["Brand"],
            "Current Qty": current_qty,
            "Min": min_s,
            "Max": max_s,
            "Suggested Order Qty": suggested_qty,
            "Price (€)": row["Price"],
            "Total Cost (€)": round(suggested_qty * row["Price"], 2)
        })

    df_orders = pd.DataFrame(order_list)
    df_to_order = df_orders[df_orders["Suggested Order Qty"] > 0]

    st.subheader("Товары, требующие заказа:")
    if not df_to_order.empty:
        st.dataframe(df_to_order, use_container_width=True)
        
        total_items_to_order = df_to_order["Suggested Order Qty"].sum()
        total_cost_sum = df_to_order["Total Cost (€)"].sum()
        
        st.metric("Общее количество к заказу", f"{total_items_to_order} шт.")
        st.metric("Общая расчетная стоимость", f"{total_cost_sum:.2f} €")
        
        if st.button("📤 Сформировать и зафиксировать заказ"):
            order_record = {
                "date": datetime.date.today().strftime("%Y-%m-%d"),
                "lead_time": f"{lead_time_days} дней",
                "items_count": total_items_to_order,
                "total_cost": total_cost_sum,
                "status": "Создан (Ожидает подтверждения Марии)"
            }
            st.session_state.orders_history.append(order_record)
            st.success("Заказ успешно сформирован и отправлен в архив / систему согласования!")
    else:
        st.info("На текущий момент все остатки находятся выше минимальных порогов. Дополнительный заказ не требуется.")

    if st.session_state.orders_history:
        st.markdown("---")
        st.subheader("История сформированных заказов")
        st.dataframe(pd.DataFrame(st.session_state.orders_history), use_container_width=True)

# --- Вкладка 3: Печать ценников (Старая функция) ---
with tab_labels:
    st.header("🏷️ Генерация и печать ценников")
    st.markdown("Выберите товары для печати ценников для витрин KaDeWe (5-й этаж).")
    
    selected_brand_labels = st.selectbox("Бренд ценников", ["Iittala", "Royal Copenhagen"], key="lbl_brand")
    df_labels = st.session_state.inventory_df[st.session_state.inventory_df["Brand"] == selected_brand_labels]
    
    selected_articles = st.multiselect("Выберите артикулы", df_labels["Article"].tolist())
    
    if selected_articles:
        st.subheader("Предпросмотр ценников:")
        for art in selected_articles:
            item_info = df_labels[df_labels["Article"] == art].iloc[0]
            st.markdown(f"""
            <div style="border: 2px solid #333; padding: 15px; border-radius: 8px; width: 300px; margin-bottom: 10px; background-color: white; color: black;">
                <h4 style="margin: 0; color: #555;">KaDeWe Berlin — {item_info['Brand']}</h4>
                <hr style="margin: 5px 0;">
                <h3 style="margin: 5px 0;">{item_info['Name']}</h3>
                <p style="margin: 0; font-size: 14px;">Art.Nr: {item_info['Article']}</p>
                <h2 style="margin: 5px 0; color: #b22222;">{item_info['Price']} €</h2>
            </div>
            """, unsafe_allow_html=True)

# --- Вкладка 4: Отчеты и продажи (Старая функция) ---
with tab_reports:
    st.header("📊 Аналитика и отчеты")
    st.metric("Всего позиций в каталоге", len(st.session_state.inventory_df))
    st.metric("Общая стоимость складских запасов", f"{(st.session_state.inventory_df['Quantity'] * st.session_state.inventory_df['Price']).sum():.2f} €")
    
    st.markdown("### Экспорт данных")
    csv_data = st.session_state.inventory_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Скачать текущие остатки (CSV)",
        data=csv_data,
        file_name=f"KaDeWe_Inventory_{datetime.date.today()}.csv",
        mime="text/csv"
    )
