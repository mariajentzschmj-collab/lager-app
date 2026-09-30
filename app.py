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
  TIMEOUT_SECONDS = 300  # 5 минут в секундах

  if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False
    st.session_state["last_active"] = time.time()

  # Проверяем, прошло ли более 5 минут с последней активности
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
    # Обновляем время последней активности при каждом действии
    st.session_state["last_active"] = time.time()
    return True

  # Экраны ввода пароля
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

# Подключение к Supabase
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
    st.warning("⚠️ Offline-Modus (keine Verbindung zur Datenbank).")
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

  if df.empty:
    st.info("Das Lager ist leer oder keine Verbindung zur Datenbank möglich.")
  else:
    filtered_df = df
    if active_stock_search:
      q = active_stock_search.strip().lower()
      filtered_df = df[
          df["name"].astype(str).str.lower().str.contains(q, na=False)
          | df["barcode"].astype(str).str.lower().str.contains(q, na=False)
          | df["article"].astype(str).str.lower().str.contains(q, na=False)
          | df["sap"].astype(str).str.lower().str.contains(q, na=False)
      ]
      if len(filtered_df) == 1:
        item = filtered_df.iloc[0]
        st.success(
            f"✨ **Gefunden:** {item['name']} | Preis:"
            f" **{item.get('preis', 0)} €** | Bestand:"
            f" **{item.get('quantity', 0)} Stk.**"
        )

    st.dataframe(filtered_df, use_container_width=True)

# 2. ARTIKEL HINZUFÜGEN
elif action == "➕ Artikel hinzufügen":
  st.header("✨ Neuen Artikel hinzufügen oder Bestand aufstocken")

  with st.form("search_add_form"):
    add_search = st.text_input(
        "🔍 Bestehenden Artikel per Barcode / SAP suchen (zum Aufstocken):",
        placeholder="Barcode scannen...",
    )
    add_submitted = st.form_submit_button("Artikel suchen")

  if add_submitted or "add_search_query" not in st.session_state:
    st.session_state["add_search_query"] = add_search

  active_add_search = st.session_state.get("add_search_query", "")

  pre_article = ""
  pre_name = ""
  pre_brand = "Iittala"
  pre_sap = ""
  pre_barcode = ""
  pre_preis = 0.0
  pre_location = "Etage 5 Lager"

  if active_add_search:
    aq = active_add_search.strip().lower()
    found_items = df[
        df["barcode"].astype(str).str.lower().str.contains(aq, na=False)
        | df["article"].astype(str).str.lower().str.contains(aq, na=False)
        | df["sap"].astype(str).str.lower().str.contains(aq, na=False)
        | df["name"].astype(str).str.lower().str.contains(aq, na=False)
    ]
    if not found_items.empty:
      item = found_items.iloc[0]
      st.success(
          f"📦 Artikel gefunden: **{item.get('name')}** (Aktueller Bestand:"
          f" {item.get('quantity', 0)} Stk.)"
      )
      pre_article = str(item.get("article", ""))
      pre_name = str(item.get("name", ""))
      pre_brand = (
          str(item.get("brand", "Iittala"))
          if item.get("brand")
          in ["Iittala", "Royal Copenhagen", "Arabia", "Georg Jensen"]
          else "Iittala"
      )
      pre_sap = str(item.get("sap", ""))
      pre_barcode = str(item.get("barcode", ""))
      pre_preis = float(item.get("preis", 0.0))
      pre_location = str(item.get("location", "Etage 5 Lager"))

  with st.form("add_form"):
    new_article = st.text_input("Artikelnummer / SKU", value=pre_article)
    new_name = st.text_input(
        "Artikelname (z. B. Iittala Ultima Thule / Royal Copenhagen)",
        value=pre_name,
    )
    new_brand = st.selectbox(
        "Marke",
        ["Iittala", "Royal Copenhagen", "Arabia", "Georg Jensen"],
        index=[
            "Iittala",
            "Royal Copenhagen",
            "Arabia",
            "Georg Jensen",
        ].index(pre_brand),
    )
    new_qty = st.number_input(
        "Hinzuzufügende / Neue Menge", min_value=0, value=1, step=1
    )
    new_location = st.text_input("Lagerort", value=pre_location)
    new_preis = st.number_input(
        "Preis (€)", min_value=0.0, value=pre_preis, format="%.2f"
    )
    new_sap = st.text_input("SAP-Nummer", value=pre_sap)
    new_barcode = st.text_input("Barcode", value=pre_barcode)

    submitted = st.form_submit_button("In Datenbank speichern / Aktualisieren")
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
          supabase.table("inventory").upsert(
              data, on_conflict="article"
          ).execute()
          st.success(
              f"✅ Artikel '{new_name}' erfolgreich gespeichert mit"
              f" **{int(new_qty)} Stk.**!"
          )
          st.session_state["add_search_query"] = ""
          st.rerun()
        except Exception as e:
          st.error(f"Fehler beim Speichern: {e}")

# 3. ARTIKEL REDUZIEREN (VERKAUF)
elif action == "📉 Artikel reduzieren (Verkauf)":
  st.header("🛒 Verkauf / Bestandsreduzierung erfassen")

  with st.form("search_sale_form"):
    sale_search = st.text_input(
        "🔍 Barcode scannen oder nach Name / SAP suchen:",
        placeholder="Barcode scannen und Enter drücken...",
    )
    search_submitted = st.form_submit_button("Suchen")

  if search_submitted or "sale_search_query" not in st.session_state:
    st.session_state["sale_search_query"] = sale_search

  active_search = st.session_state.get("sale_search_query", "")

  if df.empty:
    st.warning("Keine Artikel im Lager vorhanden.")
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
      item_options = []
      for idx, row in working_df.iterrows():
        name_val = row.get("name", "Unbekannt")
        barcode_val = row.get("barcode", "-")
        sap_val = row.get("sap", "-")
        qty_val = (
            int(row.get("quantity", 0)) if pd.notna(row.get("quantity")) else 0
        )
        display_str = (
            f"{name_val} | Barcode: {barcode_val} | SAP: {sap_val} (Bestand:"
            f" {qty_val} Stk.)"
        )
        item_options.append(display_str)

      with st.form("reduce_form"):
        selected_display = st.selectbox(
            "Passenden Artikel auswählen:", item_options
        )
        selected_idx = item_options.index(selected_display)
        selected_row = working_df.iloc[selected_idx]

        item_id = selected_row["id"]
        selected_item_name = selected_row["name"]
        raw_qty = selected_row["quantity"]
        current_qty = int(float(raw_qty)) if pd.notna(raw_qty) else 0

        st.info(
            f"Ausgewählt: **{selected_item_name}** | Aktueller Lagerbestand:"
            f" **{current_qty} Stk.**"
        )

        reduce_qty = st.number_input(
            "Anzahl zum Abziehen (Verkauf):",
            min_value=1,
            max_value=max(1, current_qty),
            value=1,
            step=1,
        )

        submit_reduce = st.form_submit_button("Verkauf bestätigen")
        if submit_reduce:
          new_qty = max(0, current_qty - int(reduce_qty))
          if supabase is not None:
            try:
              supabase.table("inventory").update(
                  {"quantity": int(new_qty)}
              ).eq("id", item_id).execute()
              st.success(
                  f"🛒 Verkauf erfolgreich erfasst! Von '{selected_item_name}'"
                  f" wurden **{int(reduce_qty)} Stk.** abgezogen. Neuer"
                  f" Bestand: **{new_qty} Stk.**"
              )
              st.session_state["sale_search_query"] = ""
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

        const config = {
            fps: 15, 
            qrbox: { width: 320, height: 120 },
            aspectRatio: 1.0,
            formatsToSupport: [
                Html5QrcodeSupportedFormats.EAN_13,
                Html5QrcodeSupportedFormats.EAN_8,
                Html5QrcodeSupportedFormats.CODE_128,
                Html5QrcodeSupportedFormats.UPC_A,
                Html5QrcodeSupportedFormats.UPC_E
            ]
        };

        let html5QrcodeScanner = new Html5QrcodeScanner("reader", config, false);
        html5QrcodeScanner.render(onScanSuccess, (errorMessage) => {});
    </script>
    """
  components.html(scanner_html, height=430)

  st.write("---")

  scanned_input = st.text_input(
      "Gescannter Barcode (hier einfügen oder tippen):",
      placeholder="Nummer hier einfügen...",
      key="scanner_input_field",
  )

  if scanned_input:
    if df.empty:
      st.warning("Keine Daten in der Tabelle geladen.")
    else:
      q = str(scanned_input).strip().lower()
      matched_rows = df[
          df["barcode"].astype(str).str.lower().str.contains(q, na=False)
          | df["article"].astype(str).str.lower().str.contains(q, na=False)
          | df["sap"].astype(str).str.lower().str.contains(q, na=False)
          | df["name"].astype(str).str.lower().str.contains(q, na=False)
      ]

      if not matched_rows.empty:
        st.success(f"Gefunden: {len(matched_rows)} Artikel")

        for idx, item in matched_rows.iterrows():
          item_name = item["name"]
          raw_qty = item["quantity"]
          try:
            orig_qty = int(float(raw_qty)) if pd.notna(raw_qty) else 0
          except:
            orig_qty = 0

          item_id = item["id"]
          item_art = item["article"]
          item_bc = item["barcode"]
          item_sap = item["sap"]

          st.write(
              f"**{item_name}** | Artikel-Nr: `{item_art}` | SAP: `{item_sap}` |"
              f" Barcode: `{item_bc}` | Original-Bestand: **{orig_qty} Stk.**"
          )

          change_type = st.radio(
              "Aktion:",
              [
                  "➕ Hinzufügen (Ware zugestellt)",
                  "➖ Abziehen (Verkauf / Entnahme)",
              ],
              key=f"radio_{item_id}",
          )
          delta_qty = st.number_input(
              "Menge (Stk.):",
              min_value=1,
              value=1,
              step=1,
              key=f"num_{item_id}",
          )

          if st.button("Bestand aktualisieren", key=f"btn_update_{item_id}"):
            d_val = int(delta_qty)
            if "Hinzufügen" in change_type:
              new_qty = orig_qty + d_val
              action_text = f"hinzugefügt (+{d_val} Stk.)"
            else:
              new_qty = max(0, orig_qty - d_val)
              action_text = f"abgezogen (-{d_val} Stk.)"

            if supabase is not None:
              try:
                supabase.table("inventory").update(
                    {"quantity": int(new_qty)}
                ).eq("id", item_id).execute()
                st.success(
                    f"✅ Bestand erfolgreich aktualisiert! Für"
                    f" **{item_name}** wurden {action_text}. Neuer Bestand:"
                    f" **{new_qty} Stk.**"
                )
                st.rerun()
              except Exception as e:
                st.error(f"Fehler beim Aktualisieren: {e}")
            else:
              st.error("Keine Datenbankverbindung.")
          st.write("---")
      else:
        st.warning(
            f"⚠️ Kein Artikel mit dem Suchbegriff '{scanned_input}' gefunden."
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

      upload_df.columns = upload_df.columns.str.strip()
      upload_df = upload_df.loc[
          :, ~upload_df.columns.str.contains("^Unnamed", na=False)
      ]

      column_mapping = {
          "Produkt-ID": "article",
          "SAP-Nummer": "sap",
          "Name": "name",
          "Verkaufspreis (EUR)": "preis",
          "Preis": "preis",
      }
      upload_df = upload_df.rename(columns=column_mapping)

      if "preis " in upload_df.columns:
        upload_df = upload_df.rename(columns={"preis ": "preis"})

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

      if "preis" in upload_df.columns:
        upload_df["preis"] = (
            pd.to_numeric(
                upload_df["preis"].astype(str).str.replace(",", "."),
                errors="coerce",
            )
            .fillna(0.0)
            .astype(float)
        )
      else:
        upload_df["preis"] = 0.0

      if "quantity" in upload_df.columns:
        upload_df["quantity"] = (
            pd.to_numeric(upload_df["quantity"], errors="coerce")
            .fillna(0)
            .astype(int)
        )
      else:
        upload_df["quantity"] = 0

      upload_df = upload_df.replace({np.nan: None})

      if "article" in upload_df.columns:
        before_count = len(upload_df)
        upload_df = upload_df.drop_duplicates(subset=["article"], keep="last")
        after_count = len(upload_df)
        if before_count > after_count:
          st.info(
              f"ℹ️ {before_count - after_count} doppelte Artikel im"
              " Excel-File gefunden und bereinigt."
          )

      st.write("Vorschau (zu importierende Daten):")
      st.dataframe(upload_df.head())

      if st.button("Alles in Supabase-Datenbank hochladen"):
        if supabase is not None:
          try:
            records = upload_df.to_dict(orient="records")
            cleaned_records = [
                {
                    k.strip(): (v if v is not None else "")
                    for k, v in record.items()
                }
                for record in records
            ]

            supabase.table("inventory").upsert(
                cleaned_records, on_conflict="article"
            ).execute()

            st.success(
                "✅ Katalog erfolgreich hochgeladen und aktualisiert!"
            )
          except Exception as e:
            st.error(f"Fehler beim Hochladen: {e}")
        else:
          st.error("Keine Verbindung zur Datenbank.")
    except Exception as e:
      st.error(f"Fehler beim Verarbeiten der Datei: {e}")

# 6. ETIKETTEN DRUCKEN
elif action == "🖨 Etiketten drucken":
  st.header("🖨 Mini-Etikett erstellen (1.4 x 4 cm)")

  with st.form("search_label_form"):
    label_search = st.text_input(
        "🔍 Artikel nach Name, Barcode oder SAP-Nummer suchen:",
        placeholder="Geben Sie Barcode, SAP oder Name ein...",
    )
    label_submitted = st.form_submit_button("Suchen")

  if label_submitted or "label_search_query" not in st.session_state:
    st.session_state["label_search_query"] = label_search

  active_label_search = st.session_state.get("label_search_query", "")

  if df.empty:
    st.warning("Keine Artikel in der Datenbank vorhanden.")
  else:
    label_filtered_df = df
    if active_label_search:
      lq = active_label_search.strip().lower()
      label_filtered_df = df[
          df["name"].astype(str).str.lower().str.contains(lq, na=False)
          | df["barcode"].astype(str).str.lower().str.contains(lq, na=False)
          | df["sap"].astype(str).str.lower().str.contains(lq, na=False)
          | df["article"].astype(str).str.lower().str.contains(lq, na=False)
      ]

    if label_filtered_df.empty:
      st.warning("⚠️ Kein Artikel gefunden.")
    else:
      label_options = []
      for idx, row in label_filtered_df.iterrows():
        name_val = row.get("name", "Unbekannt")
        barcode_val = row.get("barcode", "-")
        sap_val = row.get("sap", "-")
        article_val = row.get("article", "-")
        display_str = (
            f"{name_val} | Art-Nr: {article_val} | Barcode: {barcode_val} |"
            f" SAP: {sap_val}"
        )
        label_options.append(display_str)

      selected_label_display = st.selectbox(
          "Passenden Artikel für Etikett auswählen:", label_options
      )
      selected_label_idx = label_options.index(selected_label_display)
      item_row = label_filtered_df.iloc[selected_label_idx]

      l_name = str(item_row.get("name", ""))
      l_article = str(item_row.get("article", ""))
      l_preis = item_row.get("preis", 0.0)
      try:
        l_preis_str = (
            f"{float(l_preis):.2f} €" if pd.notna(l_preis) else "0.00 €"
        )
      except:
        l_preis_str = "0.00 €"

      l_barcode = str(item_row.get("barcode", ""))
      if l_barcode == "nan" or not l_barcode:
        l_barcode = l_article

      st.write("---")
      st.subheader("Vorschau des Mini-Etiketts (40 x 14 mm):")

      label_html = f"""
            <div style="width: 40mm; height: 14mm; box-sizing: border-box; border: 1px solid #000; padding: 1mm 2mm; font-family: Arial, sans-serif; background: #ffffff; color: #000000; display: flex; flex-direction: column; justify-content: space-between; overflow: hidden; margin: auto;">
                <div style="display: flex; justify-content: space-between; align-items: center; font-size: 8px; font-weight: bold; line-height: 1;">
                    <span style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 25mm;">{l_name}</span>
                    <span style="font-size: 9px; color: #000;">{l_preis_str}</span>
                </div>
                <div style="text-align: center; line-height: 1;">
                    <svg id="barcode_preview" style="max-height: 8mm;"></svg>
                </div>
            </div>
            
            <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.5/dist/JsBarcode.all.min.js"></script>
            <script>
                try {{
                    JsBarcode("#barcode_preview", "{l_barcode}", {{
                        format: "CODE128",
                        lineColor: "#000000",
                        width: 1,
                        height: 22,
                        displayValue: true,
                        fontSize: 7,
                        margin: 0
                    }});
                }} catch(e) {{}}
            </script>
            
            <div style="text-align: center; margin-top: 15px;">
                <button onclick="window.print()" style="background-color: #4CAF50; color: white; padding: 8px 16px; font-size: 14px; border: none; border-radius: 4px; cursor: pointer;">🖨 Etikett drucken (40x14mm)</button>
            </div>
            
            <style>
                @media print {{
                    @page {{
                        size: 40mm 14mm;
                        margin: 0;
                    }}
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
                        width: 40mm;
                        height: 14mm;
                    }}
                }}
            </style>
            """
      components.html(
          f'<div id="print-area">{label_html}</div>', height=120
      )

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
