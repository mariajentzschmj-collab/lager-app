import urllib.parse
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client

# Настройка страницы
st.set_page_config(
    page_title="KaDeWe Lager — Iittala & Royal Copenhagen", layout="wide"
)


# --- ПРОСТАЯ АВТОРИЗАЦИЯ (ЗАЩИТА ПАРОЛЕМ) ---
def check_password():
  """Возвращает True, если пользователь ввел правильный пароль."""

  def password_entered():
    # Можете изменить "kadewe2026" на любой другой секретный пароль для коллег
    if st.session_state["password"] == "kadewe2026":
      st.session_state["password_correct"] = True
      del st.session_state["password"]  # Удаляем пароль из сессии в целях безопасности
    else:
      st.session_state["password_correct"] = False

  if "password_correct" not in st.session_state:
    # Первый вход, запрашиваем пароль
    st.text_input(
        "🔑 Bitte Passwort eingeben / Введите пароль для доступа к складу:",
        type="password",
        on_change=password_entered,
        key="password",
    )
    return False
  elif not st.session_state["password_correct"]:
    # Неверный пароль
    st.text_input(
        "🔑 Bitte Passwort eingeben / Введите пароль для доступа к складу:",
        type="password",
        on_change=password_entered,
        key="password",
    )
    st.error("❌ Falsches Passwort / Неверный пароль")
    return False
  else:
    # Пароль верный
    return True


# Если пароль не введен, останавливаем выполнение приложения здесь
if not check_password():
  st.stop()


# --- ОСНОВНОЙ КОД ПРИЛОЖЕНИЯ ---
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
    if response.data is not None:
      return pd.DataFrame(response.data)
  except Exception as e:
    st.error(f"❌ Fehler beim Laden der Daten: {e}")
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
        "📷 Live-Kamera-Scanner",
        "📁 Katalog aus Datei hochladen",
        "🖨 Etiketten drucken",
        "📱 QR-Code für Kollegen",
    ],
)

# 1. BESTÄNDE ANZEIGEN
if action == "📊 Bestände anzeigen":
  st.header("📋 Aktuelles Sortiment")
  if df.empty:
    st.info("Das Lager ist leer oder keine Verbindung zur Datenbank möglich.")
  else:
    search_query = st.text_input(
        "🔍 Artikel nach Name, Artikelnummer oder Barcode suchen:"
    )
    filtered_df = df
    if search_query:
      q = search_query.strip().lower()
      filtered_df = df[
          df["name"].astype(str).str.lower().str.contains(q, na=False)
          | df["barcode"].astype(str).str.lower().str.contains(q, na=False)
          | df["article"].astype(str).str.lower().str.contains(q, na=False)
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
          st.error(f"Fehler beim Speichern: {e}")

# 3. ARTIKEL REDUZIEREN (VERKAUF)
elif action == "📉 Artikel reduzieren (Verkauf)":
  st.header("🛒 Verkauf / Bestandsreduzierung erfassen")

  if df.empty:
    st.warning("Keine Artikel zum Reduzieren vorhanden.")
  else:
    with st.form("reduce_form"):
      item_options = df["name"].tolist()
      selected_item = st.selectbox("Artikel auswählen", item_options)

      current_qty_val = df.loc[
          df["name"] == selected_item, "quantity"
      ].values[0]
      current_qty = (
          int(current_qty_val)
          if pd.notna(current_qty_val) and str(current_qty_val).isdigit()
          else 0
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

# 4. LIVE-KAMERA-SCANNER
elif action == "📷 Live-Kamera-Scanner":
  st.header("📷 Live-Barcode-Scanner für Smartphones")
  st.write(
      "Richten Sie die Kamera auf den Barcode. Kopieren Sie den erkannten"
      " Code und fügen Sie ihn unten ein:"
  )

  scanner_html = """
    <div style="width: 100%; max-width: 450px; margin: auto; text-align: center;">
        <div id="reader" style="width: 100%;"></div>
        <div style="margin-top: 15px; font-size: 18px; font-weight: bold; color: #155724; background: #d4edda; padding: 10px; border-radius: 8px;" id="result">Kamera aktiv – bitte Barcode scannen...</div>
    </div>
    <script src="https://unpkg.com/html5-qrcode"></script>
    <script>
        function playBeep() {
            try {
                let ctx = new (window.AudioContext || window.webkitAudioContext)();
                let osc = ctx.createOscillator();
                let gain = ctx.createGain();
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.type = 'sine';
                osc.frequency.value = 880; 
                gain.gain.setValueAtTime(0.3, ctx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.2);
                osc.start();
                osc.stop(ctx.currentTime + 0.2);
            } catch(e) {}
        }

        function onScanSuccess(decodedText, decodedResult) {
            playBeep();
            document.getElementById('result').innerText = "Erkannt: " + decodedText;
            navigator.clipboard.writeText(decodedText);
        }

        let html5QrcodeScanner = new Html5QrcodeScanner(
            "reader", { fps: 10, qrbox: { width: 250, height: 100 } }, false);
        html5QrcodeScanner.render(onScanSuccess);
    </script>
    """
  components.html(scanner_html, height=430)

  st.write("---")

  with st.form("scan_search_form"):
    scanned_input = st.text_input(
        "Gescannter Barcode (hier einfügen oder tippen):",
        placeholder="Nummer hier einfügen...",
    )
    search_btn = st.form_submit_button("In Datenbank suchen")

  if search_btn and scanned_input:
    if df.empty:
      st.warning("Keine Daten in der Tabelle geladen.")
    else:
      q = str(scanned_input).strip().lower()
      matched_rows = df[
          df["barcode"].astype(str).str.lower().str.contains(q, na=False)
          | df["article"].astype(str).str.lower().str.contains(q, na=False)
          | df["name"].astype(str).str.lower().str.contains(q, na=False)
      ]

      if not matched_rows.empty:
        st.success(f"Gefunden: {len(matched_rows)} Artikel")

        for idx, item in matched_rows.iterrows():
          item_name = item["name"]
          raw_qty = item["quantity"]
          orig_qty = (
              int(raw_qty)
              if pd.notna(raw_qty) and str(raw_qty).isdigit()
              else 0
          )
          item_id = item["id"]
          item_art = item["article"]
          item_bc = item["barcode"]

          st.write(
              f"**{item_name}** | Artikel-Nr: `{item_art}` | Barcode:"
              f" `{item_bc}` | Original-Bestand: **{orig_qty} Stk.**"
          )

          form_key = f"update_form_{item_id}"
          with st.form(form_key):
            change_type = st.radio(
                "Aktion:",
                [
                    "➕ Hinzufügen (Ware zugestellt)",
                    "➖ Abziehen (Verkauf / Entnahme)",
                ],
                key=f"radio_{item_id}",
            )
            delta_qty = st.number_input(
                "Menge:", min_value=1, value=1, step=1, key=f"num_{item_id}"
            )
            submitted_quick = st.form_submit_button("Bestand aktualisieren")

            if submitted_quick:
              if "Hinzufügen" in change_type:
                new_qty = orig_qty + int(delta_qty)
              else:
                new_qty = max(0, orig_qty - int(delta_qty))

              if supabase is not None:
                try:
                  supabase.table("inventory").update({"quantity": new_qty}).eq(
                      "id", item_id
                  ).execute()
                  st.success(
                      f"Erfolgreich aktualisiert! Neuer Bestand: **{new_qty}"
                      " Stk.**"
                  )
                  st.rerun()
                except Exception as e:
                  st.error(f"Fehler beim Aktualisieren: {e}")
              else:
                st.error("Keine Datenbankverbindung.")
          st.write("---")
      else:
        st.warning(
            f"⚠️ Kein Artikel mit dem Barcode '{scanned_input}' in der"
            " Datenbank gefunden."
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

      column_mapping = {
          "Produkt-ID": "article",
          "SAP-Nummer": "sap",
          "Name": "name",
          "Verkaufspreis (EUR)": "preis",
      }
      upload_df = upload_df.rename(columns=column_mapping)

      if (
          len(upload_df.columns) >= 4
          and "article" not in upload_df.columns
      ):
        upload_df.columns = [
            "article",
            "sap",
            "name",
            "preis",
        ] + list(upload_df.columns[4:])

      upload_df = upload_df.replace({np.nan: None})

      st.write("Vorschau (zu importierende Daten):")
      st.dataframe(upload_df.head())

      if st.button("Alles in Supabase-Datenbank hochladen"):
        if supabase is not None:
          try:
            records = upload_df.to_dict(orient="records")
            supabase.table("inventory").insert(records).execute()
            st.success("Erfolgreich importiert!")
            st.rerun()
          except Exception as e:
            st.error(f"Fehler beim Hochladen: {e}")
        else:
          st.error("Keine Verbindung zur Datenbank.")
    except Exception as e:
      st.error(f"Fehler beim Verarbeiten der Datei: {e}")

# 6. ETIKETTEN DRUCKEN
elif action == "🖨 Etiketten drucken":
  st.header("🖨 Preisschilder & Etiketten erstellen")
  st.write(
      "Wählen Sie einen Artikel aus, um ein sauberes Etikett mit Name, Preis,"
      " Artikelnummer und Barcode zum Drucken zu generieren."
  )

  if df.empty:
    st.warning("Keine Artikel in der Datenbank vorhanden.")
  else:
    item_options = df["name"].tolist()
    selected_label_item = st.selectbox(
        "Artikel für Etikett auswählen:", item_options
    )

    # Получаем данные выбранного товара
    item_row = df[df["name"] == selected_label_item].iloc[0]
    l_name = str(item_row.get("name", ""))
    l_brand = str(item_row.get("brand", ""))
    l_article = str(item_row.get("article", ""))
    l_preis = item_row.get("preis", 0.0)
    try:
      l_preis_str = f"{float(l_preis):.2f} €" if pd.notna(l_preis) else "0.00 €"
    except:
      l_preis_str = "0.00 €"

    l_barcode = str(item_row.get("barcode", ""))
    if l_barcode == "nan" or not l_barcode:
      l_barcode = l_article  # резервный вариант для штрихкода

    st.write("---")
    st.subheader("Vorschau des Etiketts:")

    # HTML/CSS шаблон красивого ценника со встроенным генератором штрихкодов
    label_html = f"""
        <div style="width: 320px; border: 2px solid #333; padding: 15px; border-radius: 8px; font-family: Arial, sans-serif; background: #fff; color: #000; text-align: center; margin: auto;">
            <div style="font-size: 12px; font-weight: bold; text-transform: uppercase; color: #555; margin-bottom: 5px;">KaDeWe Berlin — 5. Etage</div>
            <div style="font-size: 14px; font-weight: bold; color: #000; margin-bottom: 2px;">{l_brand}</div>
            <div style="font-size: 16px; font-weight: bold; margin-bottom: 10px; height: 40px; display: flex; align-items: center; justify-content: center;">{l_name}</div>
            <div style="font-size: 24px; font-weight: bold; color: #b00; margin-bottom: 10px;">{l_preis_str}</div>
            <div style="font-size: 11px; margin-bottom: 8px;">Art.-Nr: <b>{l_article}</b></div>
            <div>
                <svg id="barcode_preview"></svg>
            </div>
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.5/dist/JsBarcode.all.min.js"></script>
        <script>
            try {{
                JsBarcode("#barcode_preview", "{l_barcode}", {{
                    format: "CODE128",
                    lineColor: "#000",
                    width: 1.5,
                    height: 40,
                    displayValue: true,
                    fontSize: 12
                }});
            }} catch(e) {{}}
        </script>
        
        <div style="text-align: center; margin-top: 15px;">
            <button onclick="window.print()" style="background-color: #4CAF50; color: white; padding: 10px 20px; font-size: 16px; border: none; border-radius: 5px; cursor: pointer;">🖨 Etikett drucken / Als PDF speichern</button>
        </div>
        
        <style>
            @media print {{
                body * {{
                    visibility: hidden;
                }}
                #print-area, #print-area * {{
                    visibility: visible;
                }}
                #print-area {{
                    position: absolute;
                    left: 0;
                    top: 0;
                }}
            }}
        </style>
        """

    # Оборачиваем в контейнер для печати
    wrapped_html = f'<div id="print-area">{label_html}</div>'
    components.html(wrapped_html, height=320)

# 7. QR-CODE FÜR KOLLEGEN
elif action == "📱 QR-Code für Kollegen":
  st.header("📱 QR-Code für den schnellen Zugriff vom Smartphone")
  app_url = "https://mtcbfvpjnxlkvvtuknyv.streamlit.app"
  encoded_url = urllib.parse.quote(app_url)
  qr_image_url = (
      f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={encoded_url}"
  )

  st.image(qr_image_url, width=300)
  st.info("Rechtsklick -> Bild speichern unter... zum Ausdrucken.")
