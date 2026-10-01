import io
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
      if "preis" in df_loaded.columns:
        df_loaded["preis"] = pd.to_numeric(
            df_loaded["preis"], errors="coerce"
        ).fillna(0.0)
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


# Функция для универсального поиска по DataFrame (Name, Article, SAP, Barcode)
def search_items(dataframe, query):
  if dataframe.empty or not query:
    return dataframe
  q = str(query).strip().lower()
  mask = (
      dataframe["name"].astype(str).str.lower().str.contains(q, na=False)
      | dataframe["barcode"].astype(str).str.lower().str.contains(q, na=False)
      | dataframe["sap"].astype(str).str.lower().str.contains(q, na=False)
      | dataframe["article"].astype(str).str.lower().str.contains(q, na=False)
  )
  return dataframe[mask]


# Функция для отрисовки виджета камеры
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
  st.header("📋 Aktuelles Sortiment & Bestände (inkl. 0 Stk.)")

  col1, col2 = st.columns([2, 1])
  with col1:
    stock_search = st.text_input(
        "🔍 Suche (Name, Artikel, SAP, Barcode):",
        placeholder="Suchbegriff eingeben...",
    )
  with col2:
    brand_filter = st.selectbox(
        "Nach Marke filtern:",
        ["Alle Marken", "Iittala", "Royal Copenhagen", "Arabia", "Georg Jensen"],
    )

  filtered_df = df.copy()

  if brand_filter != "Alle Marken":
    filtered_df = filtered_df[
        filtered_df["brand"].astype(str).str.lower()
        == brand_filter.lower()
    ]

  if stock_search:
    filtered_df = search_items(filtered_df, stock_search)

  if not filtered_df.empty:
    total_items = filtered_df["quantity"].sum()
    total_value = (filtered_df["quantity"] * filtered_df["preis"]).sum()

    m1, m2, m3 = st.columns(3)
    m1.metric("📦 Artikelarten", len(filtered_df))
    m2.metric("🔢 Gesamtstückzahl", int(total_items))
    m3.metric("💶 Gesamtwert (Bestand)", f"{total_value:,.2f} €")
  else:
    st.info("Keine Artikel im Lager gefunden.")

  st.markdown("---")
  st.dataframe(filtered_df, use_container_width=True)

  if not filtered_df.empty:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
      filtered_df.to_excel(writer, index=False, sheet_name="Bestand")
    excel_data = output.getvalue()

    st.download_button(
        label="📥 Gefilterten Bestand als Excel herunterladen",
        data=excel_data,
        file_name="KaDeWe_Bestand.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )

# 2. ARTIKEL HINZUFÜGEN
elif action == "➕ Artikel hinzufügen":
  st.header("✨ Neuen Artikel hinzufügen oder Bestand anpassen (auch 0)")

  with st.form("search_add_form"):
    add_search = st.text_input(
        "🔍 Artikel suchen (Name, Artikel, SAP oder Barcode):",
        placeholder="Eingeben...",
    )
    add_submitted = st.form_submit_button("Artikel suchen")

  if add_submitted or "add_search_query" not in st.session_state:
    st.session_state["add_search_query"] = add_search

  active_add_search = st.session_state.get("add_search_query", "")

  pre_article, pre_name, pre_brand, pre_sap, pre_barcode, pre_preis, pre_location, pre_qty = (
      "",
      "",
      "Iittala",
      "",
      "",
      0.0,
      "Etage 5 Lager",
      0,
  )

  if active_add_search and not df.empty:
    found_items = search_items(df, active_add_search)
    if not found_items.empty:
      item = found_items.iloc[0]
      st.success(
          f"📦 Gefunden: **{item.get('name')}** (Aktueller Bestand:"
          f" **{int(item.get('quantity', 0))} Stk.**)"
      )
      pre_article, pre_name, pre_brand, pre_sap, pre_barcode, pre_preis, pre_location, pre_qty = (
          str(item.get("article", "")),
          str(item.get("name", "")),
          str(item.get("brand", "Iittala")),
          str(item.get("sap", "")),
          str(item.get("barcode", "")),
          float(item.get("preis", 0.0)),
          str(item.get("location", "Etage 5 Lager")),
          int(item.get("quantity", 0)),
      )

  with st.form("add_form"):
    new_article = st.text_input("Artikelnummer / SKU", value=pre_article)
    new_name = st.text_input("Artikelname", value=pre_name)
    brands_list = ["Iittala", "Royal Copenhagen", "Arabia", "Georg Jensen"]
    brand_index = (
        brands_list.index(pre_brand) if pre_brand in brands_list else 0
    )
    new_brand = st.selectbox("Marke", brands_list, index=brand_index)
    new_qty = st.number_input(
        "Menge (auch 0)", min_value=0, value=pre_qty, step=1
    )
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
          st.success(
              f"✅ Artikel '{new_name}' (Menge: {new_qty} Stk.) erfolgreich"
              " gespeichert!"
          )
          st.rerun()
        except Exception as e:
          st.error(f"Fehler: {e}")

# 3. ARTIKEL REDUZIEREN (VERKAUF)
elif action == "📉 Artikel reduzieren (Verkauf)":
  st.header("🛒 Verkauf / Bestandsreduzierung erfassen")

  with st.form("search_sale_form"):
    sale_search = st.text_input(
        "🔍 Suche (Name, Artikel, SAP, Barcode):",
        placeholder="Suchbegriff eingeben...",
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
      working_df = search_items(df, active_search)

    if working_df.empty:
      st.warning("⚠️ Kein Artikel gefunden.")
    else:
      item_options = [
          f"{r.get('name', 'Unbekannt')} | Art: {r.get('article', '-')} | SAP: {r.get('sap', '-')} | Barcode: {r.get('barcode', '-')} (Bestand: {int(r.get('quantity', 0))} Stk.)"
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
              st.success(
                  f"✅ Verkauf erfasst! Neuer Bestand: {new_qty} Stk. (wર્ડ"
                  " im System behalten)"
              )
              st.rerun()
            except Exception as e:
              st.error(f"Fehler: {e}")

# 4. LIVE-KAMERA-SCANNER
elif action == "📷 Live-Kamera-Scanner":
  st.header("📷 Live-Barcode-Scanner (Bestand anpassen)")
  render_camera_scanner_widget("main")

  st.markdown("---")
  scanned_input = st.text_input(
      "Gescannter Barcode, SAP-Nummer, Artikel oder Name manuell eingeben:",
      key="scanner_input_field",
  )

  if scanned_input and not df.empty:
    matched = search_items(df, scanned_input)

    if not matched.empty:
      item = matched.iloc[0]
      item_name = item.get("name", "Unbekannt")
      current_qty = int(float(item.get("quantity", 0)))
      item_brand = item.get("brand", "-")
      item_preis = float(item.get("preis", 0.0))
      item_sap = item.get("sap", "-")
      item_barcode = item.get("barcode", "-")
      item_article = item.get("article", "-")

      st.success(f"📦 Gefunden: **{item_name}** ({item_brand})")

      col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
      col_m1.metric("📊 Bestand", f"{current_qty} Stk.")
      col_m2.metric("💶 Preis", f"{item_preis:.2f} €")
      col_m3.metric("🏷 SAP", f"{item_sap}")
      col_m4.metric("📟 Barcode", f"{item_barcode}")
      col_m5.metric("📋 Art.-Nr.", f"{item_article}")

      st.markdown("### Bestandsänderung:")
      with st.form("camera_update_qty_form"):
        change_type = st.radio(
            "Aktion wählen:", ["➕ Bestand hinzufügen", "➖ Bestand reduzieren"]
        )
        delta_qty = st.number_input(
            "Anzahl der Stück:", min_value=1, value=1, step=1
        )

        if st.form_submit_button("Bestand aktualisieren"):
          if "hinzufügen" in change_type.lower():
            new_qty = current_qty + int(delta_qty)
          else:
            new_qty = max(0, current_qty - int(delta_qty))

          if supabase is not None:
            try:
              supabase.table("inventory").update(
                  {"quantity": int(new_qty)}
              ).eq("id", item["id"]).execute()
              st.success(
                  f"✅ Bestand erfolgreich aktualisiert! Neuer Bestand:"
                  f" {new_qty} Stk."
              )
              st.rerun()
            except Exception as e:
              st.error(f"Fehler beim Speichern: {e}")
    else:
      st.warning(
          "⚠️ Artikel mit diesem Barcode / SAP / Artikel / Suchbegriff wurde"
          " in der Datenbank nicht gefunden."
      )

# 5. KATALOG AUS DATEI HOCHLADEN
elif action == "📁 Katalog aus Datei hochladen":
  st.header("📂 Massen-Upload (Excel / CSV) — Alle Artikel inkl. 0 Stk.")
  uploaded_file = st.file_uploader(
      "Wählen Sie eine Excel- oder CSV-Datei aus", type=["xlsx", "csv"]
  )
  if uploaded_file is not None:
    try:
      if uploaded_file.name.endswith(".csv"):
        upload_df = pd.read_csv(uploaded_file)
      else:
        upload_df = pd.read_excel(uploaded_file)

      if "article" in upload_df.columns:
        duplicates_series = upload_df[
            upload_df.duplicated(subset=["article"], keep=False)
        ]

        if not duplicates_series.empty:
          dup_counts = duplicates_series["article"].value_counts()
          st.warning(
              f"⚠️ В загруженном файле обнаружены повторяющиеся артикулы"
              f" ({len(duplicates_series)} строк всего с дубликатами):"
          )
          dup_info_df = pd.DataFrame(
              {
                  "Артикул (article)": dup_counts.index,
                  "Количество повторов в файле": dup_counts.values,
              }
          )
          st.dataframe(dup_info_df, use_container_width=True)
          st.info(
              "ℹ️ При импорте дубликаты автоматически объединяются (берется"
              " последняя запись из файла для каждого артикула)."
          )

        upload_df = upload_df.drop_duplicates(subset=["article"], keep="last")

      st.write("Vorschau der bereinigten Daten:", upload_df.head())

      if st.button("Daten in Supabase importieren"):
        if supabase is not None:
          # Безопасное преобразование количеств (если в файле пусто, ставится 0, товар не удаляется)
          upload_df["quantity"] = (
              pd.to_numeric(upload_df.get("quantity", 0), errors="coerce")
              .fillna(0)
              .astype(int)
          )
          upload_df["preis"] = pd.to_numeric(
              upload_df.get("preis", 0.0), errors="coerce"
          ).fillna(0.0)

          for col in ["article", "name", "brand", "location", "sap", "barcode"]:
            if col in upload_df.columns:
              upload_df[col] = upload_df[col].fillna("").astype(str)
            else:
              upload_df[col] = ""

          records = upload_df.to_dict(orient="records")

          try:
            supabase.table("inventory").upsert(
                records, on_conflict="article"
            ).execute()
            st.success(
                "✅ Erfolgreich in Supabase importiert! Alle Artikel (auch mit"
                " 0 Bestand) sind im System."
            )
            st.rerun()
          except Exception as e:
            st.error(f"Fehler beim Import: {e}")

    except Exception as e:
      st.error(f"Fehler beim Verarbeiten der Datei: {e}")

# 6. ETIKETTEN DRUCKEN
elif action == "🖨 Etiketten drucken":
  st.header("🖨 Etiketten & Preisschilder drucken")
  if df.empty:
    st.warning("Keine Artikel im Bestand.")
  else:
    print_options = [
        f"{r.get('name')} | Art: {r.get('article')} | SAP: {r.get('sap')} | Barcode: {r.get('barcode')} (Bestand: {int(r.get('quantity', 0))} Stk.)"
        for _, r in df.iterrows()
    ]
    selected_to_print = st.selectbox(
        "Artikel für Etikett auswählen:", print_options
    )
    if selected_to_print:
      chosen_item = df.iloc[print_options.index(selected_to_print)]

      raw_bc = str(chosen_item.get("barcode", ""))
      if not raw_bc or raw_bc == "nan":
        raw_bc = str(chosen_item.get("sap", ""))
      if not raw_bc or raw_bc == "nan":
        raw_bc = str(chosen_item.get("article", ""))
      if not raw_bc or raw_bc == "nan":
        raw_bc = "12345678"

      barcode_url = f"https://barcodeapi.org/api/128/{urllib.parse.quote(raw_bc)}"

      st.markdown("---")
      st.subheader("Etiketten-Vorschau (Höhe 1.5 cm × Breite 4 cm):")
      st.markdown(
          f"""
            <div style="border: 2px dashed #333; width: 4cm; height: 1.5cm; padding: 2px; box-sizing: border-box; background: white; color: black; border-radius: 2px; display: flex; flex-direction: column; justify-content: space-between; overflow: hidden;">
                <div style="display: flex; justify-content: space-between; font-size: 6px; font-weight: bold; padding: 0 1px;">
                    <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 65%;">{chosen_item.get('name')}</span>
                    <span><b>{chosen_item.get('preis', 0.0):.2f} €</b></span>
                </div>
                <div style="text-align: center; flex-grow: 1; display: flex; align-items: center; justify-content: center; margin: 1px 0;">
                    <img src="{barcode_url}" style="height: 0.75cm; width: 98%; object-fit: fill;" />
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 5.5px; color: #555; padding: 0 1px;">
                    <span>{chosen_item.get('brand', 'KaDeWe')}</span>
                    <span>SAP: {chosen_item.get('sap', '-')}</span>
                </div>
            </div>
            """,
          unsafe_allow_html=True,
      )
      if st.button("Druckansicht öffnen"):
        st.info(
            "Bitte nutzen Sie Strg+P (Cmd+P auf Mac), um das Etikett zu drucken."
        )

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
