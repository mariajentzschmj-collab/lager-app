# ==========================================
# UMSATZBERECHNUNG & AKKUMULATION (TAG & MONAT)
# ==========================================

st.sidebar.markdown("---")
st.sidebar.subheader("💶 Umsatz-Tracking (Tage & Monate)")

st.sidebar.markdown(
    "Laden Sie einen Tages- oder Monatsbericht hoch. Die Umsätze werden automatisch in der Datenbank gespeichert und kumuliert."
)

sales_file = st.sidebar.file_uploader(
    "Verkaufsbericht hochladen (Excel / CSV)", type=["xlsx", "csv"], key="sales_report_accum"
)

if sales_file is not None:
    try:
        import pandas as pd

        if sales_file.name.endswith(".csv"):
            sales_report_df = pd.read_csv(sales_file)
        else:
            sales_report_df = pd.read_excel(sales_file)

        st.sidebar.success("✅ Bericht erfolgreich geladen!")
        st.sidebar.write("Vorschau der Spalten:", list(sales_report_df.columns))

        # Выбор нужных колонок
        date_col = st.sidebar.selectbox("Spalte für das Datum", sales_report_df.columns, key="acc_date_col")
        price_col = st.sidebar.selectbox("Spalte für Gesamtpreis / Umsatz", sales_report_df.columns, key="acc_price_col")

        if st.sidebar.button("💾 Umsatz speichern & kumulieren"):
            # Очищаем и суммируем общую сумму брутто из файла
            cleaned_prices = (
                sales_report_df[price_col]
                .astype(str)
                .str.replace('€', '', regex=False)
                .str.replace(' ', '', regex=False)
                .str.replace(',', '.', regex=False)
            )
            total_brutto = pd.to_numeric(cleaned_prices, errors='coerce').sum()

            # Превращаем даты в формат YYYY-MM-DD для сохранения
            sales_report_df[date_col] = pd.to_datetime(sales_report_df[date_col], errors='coerce')
            
            # Определяем дату отчета (берем первую встретившуюся корректную дату из файла)
            valid_dates = sales_report_df[date_col].dropna()
            if not valid_dates.empty:
                report_date = valid_dates.iloc[0].strftime('%Y-%m-%d')
                report_month = valid_dates.iloc[0].strftime('%Y-%m')
            else:
                report_date = pd.Timestamp.today().strftime('%Y-%m-%d')
                report_month = pd.Timestamp.today().strftime('%Y-%m')

            # Сохранение в Supabase (если таблица 'daily_sales' настроена)
            if supabase is not None:
                try:
                    # Проверяем, есть ли запись за этот день
                    existing_day = supabase.table("daily_sales").select("*").eq("date", report_date).execute()
                    
                    if existing_day and existing_day.data:
                        # Обновляем существующий день
                        supabase.table("daily_sales").update({
                            "brutto": float(total_brutto),
                            "month": report_month
                        }).eq("date", report_date).execute()
                    else:
                        # Создаем новую запись за день
                        supabase.table("daily_sales").insert({
                            "date": report_date,
                            "brutto": float(total_brutto),
                            "month": report_month
                        }).execute()
                    
                    st.sidebar.success(f"✔ Umsatz für {report_date} ({total_brutto:,.2f} €) erfolgreich gespeichert!")
                except Exception as db_err:
                    st.sidebar.warning(f"⚠ Hinweis zur DB-Speicherung: {db_err}")

            # Вывод результатов текущего отчета
            total_netto = total_brutto / 1.19
            st.sidebar.markdown("---")
            st.sidebar.metric(label="Brutto (dieser Bericht)", value=f"{total_brutto:,.2f} €")
            st.sidebar.metric(label="Netto (exkl. 19% MwSt.)", value=f"{total_netto:,.2f} €")

    except Exception as e:
        st.sidebar.error(f"⚠ Fehler beim Verarbeiten: {e}")

# Блок отображения накопленной статистики из базы данных
if supabase is not None:
    st.sidebar.markdown("---")
    st.sidebar.subheader("📈 Kumulierte Umsätze (Historie)")
    
    try:
        # Загружаем все сохраненные данные из базы
        history_res = supabase.table("daily_sales").select("*").execute()
        if history_res and history_res.data:
            hist_df = pd.DataFrame(history_res.data)
            
            if not hist_df.empty and "month" in hist_df.columns and "brutto" in hist_df.columns:
                # Группируем по месяцам для накопительного отображения
                monthly_summary = hist_df.groupby("month")["brutto"].sum().reset_index()
                monthly_summary = monthly_summary.sort_values("month")

                st.sidebar.markdown("**Nach Monaten:**")
                for _, row in monthly_summary.iterrows():
                    m_name = row["month"]
                    m_brutto = row["brutto"]
                    m_netto = m_brutto / 1.19
                    st.sidebar.markdown(f"🗓 **{m_name}**: Netto **{m_netto:,.2f} €** *(Brutto: {m_brutto:,.2f} €)*")
        else:
            st.sidebar.info("ℹ Noch keine kumulierten Daten in der Datenbank vorhanden.")
    except Exception as hist_err:
        # Если таблица еще не создана в Supabase, выводим подсказку для администратора
        st.sidebar.caption("💡 Tipp: Erstellen Sie in Supabase eine Tabelle `daily_sales` mit den Spalten `date`, `brutto` und `month`, um die Historie zu speichern.")
