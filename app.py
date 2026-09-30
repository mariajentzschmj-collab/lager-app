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
    if st.session_state["password"] == "kadewe2026":
      st.session_state["password_correct"] = True
      del st.session_state["password"]
    else:
      st.session_state["password_correct"] = False

  if "password_correct" not in st.session_state:
    st.text_input(
        "🔑 Bitte Passwort eingeben / Введите пароль для доступа к складу:",
        type="password",
        on_change=password_entered,
        key="password",
    )
    return False
  elif not st.session_state["password_correct"]:
    st.text_input(
        "🔑 Bitte Passwort eingeben / Введите пароль для доступа к складу:",
        type="password",
        on_change=password_entered,
        key="password",
    )
    st.error("❌ Falsches Passwort / Неверный пароль")
    return False
  else:
    return True


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
          | df["sap"].astype(str).str.lower().str.contains(q, na=False)
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
    st.warning("Keine Artikel im Lager vorhanden.")
  else:
    st.write(
        "💡 *Sie können den Artikel über den Namen, Barcode oder die"
        " SAP-Nummer suchen und auswählen.*"
    )

    sale_search = st.text_input(
        "🔍 Nach Name, Barcode oder SAP-Nummer filtern:",
        placeholder="Geben Sie Barcode, SAP oder Name ein...",
    )

    working_df = df
    if sale_search:
      sq = sale_search.strip().lower()
      working_df = df[
          df["name"].astype(str).str.lower().str.contains(sq, na=False)
          | df["barcode"].astype(str).str.lower().str.contains(sq, na=False)
          | df["sap"].astype(str).str.lower().str.contains(sq, na=False)
          | df["article"].astype(str).str.lower().str.contains(sq, na=False)
      ]

    if working_df.empty:
      st.warning(
          "⚠️ Kein Artikel gefunden, der den Suchkriterien entspricht."
      )
    else:
      item_options = []
      for idx, row in working_df.iterrows():
        name_val = row.get("name", "Unbekannt")
        barcode_val = row.get("barcode", "-")
        sap_val = row.get("sap", "-")
        qty_val = row.get("quantity", 0)
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
        current_qty = (
            int(raw_qty)
            if pd.notna(raw_qty) and str(raw_qty).isdigit()
            else 0
        )

        st.info(
            f"Ausgewählt: **{selected_item_name}** | Aktueller Lagerbestand:"
            f" **{current_qty} Stk.**"
        )

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
                  "id", item_id
              ).execute()
              st.success(
                  f"Bestand für '{selected_item_name}' aktualisiert! Neuer"
                  f" Bestand: {new_qty} Stk."
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
          | df["sap"].astype(str).str.lower().str.contains(q, na=False)
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
          item_sap = item["sap"]

          st.write(
              f"**{item_name}** | Artikel-Nr: `{item_art}` | SAP: `{item_sap}` |"
              f" Barcode: `{item_bc}` | Original-Bestand: **{orig_qty} Stk.**"
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
            f"⚠️️ Kein Artikel mit dem Suchbegriff '{scanned_input}' in der"
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
      "Wählen Sie einen Artikel aus (über Name, Barcode oder SAP-Nummer), um"
      " ein klares Etikett mit Preis, Artikelnummer und QR-Code zu"
      " generieren."
  )

  if df.empty:
    st.warning("Keine Artikel in der Datenbank vorhanden.")
  else:
    label_search = st.text_input(
        "🔍 Artikel nach Name, Barcode oder SAP-Nummer suchen:",
        placeholder="Geben Sie Barcode, SAP oder Name ein...",
        key="label_search_input",
    )

    label_filtered_df = df
    if label_search:
      lq = label_search.strip().lower()
      label_filtered_df = df[
          df["name"].astype(str).str.lower().str.contains(lq, na=False)
          | df["barcode"].astype(str).str.lower().str.contains(lq, na=False)
          | df["sap"].astype(str).str.lower().str.contains(lq, na=False)
          | df["article"].astype(str).str.lower().str.contains(lq, na=False)
      ]

    if label_filtered_df.empty:
      st.warning(
          "⚠️ Kein Artikel gefunden, der den Suchkriterien entspricht."
      )
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
      l_brand = str(item_row.get("brand", ""))
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
      st.subheader("Vorschau des Etiketts:")

      label_html = f"""
            <div style="width: 340px; border: 2px solid #333; padding: 15px; border-radius: 8px; font-family: Arial, sans-serif; background: #ffffff; color: #000000; text-align: center; margin: auto;">
                <div style="font-size: 11px; font-weight: bold; text-transform: uppercase; color: #555555; margin-bottom: 5px; letter-spacing: 1px;">KaDeWe Berlin — 5. Etage</div>
                <div style="font-size: 13px; font-weight: bold; color: #333333; margin-bottom: 2px; text-transform: uppercase;">{l_brand}</div>
                <div style="font-size: 15px; font-weight: bold; color: #000000; margin-bottom: 10px; min-height: 40px; display: flex; align-items: center; justify-content: center;">{l_name}</div>
                <div style="font-size: 26px; font-weight: bold; color: #000000; margin-bottom: 10px;">{l_preis_str}</div>
                <div style="font-size: 11px; color: #333333; margin-bottom: 8px;">Art.-Nr: <b style="color: #000000;">{l_article}</b></div>
                
                <div style="display: flex; justify-content: space-around; align-items: center; margin-top: 10px; background: #fafafa; padding: 8px; border-radius: 6px;">
                    <div>
                        <svg id="barcode_preview"></svg>
                    </div>
                    <div style="text-align: center;">
                        <div id="qrcode_preview"></div>
                    </div>
                </div>
            </div>
            
            <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.5/dist/JsBarcode.all.min.js"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
            <script>
                try {{
                    JsBarcode("#barcode_preview", "{l_barcode}", {{
                        format: "CODE128",
                        lineColor: "#000000",
                        width: 1.2,
                        height: 38,
                        displayValue: true,
                        fontSize: 10
                    }});
                }} catch(e) {{}}

                try {{
                    document.getElementById("qrcode_preview").innerHTML = "";
                    new QRCode(document.getElementById("qrcode_preview"), {{
                        text: "{l_article} - {l_name}",
                        width: 45,
                        height: 45,
                        colorDark : "#000000",
                        colorLight : "#ffffff",
                        correctLevel : QRCode.CorrectLevel.H
                    }});
                }} catch(e) {{}}
            </script>
            
            <div style="text-align: center; margin-top: 15px;">
                <button onclick="window.print()" style="background-color: #4CAF50; color: white; padding: 10px 20px; font-size: 16px; border: none; border-radius: 5px; cursor: pointer;">🖨 Etikett drucken / PDF</button>
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

      wrapped_html = f'<div id="print-area">{label_html}</div>'
      components.html(wrapped_html, height=360)

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
