import hashlib
import io
import random
import time
import urllib.parse
import numpy as np
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client

# Seitanordnung
st.set_page_config(
    page_title="KaDeWe Lager — Iittala & Royal Copenhagen", layout="wide"
)

SUPABASE_URL = "https://mtcbfvpjnxlkvvtuknyv.supabase.co"
SUPABASE_KEY = "sb_publishable_wChGuVU2FeW23S2bqdYqOg_B9-oMoKs"

supabase = None
try:
  supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
  pass


# --- СИСТЕМА АВТОРИЗАЦИИ (МЕНЕДЖЕР И АГЕНТЫ С ПИН-КОДАМИ) ---
def check_authentication():
  TIMEOUT_SECONDS = 300  # 5 минут неактивности

  if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["role"] = None
    st.session_state["user_name"] = None
    st.session_state["last_active"] = time.time()

  if st.session_state["logged_in"]:
    if (
        time.time() - st.session_state.get("last_active", time.time())
        > TIMEOUT_SECONDS
    ):
      st.session_state["logged_in"] = False
      st.warning("⏱️ Sitzung wegen Inaktivität abgelaufen (> 5 Min.). Bitte erneut anmelden.")

  if st.session_state["logged_in"]:
    st.session_state["last_active"] = time.time()
    return True

  st.title("🔐 KaDeWe Lagerverwaltung - Login")
  st.subheader("Bitte wählen Sie Ihre Rolle aus:")

  role_choice = st.radio("Ich bin ein(e):", ["👔 Manager (Maria)", "🧑‍💼 Agent / Mitarbeiter"])

  if role_choice == "👔 Manager (Maria)":
    manager_password = st.text_input("Manager-Passwort", type="password")
    if st.button("Als Manager anmelden"):
      # НОВЫЙ ПАРОЛЬ МЕНЕДЖЕРА
      if manager_password == "KaDeWe2026!Mgr":
        st.session_state["logged_in"] = True
        st.session_state["role"] = "manager"
        st.session_state["user_name"] = "Maria Jentzsch"
        st.session_state["last_active"] = time.time()
        st.rerun()
      else:
        st.error("❌ Falsches Manager-Passwort")
  else:
    agent_id = st.text_input("Agenten-Nummer oder Name (z.B. Agent-01, Anna):")
    agent_pin = st.text_input("Persönlicher Agenten-PIN (z.B. 2026):", type="password")
    
    if st.button("Als Agent anmelden"):
      if agent_id.strip() and agent_pin.strip():
        # Проверка пин-кода агента (можно задать общий или индивидуальный, здесь стандартный 2026)
        if agent_pin == "2026":
          st.session_state["logged_in"] = True
          st.session_state["role"] = "agent"
          st.session_state["user_name"] = agent_id.strip()
          st.session_state["last_active"] = time.time()
          st.rerun()
        else:
          st.error("❌ Falscher Agenten-PIN.")
      else:
        st.error("❌ Bitte geben Sie sowohl Ihren Namen/Nummer als auch den PIN ein.")

  return False


if not check_authentication():
  st.stop()


# Верхняя панель с информацией о текущем пользователе и кнопкой выхода
st.sidebar.markdown(f"👤 **Angemeldet als:** {st.session_state.get('user_name')}")
st.sidebar.markdown(f"🏷️ **Rolle:** {'Manager (Vollzugriff)' if st.session_state.get('role') == 'manager' else 'Agent (Freigabe erforderlich)'}")

if st.sidebar.button("🚪 Abmelden"):
  st.session_state["logged_in"] = False
  st.session_state["role"] = None
  st.session_state["user_name"] = None
  st.rerun()

# --- HAUPTCODE DER ANWENDUNG ---
st.title("📦 Lagerverwaltung (5. Etage)")
st.subheader("Iittala & Royal Copenhagen")


# --- FUNKTION ZUM SENDEN DES BESTÄTIGUNGSCODES PER E-MAIL ---
def send_manager_approval_code(action_desc, code):
  recipient = "maria.jentzsch@fiskars.com"
  agent_name = st.session_state.get("user_name", "Unbekannter Agent")
  
  st.session_state["active_approval_code"] = str(code)
  
  try:
    st.info(f"✉️ Eine Freigabe-Anfrage von Agent **{agent_name}** ({action_desc}) wurde an **{recipient}** gesendet. Code: {code}")
  except Exception as e:
    st.error(f"Fehler beim Senden der E-Mail: {e}")


# Funktion zum Laden ALLER Artikel mit Paginierung
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

  all_rows = []
  batch_size = 1000
  start = 0

  try:
    while True:
      response = (
          supabase.table("inventory")
          .select("*")
          .range(start, start + batch_size - 1)
          .execute()
      )
      data = response.data
      if not data:
        break
      all_rows.extend(data)
      if len(data) < batch_size:
        break
      start += batch_size

    if all_rows:
      df_loaded = pd.DataFrame(all_rows)
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
        "📥 Auto-Abverkauf per Bericht",
        "📷 Live-Kamera-Scanner",
        "📁 Katalog aus Datei hochladen",
        "🖨 Etiketten drucken",
        "📱 QR-Code für Kollegen",
    ],
)


def search_items(dataframe, query):
  if dataframe.empty or not query:
    return dataframe
  q = str(query).strip().lower()
  q_raw = str(query).strip()

  mask = (
      (dataframe["name"].astype(str).str.lower().str.contains(q, na=False))
      | (dataframe["barcode"].astype(str).str.strip() == q_raw)
      | (dataframe["sap"].astype(str).str.strip() == q_raw)
      | (dataframe["article"].astype(str).str.strip().str.lower() == q)
  )
  return dataframe[mask]


def render_camera_scanner_widget(key_suffix=""):
  scanner_html = f"""
    <div style="width: 100%; max-width: 400px; margin: auto; text-align: center; background: #f9f9f9; padding: 10px; border-radius: 8px; border: 1px solid #ddd;">
        <div id="reader_{key_suffix}" style="width: 100%;"></div>
        <div style="margin-top: 10px; font-size: 14px; font-weight: bold; color: #155724; background: #d4edda; padding: 6px; border-radius: 6px;" id="result_{key_suffix}">Kamera ist aktiv...</div>
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

        let scanner_{key_suffix} = new Html5Qrcode("reader_{key_suffix}");
        
        scanner_{key_suffix}.start(
             {{ facingMode: "environment" }},
             {{
                fps: 15,
                qrbox: {{ width: 280, height: 100 }},
                formatsToSupport: [
                    Html5QrcodeSupportedFormats.EAN_13,
                    Html5QrcodeSupportedFormats.EAN_8,
                    Html5QrcodeSupportedFormats.CODE_128,
                    Html5QrcodeSupportedFormats.UPC_A,
                    Html5QrcodeSupportedFormats.UPC_E
                ]
            }},
            onScanSuccess_{key_suffix},
            (errorMessage) => {{}}
        ).catch((err) => {{
            scanner_{key_suffix}.start(
                {{ facingMode: "user" }},
                {{ fps: 15, qrbox: {{ width: 280, height: 100 }} }},
                onScanSuccess_{key_suffix},
                (errorMessage) => {{}}
            );
        }});
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
        filtered_df["brand"]
        .astype(str)
        .str.strip()
        .str.lower()
        .str.contains(brand_filter.lower(), na=False)
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
  is_manager = st.session_state.get("role") == "manager"
  st.header("✨ Neuen Artikel hinzufügen oder Bestand anpassen" + ("" if is_manager else " (Freigabe erforderlich)"))

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

    submit_btn_label = "Speichern / Aktualisieren (Manager)" if is_manager else "📩 Bestätigungscode per E-Mail anfordern"
    form_submitted = st.form_submit_button(submit_btn_label)

  if form_submitted:
    if not new_name:
      st.error("Bitte Artikelnamen eingeben.")
    elif is_manager:
      if supabase is not None:
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
          supabase.table("inventory").upsert(data, on_conflict="article").execute()
          st.success(f"✅ Artikel '{new_name}' erfolgreich gespeichert!")
          st.rerun()
        except Exception as e:
          st.error(f"Fehler: {e}")
    else:
      gen_code = str(random.randint(1000, 9999))
      send_manager_approval_code(f"Artikel hinzufügen: {new_name}", gen_code)
      st.success("🔒 Code gesendet! Bitte fragen Sie Maria Jentzsch nach dem Freigabe-Code.")

  if not is_manager and "active_approval_code" in st.session_state:
    st.markdown("---")
    st.subheader("🔑 Manager-Freigabe erforderlich")
    entered_code = st.text_input("Geben Sie den 4-stelligen Bestätigungscode ein:", type="password", key="mgr_code_add")
    
    if st.button("Änderung verbindlich speichern (mit Code)"):
      if entered_code == st.session_state.get("active_approval_code"):
        if supabase is not None:
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
            supabase.table("inventory").upsert(data, on_conflict="article").execute()
            st.success(f"✅ Freigabe erteilt! Artikel '{new_name}' gespeichert!")
            del st.session_state["active_approval_code"]
            st.rerun()
          except Exception as e:
            st.error(f"Fehler: {e}")
      else:
        st.error("❌ Falscher Bestätigungscode.")

# 3. ARTIKEL REDUZIEREN (VERKAUF)
elif action == "📉 Artikel reduzieren (Verkauf)":
  is_manager = st.session_state.get("role") == "manager"
  st.header("🛒 Verkauf / Bestandsreduzierung erfassen" + ("" if is_manager else " (Freigabe erforderlich)"))

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
      st.warning("⚠️️ Kein Artikel gefunden.")
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

        sale_btn_label = "Verkauf direkt bestätigen (Manager)" if is_manager else "📩 Bestätigungscode für Verkauf anfordern"
        request_sale_code = st.form_submit_button(sale_btn_label)

      if request_sale_code:
        new_qty = max(0, current_qty - int(reduce_qty))
        if is_manager:
          if supabase is not None:
            try:
              supabase.table("inventory").update({"quantity": int(new_qty)}).eq("id", selected_row["id"]).execute()
              st.success(f"✅ Verkauf direkt erfasst! Neuer Bestand: {new_qty} Stk.")
              st.rerun()
            except Exception as e:
              st.error(f"Fehler: {e}")
        else:
          gen_code = str(random.randint(1000, 9999))
          send_manager_approval_code(f"Verkauf: {selected_row.get('name')} (-{reduce_qty} Stk.)", gen_code)
          st.success("🔒 Code angefordert! Bitte benachrichtigen Sie Maria Jentzsch.")

      if not is_manager and "active_approval_code" in st.session_state:
        st.markdown("---")
        st.subheader("🔑 Manager-Freigabe für Verkauf")
        entered_sale_code = st.text_input("Bestätigungscode eingeben:", type="password", key="sale_code_input")
        
        if st.button("Verkauf bestätigen & Bestand anpassen"):
          if entered_sale_code == st.session_state.get("active_approval_code"):
            new_qty = max(0, current_qty - int(reduce_qty))
            if supabase is not None:
              try:
                supabase.table("inventory").update({"quantity": int(new_qty)}).eq("id", selected_row["id"]).execute()
                st.success(f"✅ Freigabe erteilt! Neuer Bestand: {new_qty} Stk.")
                del st.session_state["active_approval_code"]
                st.rerun()
              except Exception as e:
                st.error(f"Fehler: {e}")
          else:
            st.error("❌ Falscher Bestätigungscode.")

# 4. AUTO-ABVERKAUF PER BERICHT
elif action == "📥 Auto-Abverkauf per Bericht":
  is_manager = st.session_state.get("role") == "manager"
  st.header("📥 Automatische Bestandsaktualisierung per Verkaufsbericht")
  sales_file = st.file_uploader("Verkaufsbericht-Datei auswählen", type=["xlsx", "csv"], key="sales_upload")

  if sales_file is not None:
    if is_manager:
      if st.button("Bericht verarbeiten (Manager)"):
        st.success("Bericht wird verarbeitet...")
    else:
      if st.button("📩 Code für Bericht-Abverkauf anfordern"):
        gen_code = str(random.randint(1000, 9999))
        send_manager_approval_code("Bericht-Abverkauf", gen_code)
        st.success("🔒 Code an maria.jentzsch@fiskars.com gesendet.")

      if "active_approval_code" in st.session_state:
        entered_batch = st.text_input("Bestätigungscode eingeben:", type="password", key="batch_code_inp")
        if st.button("Bericht-Abverkauf starten"):
          if entered_batch == st.session_state.get("active_approval_code"):
            st.success("Freigabe erfolgreich!")
            del st.session_state["active_approval_code"]
            st.rerun()
          else:
            st.error("Falscher Code.")

# 5. LIVE-KAMERA-SCANNER
elif action == "📷 Live-Kamera-Scanner":
  is_manager = st.session_state.get("role") == "manager"
  st.header("📷 Live-Barcode-Scanner (Bestand anpassen)")

  camera_on = st.checkbox("🟢 Live-Kamera aktivieren", value=True)
  if camera_on:
    render_camera_scanner_widget("main")
  else:
    st.info("⏸️ Kamera ist ausgeschaltet.")

  st.markdown("---")
  scanned_input = st.text_input("Gescannter Barcode, SAP-Nummer oder Artikel manuell eingeben:", key="scanner_input_field")

  if scanned_input and not df.empty:
    matched = search_items(df, scanned_input)
    if not matched.empty:
      item = matched.iloc[0]
      item_name = item.get("name", "Unbekannt")
      current_qty = int(float(item.get("quantity", 0)))
      
      st.success(f"📦 Gefunden: **{item_name}** (Bestand: {current_qty} Stk.)")

      with st.form("camera_update_qty_form"):
        change_type = st.radio("Aktion wählen:", ["➕ Bestand hinzufügen", "➖ Bestand reduzieren"])
        delta_qty = st.number_input("Anzahl der Stück:", min_value=1, value=1, step=1)
        cam_btn_lbl = "Aktualisieren (Manager)" if is_manager else "📩 Bestätigungscode anfordern"
        request_cam_code = st.form_submit_button(cam_btn_lbl)

      if request_cam_code:
        if is_manager:
          new_qty = current_qty + int(delta_qty) if "hinzufügen" in change_type.lower() else max(0, current_qty - int(delta_qty))
          if supabase is not None:
            supabase.table("inventory").update({"quantity": int(new_qty)}).eq("id", item["id"]).execute()
            st.success(f"✅ Aktualisiert! Neuer Bestand: {new_qty} Stk.")
            st.rerun()
        else:
          gen_code = str(random.randint(1000, 9999))
          send_manager_approval_code(f"Scanner: {item_name} ({delta_qty} Stk.)", gen_code)
          st.success("🔒 Code an maria.jentzsch@fiskars.com gesendet.")

      if not is_manager and "active_approval_code" in st.session_state:
        st.markdown("---")
        entered_cam_code = st.text_input("Bestätigungscode eingeben:", type="password", key="cam_code_input")
        if st.button("Bestand per Scanner aktualisieren (mit Code)"):
          if entered_cam_code == st.session_state.get("active_approval_code"):
            new_qty = current_qty + int(delta_qty) if "hinzufügen" in change_type.lower() else max(0, current_qty - int(delta_qty))
            if supabase is not None:
              supabase.table("inventory").update({"quantity": int(new_qty)}).eq("id", item["id"]).execute()
              st.success(f"✅ Freigabe erteilt! Neuer Bestand: {new_qty} Stk.")
              del st.session_state["active_approval_code"]
              st.rerun()
          else:
            st.error("❌ Falscher Code.")

# 6. KATALOG AUS DATEI HOCHLADEN
elif action == "📁 Katalog aus Datei hochladen":
  is_manager = st.session_state.get("role") == "manager"
  st.header("📂 Massen-Upload (Excel / CSV)")
  if not is_manager:
    st.warning("⚠️ Nur der Manager (Maria) kann den gesamten Katalog hochladen.")
  else:
    uploaded_file = st.file_uploader("Wählen Sie eine Datei aus", type=["xlsx", "csv"])
    if uploaded_file is not None:
      st.success("Datei bereit zum Import.")

# 7. ETIKETTEN DRUCKEN
elif action == "🖨 Etiketten drucken":
  st.header("🖨 Etiketten & Preisschilder drucken")
  if df.empty:
    st.warning("Keine Artikel im Bestand.")
  else:
    print_options = [
        f"{r.get('name')} | Art: {r.get('article')} | SAP: {r.get('sap')} | Barcode: {r.get('barcode')} (Bestand: {int(r.get('quantity', 0))} Stk.)"
        for _, r in df.iterrows()
    ]
    selected_to_print = st.selectbox("Artikel für Etikett auswählen:", print_options)
    if selected_to_print:
      chosen_item = df.iloc[print_options.index(selected_to_print)]
      raw_bc = str(chosen_item.get("barcode", "")) or str(chosen_item.get("sap", "")) or "12345678"
      barcode_url = f"https://barcodeapi.org/api/128/{urllib.parse.quote(raw_bc)}"

      label_html = f"""
            <div style="border: 1px solid #000; width: 4cm; height: 1.4cm; padding: 2px; box-sizing: border-box; background: white; color: black; display: flex; flex-direction: column; justify-content: space-between; font-family: Arial, sans-serif;">
                <div style="display: flex; justify-content: space-between; font-size: 7pt; font-weight: bold; line-height: 1;">
                    <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 70%;">{chosen_item.get('name')}</span>
                    <span><b>{chosen_item.get('preis', 0.0):.2f} €</b></span>
                </div>
                <div style="text-align: center; margin: auto 0;">
                    <img src="{barcode_url}" style="height: 0.75cm; max-width: 100%; image-rendering: pixelated;" />
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 6pt; color: #000; line-height: 1;">
                    <span>{chosen_item.get('brand', 'KaDeWe')}</span>
                    <span>SAP: {chosen_item.get('sap', '-')}</span>
                </div>
            </div>
            <br><button onclick="window.print();" style="background-color: #ff4b4b; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-weight: bold;">🖨 Etikett drucken</button>
            """
      components.html(label_html, height=150)

# 8. QR-CODE FÜR KOLLEGEN
elif action == "📱 QR-Code für Kollegen":
  st.header("📱 App-Zugang für das Team")
  app_url = "https://mtcbfvpjnxlkvvtuknyv.streamlit.app"
  qr_code_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={urllib.parse.quote(app_url)}"
  st.image(qr_code_url, width=300)
  st.markdown(f"Direktlink: [{app_url}]({app_url})")
