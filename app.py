# ==========================================
# MONATLICHE UMSATZANFRAGE (MIT 19% MWST.-ABZUG)
# ==========================================

st.sidebar.markdown("---")
st.sidebar.subheader("💶 Detaillierter Umsatz nach Monaten")

st.sidebar.markdown(
    "Laden Sie den Verkaufsbericht hoch (ab 01.01.2026), um den Nettoumsatz monatlich zu berechnen."
)

sales_file_monthly = st.sidebar.file_uploader(
    "Verkaufsbericht (Jahresdatei) hochladen",
    type=["xlsx", "csv"],
    key="sales_report_monthly",
)

if sales_file_monthly is not None:
    try:
        import pandas as pd

        if sales_file_monthly.name.endswith(".csv"):
            sales_monthly_df = pd.read_csv(sales_file_monthly)
        else:
            sales_monthly_df = pd.read_excel(sales_file_monthly)

        st.sidebar.success("✅ Jahresbericht erfolgreich geladen!")

        columns_list = list(sales_monthly_df.columns)
        
        date_col = st.sidebar.selectbox("Spalte für das Datum", columns_list, key="d_col")
        qty_col_m = st.sidebar.selectbox("Spalte für verkaufte Menge", columns_list, key="qm_col")
        price_col_m = st.sidebar.selectbox("Spalte für tatsächlichen Verkaufspreis", columns_list, key="pm_col")

        if st.sidebar.button("📊 Monatsumsatz berechnen"):
            sales_monthly_df[date_col] = pd.to_datetime(sales_monthly_df[date_col], errors='coerce')
            
            sales_monthly_df["Monat"] = sales_monthly_df[date_col].dt.to_period("M").astype(str)
            
            sales_monthly_df["Brutto"] = (
                pd.to_numeric(sales_monthly_df[qty_col_m], errors='coerce').fillna(0) * 
                pd.to_numeric(sales_monthly_df[price_col_m], errors='coerce').fillna(0)
            )

            grouped = sales_monthly_df.groupby("Monat")["Brutto"].sum().reset_index()
            
            grouped["Netto (exkl. 19% MwSt.)"] = grouped["Brutto"] / 1.19
            grouped["Brutto (inkl. 19% MwSt.)"] = grouped["Brutto"]

            grouped = grouped.sort_values("Monat")

            st.sidebar.markdown("---")
            st.sidebar.write("### 📈 Umsatz nach Monaten:")
            
            for _, row in grouped.iterrows():
                month_name = row["Monat"]
                net_val = row["Netto (exkl. 19% MwSt.)"]
                brutto_val = row["Brutto (inkl. 19% MwSt.)"]
                st.sidebar.markdown(f"**{month_name}:** Netto: **{net_val:,.2f} €** *(Brutto: {brutto_val:,.2f} €)*")

    except Exception as e:
        st.sidebar.error(f"⚠ Fehler bei der Auswertung: {e}")
