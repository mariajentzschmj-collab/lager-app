import pandas as pd
import streamlit as st
from supabase import create_client

# Настройка страницы
st.set_page_config(
    page_title="KaDeWe Lager — Iittala & Royal Copenhagen", layout="wide"
)

st.title("📦 Lagerverwaltung (5. Etage)")
st.subheader("Iittala & Royal Copenhagen")

# Подключение к Supabase с защитой от сбоев
supabase = None
try:
  url = st.secrets["supabase"]["url"]
  key = st.secrets["supabase"]["key"]
  supabase = create_client(url, key)
except Exception as e:
  st.warning(
      "⚠️ Achtung: Keine Verbindung zur Cloud-Datenbank (Supabase). Die"
      " Anwendung läuft im Offline-Modus."
  )


# Функция для загрузки данных из базы
def load_data():
  if supabase is None:
    return pd.DataFrame(columns=["id", "name", "brand", "quantity", "price"])
  try:
    response = supabase.table("inventory").select("*").execute()
    if response.data:
      return pd.DataFrame(response.data)
  except Exception as e:
    st.error(f"Fehler beim Laden der Daten: {e}")
  return pd.DataFrame(columns=["id", "name", "brand", "quantity", "price"])


df = load_data()

# --- SEITENMENÜ ---
st.sidebar.header("⚙️ Lagersteuerung")
action = st.sidebar.radio(
    "Aktion auswählen:",
    [
        "📊 Bestände anzeigen",
        "➕ Artikel hinzufügen",
        "📉 Artikel reduzieren (Verkauf)",
        "📁 Katalog aus Datei hochladen",
    ],
)

# 1. BESTÄNDE ANZEIGEN
if action == "📊 Bestände anzeigen":
  st.header("📋 Aktuelles Sortiment")
  if df.empty:
    st.info(
        "Das Lager ist leer oder keine Verbindung zur Datenbank möglich."
    )
  else:
    search_query = st.text_input(
        "🔍 Artikel nach Name suchen (Suche eingeben):"
    )
    filtered_df = df
    if search_query:
      filtered_df = df[
          df["name"].str.contains(search_query, case=False, na=False)
      ]

    st.dataframe(filtered_df, use_container_width=True)

# 2. ARTIKEL HINZUFÜGEN
elif action == "➕ Artikel hinzufügen":
  st.header("✨ Neuen Artikel hinzufügen")

  with st.form("add_form"):
    new_name = st.text_input(
        "Artikelname (z. B. Iittala Ultima Thule / Royal Copenhagen)"
    )
    new_brand = st.selectbox(
        "Marke", ["Iittala", "Royal Copenhagen", "Arabia", "Georg Jensen"]
    )
    new_qty = st.number_input("Menge im Lager", min_value=0, value=1)
    new_price = st.number_input(
        "Preis (€)", min_value=0.0, value=0.0, format="%.2f"
    )

    submitted = st.form_submit_button("In Datenbank speichern")
    if submitted:
      if new_name:
        if supabase is not None:
          data = {
              "name": new_name,
              "brand": new_brand,
              "quantity": int(new_qty),
              "price": float(new_price),
          }
          supabase.table("inventory").insert(data).execute()
          st.success(f"Artikel '{new_name}' erfolgreich hinzugefügt!")
          st.rerun()
        else:
          st.error(
              "Keine Verbindung zur Datenbank. Speichern nicht möglich."
          )
      else:
        st.error("Bitte geben Sie einen Artikelnamen ein.")

# 3. ARTIKEL REDUZIEREN (VERKAUF)
elif action == "📉 Artikel reduzieren (Verkauf)":
  st.header("🛒 Verkauf / Bestandsreduzierung erfassen")

  if df.empty:
    st.warning("Keine Artikel zum Reduzieren vorhanden.")
  else:
    with st.form("reduce_form"):
      item_options = df["name"].tolist()
      selected_item = st.selectbox("Artikel auswählen", item_options)

      current_qty = int(
          df.loc[df["name"] == selected_item, "quantity"].values[0]
      )
      st.write(f"Aktueller Bestand im Lager: **{current_qty} Stk.**")

      reduce_qty = st.number_input(
          "Wie viele Stk. wurden verkauft / aus dem Lager genommen?",
          min_value=1,
          max_value=max(1, current_qty),
          value=1,
      )

      submit_reduce = st.form_submit_button("Verkauf bestätigen")
      if submit_reduce:
        new_qty = current_qty - int(reduce_qty)
        if supabase is not None:
          supabase.table("inventory").update({"quantity": new_qty}).eq(
              "name", selected_item
          ).execute()
          st.success(
              f"Bestand für '{selected_item}' aktualisiert! Neuer Bestand:"
              f" {new_qty} Stk."
          )
          st.rerun()
        else:
          st.error("Keine Verbindung zur Datenbank.")

# 4. KATALOG AUS DATEI HOCHLADEN
elif action == "📁 Katalog aus Datei hochladen":
  st.header("📂 Massen-Upload des Katalogs")
  st.write(
      "Laden Sie eine Excel- (.xlsx) oder CSV-Datei hoch. Die Spalten im"
      " Dokument müssen lauten: `name`, `brand`, `quantity`, `price`."
  )

  uploaded_file = st.file_uploader(
      "Katalogdatei auswählen", type=["xlsx", "csv"]
  )

  if uploaded_file is not None:
    try:
      if uploaded_file.name.endswith(".xlsx"):
        import openpyxl

        upload_df = pd.read_excel(uploaded_file)
      else:
        upload_df = pd.read_csv(uploaded_file)

      st.write("Vorschau der hochgeladenen Datei:")
      st.dataframe(upload_df.head())

      if st.button("Alles in Supabase-Datenbank hochladen"):
        if supabase is not None:
          records = upload_df.to_dict(orient="records")
          supabase.table("inventory").insert(records).execute()
          st.success("Katalog erfolgreich in die Datenbank importiert!")
          st.rerun()
        else:
          st.error("Keine Verbindung zur Datenbank.")
    except Exception as e:
      st.error(
          "Fehler beim Lesen der Datei. Überprüfen Sie die Spaltennamen:"
          f" {e}"
      )
