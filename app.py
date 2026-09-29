import urllib.parse
import pandas as pd
import streamlit as st
from streamlit_zxing import st_zxing
from supabase import create_client

# Настройка страницы
st.set_page_config(
    page_title="KaDeWe Lager — Iittala & Royal Copenhagen", layout="wide"
)

st.title("📦 Lagerverwaltung (5. Etage)")
st.subheader("Iittala & Royal Copenhagen")

# Подключение к Supabase
SUPABASE_URL = "https://mtcbfvpjnxlkvvtuknyv.supabase.co"
SUPABASE_KEY = "sb_publishable_wChGuVU2FeW23S2bqdYqOg_B9-oMoKs"

supabase = None
try:
  supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
  pass


# Функция для загрузки данных из базы
def load_data():
  cols = [
      "id",
      "article",
      "name",
      "brand",
      "quantity",
      "location",
      "preis",
      "sap",
      "barcode",
  ]
  if supabase is None:
    st.warning("⚠️ Offline-Modus (keine Verbindung zur Datenbank).")
    return pd.DataFrame(columns=cols)
  try:
    response = supabase.table("inventory").select("*").execute()
    if response.data:
      return pd.DataFrame(response.data)
  except Exception as e:
    st.info("💡 Datenbank vorübergehend nicht erreichbar.")
  return pd.DataFrame(columns=cols)


df = load_data()

# --- SEITENMENÜ ---
st.sidebar.header("⚙️ Lagersteuerung")
action = st.sidebar.radio(
    "Aktion auswählen:",
    [
        "📊 Bestände anzeigen",
        "➕ Artikel hinzufügen",
        "📉 Artikel reduzieren (Verkauf)",
        "📷 Barcode scannen",
        "📁 Katalog aus Datei hochladen",
        "🖨 QR-Code für Kollegen",
    ],
)

# 1. BESTÄNDE ANZEIGEN
if action == "📊 Bestände anzeigen":
  st.header("📋 Aktuelles Sortiment")
  if df.empty:
    st.info("Das Lager ist leer oder keine Verbindung zur Datenbank möglich.")
  else:
    search_query = st.text_input(
        "🔍 Artikel nach Name oder Barcode suchen:"
    )
    filtered_df = df
    if search_query:
      filtered_df = df[
          df["name"].str.contains(search_query, case=False, na=False)
          | df["barcode"].astype(str).str.contains(
              search_query, case=False, na=False
          )
      ]

    st.dataframe(filtered_df, use_container_width=True)

# 2. ARTIKEL HINZUFÜGEN
elif action == "➕ Artikel hinzufügen":
  st.header("✨ Neuen Artikel hinzufügen")

  with st.form("add_form"):
    new_article = st.text_input("Artikelnummer / SKU", value="")
    new_name = st.text_input(
        "Artikelname (z. B. Iittala Ultima Thule / Royal Copenhagen)"
    )
    new_brand = st.selectbox(
        "Marke", ["Iittala", "Royal Copenhagen", "Arabia", "Georg Jensen"]
    )
    new_qty = st.number_input("Menge im Lager", min_value=0, value=1)
    new_location = st.text_input("Lagerort", value="Etage 5 Lager")
    new_preis = st.number_input(
        "Preis (€)", min_value=0.0, value=0.0, format="%.2f"
    )
    new_sap = st.text_input("SAP-Nummer")
    new_barcode = st.text_input("Barcode")

    submitted = st.form_submit_button("In Datenbank speichern")
    if submitted:
      if not new_name:
        st.error("Bitte geben Sie einen Artikelnamen ein.")
      elif supabase is None:
        st.error("Keine Verbindung zur Datenbank. Speichern nicht möglich.")
      else:
        is_duplicate = False
        duplicate_reason = ""

        if not df.empty:
          if new_article and (df["article"].astype(str) == new_article).any():
            is_duplicate = True
            duplicate_reason = (
                f"Artikelnummer (SKU) '{new_article}' existiert bereits im Lager!"
            )
          elif new_barcode and (df["barcode"].astype(str) == new_barcode).any():
            is_duplicate = True
            duplicate_reason = (
                f"Barcode '{new_barcode}' existiert bereits im Lager!"
            )

        if is_duplicate:
          st.error(f"⚠️ Achtung, Duplikat erkannt: {duplicate_reason}")
        else:
          try:
            data = {
                "article": str(new_article),
                "name": str(new_name),
                "brand": str(new_brand),
                "quantity": int(new_qty),
                "location": str(new_location),
                "preis": float(new_preis),
                "sap": str(new_sap),
                "barcode": str(new_barcode),
            }
            supabase.table("inventory").insert(data).execute()
            st.success(f"Artikel '{new_name}' erfolgreich hinzugefügt!")
            st.rerun()
          except Exception as e:
            st.error(f"Fehler beim Speichern in die Datenbank: {e}")

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
          try:
            supabase.table("inventory").update({"quantity": new_qty}).eq(
                "name", selected_item
            ).execute()
            st.success(
                f"Bestand für '{selected_item}' aktualisiert! Neuer Bestand:"
                f" {new_qty} Stk."
            )
            st.rerun()
          except Exception as e:
            st.error(f"Fehler bei der Aktualisierung: {e}")
        else:
          st.error("Keine Verbindung zur Datenbank.")

# 4. BARCODE SCANNEN
elif action == "📷 Barcode scannen":
  st.header("📷 Barcode mit der Handykamera scannen")
  st.write(
      "Richten Sie die Kamera Ihres Smartphones auf den Barcode des Produkts."
  )

  scanned_barcode = st_zxing()

  if scanned_barcode:
    st.success(f"Erannter Barcode: **{scanned_barcode}**")
    if not df.empty and "barcode" in df.columns:
      matched_item = df[df["barcode"].astype(str) == str(scanned_barcode)]
      if not matched_item.empty:
        st.write("Gefundener Artikel in der Datenbank:")
        st.dataframe(matched_item, use_container_width=True)
      else:
        st.warning(
            "Kein Artikel mit diesem Barcode in der Datenbank gefunden."
        )

# 5. KATALOG AUS DATEI HOCHLADEN
elif action == "📁 Katalog aus Datei hochladen":
  st.header("📂 Massen-Upload des Katalogs")
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
          try:
            records = upload_df.to_dict(orient="records")
            supabase.table("inventory").insert(records).execute()
            st.success("Katalog erfolgreich in die Datenbank importiert!")
            st.rerun()
          except Exception as e:
            st.error(f"Fehler beim Hochladen der Datensätze: {e}")
        else:
          st.error("Keine Verbindung zur Datenbank.")
    except Exception as e:
      st.error(f"Fehler beim Lesen der Datei: {e}")

# 6. QR-CODE FÜR KOLLEGEN
elif action == "🖨 QR-Code für Kollegen":
  st.header("🖨 QR-Code für den schnellen Zugriff vom Smartphone")
  st.write(
      "Kollegen können die Handykamera auf diesen Code richten, um das"
      " Lager-App direkt auf der 5. Etage zu öffnen."
  )

  app_url = "https://mtcbfvpjnxlkvvtuknyv.streamlit.app"
  encoded_url = urllib.parse.quote(app_url)
  qr_image_url = (
      f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={encoded_url}"
  )

  st.image(qr_image_url, width=300)
  st.info(
      "💡 Sie können mit der rechten Maustaste auf das Bild klicken, „Bild"
      " speichern unter...“ wählen und es für den Arbeitsbereich ausdrucken."
  )
