import streamlit as st
import pandas as pd
from datetime import datetime, date

def init_time_tracker_widget(supabase_client, github_file_path="2026_PEP.xlsx"):
    """
    Универсальный модуль: читает график с GitHub и выводит виджет Zeiterfassung внизу страницы.
    Основной app.py менять не придется!
    """
    
    # 1. Загрузка графика прямо из GitHub (или локальной папки проекта)
    try:
        if github_file_path.endswith('.csv'):
            pep_df = pd.read_csv(github_file_path)
        else:
            pep_df = pd.read_excel(github_file_path)
    except Exception:
        pep_df = None  # Если файла нет под рукой, приложение не упадет

    st.markdown("---")
    st.markdown("### ⏱️ Zeiterfassung & Arbeitszeitkontrolle")
    
    # Определяем текущего вошедшего сотрудника из сессии Streamlit
    current_user = (
        st.session_state.get("user_fullname") or 
        st.session_state.get("user_display_name") or 
        st.session_state.get("username") or 
        st.session_state.get("view_emp_selectbox") or 
        "Unbekannt"
    )

    today = date.today()
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**Mitarbeiter:** {current_user}")
        st.write(f"**Datum:** {today.strftime('%d.%m.%Y')}")
        
        # Получаем запись за сегодня из Supabase (таблица time_tracking уже создана)
        existing_record = None
        try:
            res = supabase_client.table("time_tracking")\
                .select("*")\
                .eq("employee_name", current_user)\
                .eq("work_date", str(today))\
                .execute()
            if res.data:
                existing_record = res.data[0]
        except Exception as e:
            st.error(f"Fehler beim Laden der Zeiterfassungsdaten: {e}")

        default_in = datetime.strptime(existing_record["time_in"], "%H:%M").time() if existing_record and existing_record.get("time_in") else datetime.now().time()
        default_out = datetime.strptime(existing_record["time_out"], "%H:%M").time() if existing_record and existing_record.get("time_out") else datetime.now().time()
        
        t_in = st.time_input("Kommenszeit:", value=default_in)
        t_out = st.time_input("Gehenszeit:", value=default_out)
        
        # Оплачиваемая пауза по умолчанию, но с возможностью включить вычет
        deduct_break = st.checkbox("Pause abziehen (45 Minuten)", value=False)
        
        if st.button("💾 Arbeitszeit speichern", type="primary"):
            datetime_in = datetime.combine(today, t_in)
            datetime_out = datetime.combine(today, t_out)
            
            if datetime_out > datetime_in:
                duration_hours = (datetime_out - datetime_in).total_seconds() / 3600.0
                if deduct_break and duration_hours > 6.0:
                    duration_hours -= 0.75
                duration_hours = round(max(0.0, duration_hours), 2)
            else:
                duration_hours = 0.0
            
            data_to_save = {
                "employee_name": current_user,
                "work_date": str(today),
                "time_in": t_in.strftime("%H:%M"),
                "time_out": t_out.strftime("%H:%M"),
                "total_hours": duration_hours
            }
            
            try:
                if existing_record:
                    supabase_client.table("time_tracking").update(data_to_save).eq("id", existing_record["id"]).execute()
                else:
                    supabase_client.table("time_tracking").insert(data_to_save).execute()
                st.success(f"Erfolgreich gespeichert: {duration_hours} Std. für heute!")
                st.rerun()
            except Exception as err:
                st.error(f"Fehler beim Speichern: {err}")

    with col2:
        st.write("📊 **Monatsübersicht (Aktueller Monat)**")
        current_month_str = today.strftime("%Y-%m")
        
        try:
            res_month = supabase_client.table("time_tracking")\
                .select("*")\
                .eq("employee_name", current_user)\
                .gte("work_date", f"{current_month_str}-01")\
                .execute()
                
            if res_month.data:
                df_month = pd.DataFrame(res_month.data)
                total_worked_hours = df_month["total_hours"].sum()
                days_worked = len(df_month)
                
                st.metric("Geleistete Stunden in diesem Monat", f"{total_worked_hours:.2f} Std.")
                st.metric("Gearbeitete Tage", f"{days_worked}")
                
                st.dataframe(
                    df_month[["work_date", "time_in", "time_out", "total_hours"]].rename(columns={
                        "work_date": "Datum",
                        "time_in": "Kommen",
                        "time_out": "Gehen",
                        "total_hours": "Stunden (netto)"
                    }),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("Bislang keine Einträge in diesem Monat vorhanden.")
        except Exception as e:
            st.error(f"Monatsbericht konnte nicht geladen werden: {e}")
            
    return pep_df
