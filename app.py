import time
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

# --- ПАРОЛЬ И ТАЙМЕР АКТИВНОСТИ (5 МИНУТ) ---
def check_password():
  TIMEOUT_SECONDS = 300  # 5 минут

  if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False
    st.session_state["last_active"] = time.time()

  if st.session_state["password_correct"]:
    if (
        time.time() - st.session_state.get("last_active", time.time())
        > TIMEOUT_SECONDS
    ):
      st.session_state["password_correct"] = False
      st.warning(
          "⏱️ Sitzung wegen Inaktivität abgelaufen (> 5 Min.). Bitte erneut"
          " anmelden."
      )

  if st.session_state["password_correct"]:
    st.session_state["last_active"] = time.time()
    return True

  st.title("🔐 Lagerverwaltung - Login")
  st.subheader(
      "Bitte geben Sie das Passwort ein (Timeout nach 5 Min. Inaktivität)"
  )

  password = st.text_input("Passwort", type="password")
  if st.button("Anmelden"):
    if password == "kadewe2026":
      st.session_state["password_correct"] = True
      st.session_state["last_active"] = time.time()
      st.rerun()
    else:
      st.error("❌ Falsches Passwort")
  return False


if not check_password():
  st.stop()

# --- ОСНОВНОЙ КОД ПРИЛОЖЕНИЯ ---
st.title("📦 Lagerverwaltung (5. Etage)")
st.subheader("Iittala & Royal Copenhagen")

SUPABASE_URL = "https://mtcbfvpjnxlkvvtuknyv.supabase.co"
SUPABASE_KEY = "sb_publishable_wChGuVU2FeW23S2bqdYqOg_B9-oMoKs"

supabase = None
try:
  supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
  pass


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
    return pd.DataFrame(columns=cols)
  try:
    response = supabase.table("inventory").select("*").execute()
    if response.data is not None:
      df_loaded = pd.DataFrame(response.data)
      if "quantity" in df_loaded.columns:
        df_loaded["quantity"] = (
            pd.to_numeric(df_loaded["quantity"], errors="coerce")
            .fillna(0)
            .astype(int)
        )
      return df_loaded
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


# Функция для отрисовки виджета камеры (исправлены фигурные скобки JS)
def render_camera_scanner_widget(key_suffix=""):
  scanner_html = f"""
    <div style="width: 100%; max-width: 400px; margin: auto; text-align: center; background: #f9f9f9; padding: 10px; border-radius: 8px; border: 1px solid #ddd;">
        <div id="reader_{key_suffix}" style="width: 100%;"></div>
        <div style="margin-top: 10px; font-size: 14px; font-weight: bold; color: #155724; background: #d4edda; padding: 6px; border-radius: 6px;" id="result_{key_suffix}">Kamera bereit...</div>
    </div>
    <script src="https://unpkg.com/html5-qrcode"></script>
    <script>
        function playBeep_{key_suffix}() {{
            try {{
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
            }} catch(e) {{}}
        }}

        function onScanSuccess_{key_suffix}(decodedText, decodedResult) {{
            playBeep_{key_suffix}();
            document.getElementById('result_{key_suffix}').innerText = "Erkannt: " + decodedText;
            navigator.clipboard.writeText(decodedText);
        }}

        const config_{key_suffix} = {{
            fps: 15, 
            qrbox: {{ width: 280, height: 100 }},
            aspectRatio: 1.0,
            formatsToSupport: [
                Html5QrcodeSupportedFormats.EAN_13,
                Html5QrcodeSupportedFormats.EAN_8,
                Html5QrcodeSupportedFormats.CODE_128,
                Html5QrcodeSupportedFormats.UPC_A,
                Html5QrcodeSupportedFormats.UPC_E
            ]
        }};

        let scanner_{key_suffix} = new Html5QrcodeScanner("reader_{key_suffix}", config_{key_suffix}, false);
        scanner_{key_suffix}.render(onScanSuccess_{key_suffix}, (errorMessage) => {{}});
    </script>
    """
  components.html(scanner_html, height=350)


# 1. BESTÄNDE ANZEIGEN
if action == "📊 Bestände anzeigen":
  st.header("📋 Aktuelles Sortiment & Bestände")

  with st.form("search_stock_form"):
    stock_search = st.text_input(
        "🔍 Barcode scannen oder nach Name / SAP suchen:",
        placeholder="Barcode scannen und Enter drücken...",
    )
    stock_submitted = st.form_submit_button("Suchen")

  if stock_submitted or "stock_search_query" not in st.session_state:
    st.session_state["stock_search_query"] = stock_search

  active_stock_search = st.session_state.get("stock_search_query", "")

  if not df.empty and active_stock_search:
    q = active_stock_search.strip().lower()
    filtered_df = df[
        df["name"].astype(str).str.lower().str.contains(q, na=False)
        | df["barcode"].astype(str).str.lower().str.contains(q, na=False)
        | df["article"].astype(str).str.lower().str.contains(q, na=False)
        | df["sap"].astype(str).str.lower().str.contains(q, na=False)
    ]
    st.dataframe(filtered_df, use_container_width=True)
  else:
    st.dataframe(df, use_container_width=True)

# 2. ARTIKEL HINZUFÜGEN
elif action == "➕ Artikel hinzufügen":
  st.header("✨ Neuen Artikel hinzufügen oder Bestand aufstocken")

  with st.expander("📷 Kamera-Scanner öffnen (zum Erfassen des Barcodes)"):
    render_camera_scanner_widget("add")

  with st.form("search_add_form"):
    add_search = st.text_input(
        "🔍 Bestehenden Artikel per Barcode / SAP suchen:",
        placeholder="Barcode eingeben oder scannen...",
    )
    add_submitted = st.form_submit_button("Artikel suchen")

  if add_submitted or "add_search_query" not in st.session_state:
    st.session_state["add_search_query"] = add_search

  active_add_search = st.session_state.get("add_search_query", "")

  pre_article, pre_name, pre_brand, pre_sap, pre_barcode, pre_preis, pre_location = (
      "",
      "",
      "Iittala",
      "",
      "",
      0.0,
      "Etage 5 Lager",
  )

  if active_add_search and not df.empty:
    aq = active_add_search.strip().lower()
    found_items = df[
        df["barcode"].astype(str).str.lower().str.contains(aq, na=False)
        | df["article"].astype(str).str.lower().str.contains(aq, na=False)
        | df["sap"].astype(str).str.lower().str.contains(aq, na=False)
        | df["name"].astype(str).str.lower().str.contains(aq, na=False)
    ]
    if not found_items.empty:
      item = found_items.iloc[0]
      st.success(f"📦 Gefunden: **{item.get('name')}**")
      pre_article, pre_name, pre_brand, pre_sap, pre_barcode, pre_preis, pre_location = (
          str(item.get("article", "")),
          str(item.get("name", "")),
          str(item.get("brand", "Iittala")),
          str(item.get("sap", "")),
          str(item.get("barcode", "")),
          float(item.get("preis", 0.0)),
          str(item.get("location", "Etage 5 Lager")),
      )

  with st.form("add_form"):
    new_article = st.text_input("Artikelnummer / SKU", value=pre_article)
    new_name = st.text_input("Artikelname", value=pre_name)
    brands_list = ["Iittala", "Royal Copenhagen", "Arabia", "Georg Jensen"]
    brand_index = (
        brands_list.index(pre_brand) if pre_brand in brands_list else 0
    )
    new_brand = st.selectbox("Marke", brands_list, index=brand_index)
    new_qty = st.number_input("Menge", min_value=0, value=1, step=1)
    new_location = st.text_input("Lagerort", value=pre_location)
    new_preis = st.number_input(
        "Preis (€)", min_value=0.0, value=pre_preis, format="%.2f"
    )
    new_sap = st.text_input("SAP-Nummer", value=pre_sap)
    new_barcode = st.text_input("Barcode", value=pre_barcode)

    if st.form_submit_button("Speichern / Aktualisieren"):
      if not new_name:
        st.error("Bitte Artikelnamen eingeben.")
      elif supabase is not None:
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
          supabase.table("inventory").upsert(
              data, on_conflict="article"
          ).execute()
          st.success(f"✅ Artikel '{new_name}' gespeichert!")
          st.rerun()
        except Exception as e:
          st.error(f"Fehler: {e}")

# 3. ARTIKEL REDUZIEREN (VERKAUF)
elif action == "📉 Artikel reduzieren (Verkauf)":
  st.header("🛒 Verkauf / Bestandsreduzierung erfassen")

  with st.expander(
      "📷 Kamera-Scanner öffnen (für Direktverkauf per Barcode)"
  ):
    render_camera_scanner_widget("sale")

  with st.form("search_sale_form"):
    sale_search = st.text_input(
        "🔍 Barcode scannen oder nach Name / SAP suchen:",
        placeholder="Barcode eingeben oder scannen...",
    )
    search_submitted = st.form_submit_button("Suchen")

  if search_submitted or "sale_search_query" not in st.session_state:
    st.session_state["sale_search_query"] = sale_search

  active_search = st.session_state.get("sale_search_query", "")

  if df.empty:
    st.warning("Keine Artikel im Lager.")
  else:
    working_df = df
    if active_search:
      sq = active_search.strip().lower()
      working_df = df[
          df["name"].astype(str).str.lower().str.contains(sq, na=False)
          | df["barcode"].astype(str).str.lower().str.contains(sq, na=False)
          | df["sap"].astype(str).str.lower().str.contains(sq, na=False)
          | df["article"].astype(str).str.lower().str.contains(sq, na=False)
      ]

    if working_df.empty:
      st.warning("⚠️ Kein Artikel gefunden.")
    else:
      item_options = [
          f"{r.get('name', 'Unbekannt')} | Barcode: {r.get('barcode', '-')} | SAP: {r.get('sap', '-')} (Bestand: {int(r.get('quantity', 0))} Stk.)"
          for _, r in working_df.iterrows()
      ]

      with st.form("reduce_form"):
        selected_display = st.selectbox(
            "Passenden Artikel auswählen:", item_options
        )
        selected_row = working_df.iloc[item_options.index(selected_display)]
        current_qty = int(float(selected_row.get("quantity", 0)))

        st.info(f"Aktueller Bestand: **{current_qty} Stk.**")
        reduce_qty = st.number_input(
            "Anzahl zum Abziehen:",
            min_value=1,
            max_value=max(1, current_qty),
            value=1,
        )

        if st.form_submit_button("Verkauf bestätigen"):
          new_qty = max(0, current_qty - int(reduce_qty))
          if supabase is not None:
            try:
              supabase.table("inventory").update(
                  {"quantity": int(new_qty)}
              ).eq("id", selected_row["id"]).execute()
              st.success(f"✅ Verkauf erfasst! Neuer Bestand: {new_qty} Stk.")
              st.rerun()
            except Exception as e:
              st.error(f"Fehler: {e}")

# 4. LIVE-KAMERA-SCANNER
elif action == "📷 Live-Kamera-Scanner":
  st.header("📷 Live-Barcode-Scanner für Smartphones")
  render_camera_scanner_widget("main")

  scanned_input = st.text_input(
      "Gescannter Barcode (hier einfügen):", key="scanner_input_field"
  )
  if scanned_input and not df.empty:
    matched = df[
        df["barcode"].astype(str).str.contains(scanned_input.strip(), na=False)
    ]
    if not matched.empty:
      st.success(
          f"Gefunden: {matched.iloc[0]['name']} (Bestand:"
          f" {matched.iloc[0]['quantity']} Stk.)"
      )
    else:
      st.warning("Barcode nicht in der Datenbank gefunden.")

# 5. KATALOG AUS DATEI HOCHLADEN
elif action == "📁 Katalog aus Datei hochladen":
  st.header("📂 Massen-Upload (Excel / CSV)")
  uploaded_file = st.file_uploader(
      "Wählen Sie eine Excel- oder CSV-Datei aus", type=["xlsx", "csv"]
  )
  if uploaded_file is not None:
    try:
      if uploaded_file.name.endswith(".csv"):
        upload_df = pd.read_csv(uploaded_file)
      else:
        upload_df = pd.read_excel(uploaded_file)
      st.write("Vorschau der hochgeladenen Daten:", upload_df.head())
      if st.button("Daten in Supabase importieren"):
        if supabase is not None:
          records = upload_df.to_dict(orient="records")
          supabase.table("inventory").upsert(
              records, on_conflict="article"
          ).execute()
          st.success("✅ Erfolgreich in Supabase importiert!")
          st.rerun()
    except Exception as e:
      st.error(f"Fehler beim Verarbeiten der Datei: {e}")

# 6. ETIKETTEN DRUCKEN
elif action == "🖨 Etiketten drucken":
  st.header("🖨 Etiketten & Preisschilder drucken")
  if df.empty:
    st.warning("Keine Artikel im Bestand.")
  else:
    print_options = [
        f"{r.get('name')} (SAP: {r.get('sap')}) - {r.get('preis')} €"
        for _, r in df.iterrows()
    ]
    selected_to_print = st.selectbox(
        "Artikel für Etikett auswählen:", print_options
    )
    if selected_to_print:
      chosen_item = df.iloc[print_options.index(selected_to_print)]
      st.markdown("---")
      st.subheader("Etiketten-Vorschau:")
      st.markdown(
          f"""
            <div style="border: 2px dashed #333; padding: 20px; width: 300px; text-align: center; background: white; color: black; border-radius: 10px;">
                <h3>{chosen_item.get('brand', 'KaDeWe')}</h3>
                <p><b>{chosen_item.get('name')}</b></p>
                <p>SAP: {chosen_item.get('sap', '-')}</p>
                <h2>{chosen_item.get('preis', 0.0):.2f} €</h2>
                <p><small>Barcode: {chosen_item.get('barcode', '-')}</small></p>
            </div>
            """,
          unsafe_allow_html=True,
      )
      if st.button("Druckansicht öffnen"):
        st.info("Bitte nutzen Sie Strg+P (Cmd+P auf Mac), um das Etikett zu drucken.")

# 7. QR-CODE FÜR KOLLEGEN
elif action == "📱 QR-Code für Kollegen":
  st.header("📱 App-Zugang für das Team")
  st.write(
      "Scannen Sie diesen QR-Code mit einem Smartphone, um direkt zur"
      " Lager-App zu gelangen:"
  )
  app_url = "https://mtcbfvpjnxlkvvtuknyv.streamlit.app"
  qr_code_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={urllib.parse.quote(app_url)}"
  st.image(qr_code_url, width=300)
  st.markdown(f"Direktlink: [{app_url}]({app_url})")
