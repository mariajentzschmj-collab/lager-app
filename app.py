import hashlib
import io
import json
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


# --- СИСТЕМА АВТОРИЗАЦИИ (МЕНЕДЖЕР И АГЕНТЫ С ПИН-КОДОМ) ---
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

  role_choice = st.radio("Ich bin ein(e):", ["👔 Manager (Maria)", "🧑‍‍💼 Agent / Mitarbeiter"])

  if role_choice == "👔 Manager (Maria)":
    manager_password = st.text_input("Manager-Passwort", type="password")
    if st.button("Als Manager anmelden"):
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
st.sidebar.markdown(f"🏷️ **Rolle:** {'Manager (Vollzugriff)' if st.session_state.get('role') == 'manager' else 'Agent (Freigabe in App)'}")

# Если менеджер — проверяем количество ожидающих запросов в базе данных
pending_count = 0
if st.session_state.get("role") == "manager" and supabase is not None:
  try:
    res = supabase.table("approvals").select("*", count="exact").eq("status", "pending").execute()
    pending_count = res.count if res.count is not None else len(res.data)
  except Exception:
    pending_count = 0

if pending_count > 0:
  st.sidebar.error(f"🔔 **Wartet auf Freigabe:** {pending_count} Anfrage(n)")

if st.sidebar.button("🚪 Abmelden"):
  st.session_state["logged_in"] = False
  st.session_state["role"] = None
  st.session_state["user_name"] = None
  st.rerun()

# --- HAUPTCODE DER ANWENDUNG ---
st.title("📦 Lagerverwaltung (5. Etage)")
st.subheader("Iittala & Royal Copenhagen")


# --- ФУНКЦИЯ СОЗДАНИЯ ЗАПРОСА НА ПОДТВЕРЖДЕНИЕ В БАЗЕ ---
def request_manager_approval(action_type, payload_dict):
  agent_name = st.session_state.get("user_name", "Unbekannter Agent")
  if supabase is not None:
    try:
      data = {
          "agent_name": agent_name,
          "action_type": action_type,
          "payload": json.dumps(payload_dict),
          "status": "pending"
      }
      supabase.table("approvals").insert(data).execute()
      st.success("📤 Ihre Anfrage wurde an den Manager gesendet! Sobald Maria sie im System bestätigt, wird der Bestand aktualisiert.")
    except Exception as e:
      st.error(f"Fehler beim Senden der Anfrage: {e}")


# Функция для загрузки ALLER Artikel с Paginierung
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

# --- СЕКЦИЯ УПРАВЛЕНИЯ ЗАПРОСАМИ ДЛЯ МЕНЕДЖЕРА ---
if st.session_state.get("role") == "manager":
  with st.expander(f"🔔 Anfragen von Agenten verwalten ({pending_count} ausstehend)", expanded=(pending_count > 0)):
    if supabase is not None:
      try:
        pending_res = supabase.table("approvals").select("*").eq("status", "pending").execute()
        pending_requests = pending_res.data
        
        if not pending_requests:
          st.info("Keine ausstehenden Anfragen von Agenten.")
        else:
          for req in pending_requests:
            req_id = req["id"]
            agent = req["agent_name"]
            act_type = req["action_type"]
            payload = json.loads(req["payload"])
            
            st.markdown(f"**Agent:** `{agent}` | **Aktion:** `{act_type}` | **Zeit:** {req.get('created_at', '-')}")
            st.json(payload)
            
            c1, c2, _ = st.columns([1, 1, 3])
            with c1:
              if st.button("✅ Bestätigen", key=f"app_yes_{req_id}"):
                if act_type == "add_or_update":
                  supabase.table("inventory").upsert(payload, on_conflict="article").execute()
                elif act_type == "reduce_stock":
                  item_id = payload.get("id")
                  new_q = payload.get("new_quantity")
                  supabase.table("inventory").update({"quantity": int(new_q)}).eq("id", item_id).execute()
                elif act_type == "bulk_wareneingang":
                  # Массовый приход по SAP с прибавлением к текущему остатку
                  for item in payload.get("items", []):
                    sap_num = str(item.get("sap"))
                    inc_qty = int(item.get("incoming_qty", 0))
                    existing = supabase.table("inventory").select("*").eq("sap", sap_num).execute()
                    if existing.data:
                      curr_q = int(existing.data[0].get("quantity", 0))
                      new_q = curr_q + inc_qty
                      supabase.table("inventory").update({"quantity": new_q}).eq("sap", sap_num).execute()
                    else:
                      supabase.table("inventory").upsert(item, on_conflict="article").execute()
                elif act_type == "bulk_sales_report":
                  # Массовое вычитание по отчету о продажах
                  for item in payload.get("items", []):
                    art = str(item.get("article"))
                    sold_qty = int(item.get("sold_qty", 0))
                    existing = supabase.table("inventory").select("*").eq("article", art).execute()
                    if existing.data:
                      curr_q = int(existing.data[0].get("quantity", 0))
                      new_q = max(0, curr_q - sold_qty)
                      supabase.table("inventory").update({"quantity": new_q}).eq("article", art).execute()
                elif act_type == "catalog_upload":
                  # Массовая загрузка каталога (включая нулевые значения)
                  for item in payload.get("items", []):
                    supabase.table("inventory").upsert(item, on_conflict="article").execute()

                supabase.table("approvals").update({"status": "approved"}).eq("id", req_id).execute()
                st.success("✅ Anfrage erfolgreich bestätigt und Lagerbestand aktualisiert!")
                st.rerun()
            
            with c2:
              if st.button("❌ Ablehnen", key=f"app_no_{req_id}"):
                supabase.table("approvals").update({"status": "rejected"}).eq("id", req_id).execute()
                st.warning("❌ Anfrage abgelehnt.")
                st.rerun()
            st.markdown("---")
      except Exception as e:
        st.error(f"Fehler beim Laden der Anfragen: {e}")

# --- SEITENMENÜ ---
st.sidebar.header("⚙️ Lagersteuerung")
action = st.sidebar.radio(
    "Aktion auswählen:",
    [
        "📊 Bestände anzeigen",
        "➕ Artikel hinzufügen",
        "📉 Artikel reduzieren (Verkauf)",
        "📥 Massen-Wareneingang (Zuwachs)",
        "📥 Auto-Abverkauf per Bericht",
        "📁 Katalog aus Datei hochladen",
        "📷 Live-Kamera-Scanner",
        "🖨 Etiketten drucken",
        "📋 Inventur-Schnelleingabe",
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
  st.header("✨ Neuen Artikel hinzufügen oder Bestand anpassen" + ("" if is_manager else " (Wartet auf Manager-Freigabe)"))

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

    submit_btn_label = "Speichern / Aktualisieren (Manager)" if is_manager else "📤 Freigabe an Maria anfordern"
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
      payload = {
          "article": str(new_article),
          "name": str(new_name),
          "brand": str(new_brand),
          "quantity": int(new_qty),
          "location": str(new_location),
          "preis": float(new_preis),
          "sap": str(new_sap),
          "barcode": str(new_barcode),
      }
      request_manager_approval("add_or_update", payload)

# 3. ARTIKEL REDUZIEREN (VERKAUF)
elif action == "📉 Artikel reduzieren (Verkauf)":
  is_manager = st.session_state.get("role") == "manager"
  st.header("🛒 Verkauf / Bestandsreduzierung erfassen" + ("" if is_manager else " (Wartet auf Manager-Freigabe)"))

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

        sale_btn_label = "Verkauf direkt bestätigen (Manager)" if is_manager else "📤 Freigabe für Verkauf anfordern"
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
          payload = {
              "id": int(selected_row["id"]),
              "name": str(selected_row.get("name")),
              "current_quantity": current_qty,
              "reduce_by": int(reduce_qty),
              "new_quantity": new_qty
          }
          request_manager_approval("reduce_stock", payload)

# 4. MASSEN-WARENEINGANG (ZUWACHS) ПО SAP — ТОЛЬКО ПЛЮСУЕТ К СУЩЕСТВУЮЩИМ
elif action == "📥 Massen-Wareneingang (Zuwachs)":
  is_manager = st.session_state.get("role") == "manager"
  st.header("📥 Massen-Wareneingang (Bestand erhöhen nach SAP)" + ("" if is_manager else " (Wartet auf Manager-Freigabe)"))
  st.markdown("Laden Sie eine Excel- oder CSV-Datei mit den eintreffenden Waren hoch (Spalten: `sap`, `quantity`). Die angegebenen Mengen werden **nach SAP-Nummer automatisch zum bestehenden Bestand addiert**.")

  template_df = pd.DataFrame(columns=["sap", "name", "brand", "quantity", "preis", "article", "barcode"])
  template_df.loc[0] = ["1066372", "Mussedeltid Teller 27cm", "Royal Copenhagen", 1, 29.40, "101234", "5705140123456"]

  out_tmpl = io.BytesIO()
  with pd.ExcelWriter(out_tmpl, engine="openpyxl") as writer:
    template_df.to_excel(writer, index=False, sheet_name="Wareneingang")
  
  st.download_button(
      label="📥 Excel-Vorlage für Wareneingang herunterladen",
      data=out_tmpl.getvalue(),
      file_name="KaDeWe_Wareneingang_Vorlage.xlsx",
      mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
  )

  st.markdown("---")
  incoming_file = st.file_uploader("Wareneingangs-Datei auswählen", type=["xlsx", "csv"], key="incoming_upload_v3")

  if incoming_file is not None:
    try:
      if incoming_file.name.endswith(".csv"):
        inc_df = pd.read_csv(incoming_file)
      else:
        inc_df = pd.read_excel(incoming_file)

      # Нормализуем названия колонок к нижнему регистру
      inc_df.columns = [str(c).strip().lower() for c in inc_df.columns]
      st.write("📋 Vorschau des Wareneingangs:", inc_df.head())

      if st.button("🚀 Wareneingang buchen & Bestände erhöhen"):
        if supabase is not None:
          success_count = 0
          not_found_count = 0
          updated_details = []

          def clean_val(val):
            if pd.isna(val):
              return ""
            s = str(val).strip()
            if s.endswith(".0"):
              s = s[:-2]
            return s

          for _, row in inc_df.iterrows():
            sap_num = clean_val(row.get("sap", ""))
            art_num = clean_val(row.get("article", ""))

            # Если в строке нет ни SAP, ни артикула — пропускаем
            if not sap_num and not art_num:
              continue

            # Количество
            q_raw = row.get("quantity", 0)
            try:
              inc_qty = int(float(str(q_raw).replace(',', '.'))) if not pd.isna(q_raw) else 0
            except:
              inc_qty = 0

            if inc_qty <= 0:
              continue

            # Цена (если указана в файле)
            p_raw = row.get("preis", row.get("price", 0))
            preis_val = 0.0
            if not pd.isna(p_raw):
              p_str = str(p_raw).replace('€', '').replace(' ', '').replace(',', '.')
              try:
                preis_val = float(p_str) if p_str else 0.0
              except:
                preis_val = 0.0

            # Ищем товар в базе ТОЛЬКО среди существующих (по SAP или Article)
            existing = None
            if sap_num:
              existing = supabase.table("inventory").select("*").eq("sap", sap_num).execute()
            if (not existing or not existing.data) and art_num:
              existing = supabase.table("inventory").select("*").eq("article", art_num).execute()

            if existing and existing.data:
              # Товар найден — строго прибавляем количество!
              item_db = existing.data[0]
              item_id = item_db["id"]
              item_name = item_db.get("name", "Unbekannter Artikel")
              curr_q = int(item_db.get("quantity", 0))
              new_q = curr_q + inc_qty

              update_data = {"quantity": new_q}
              if preis_val > 0:
                update_data["preis"] = preis_val

              res = supabase.table("inventory").update(update_data).eq("id", item_id).execute()
              if res.data:
                success_count += 1
                updated_details.append({
                    "Artikel": item_name,
                    "SAP / Code": sap_num if sap_num else art_num,
                    "Hinzugefügt": inc_qty,
                    "Alter Bestand": curr_q,
                    "Neuer Bestand": new_q
                })
            else:
              # Если товара нет в базе, приход на него не создаем автоматически, чтобы избежать ошибок
              not_found_count += 1

          # Итоги
          st.success(f"✅ Wareneingang erfolgreich gebucht! Bestände für **{success_count}** Positionen erhöht.")
          
          if updated_details:
            st.markdown("### 📊 Details zum Wareneingang:")
            st.dataframe(pd.DataFrame(updated_details), use_container_width=True)

          if not_found_count > 0:
            st.warning(f"⚠ {not_found_count} Positionen wurden in der Datenbank nicht gefunden (Bestand wurde nicht erhöht). Bitte legen Sie neue Artikel zuerst im Katalog an.")

        else:
          st.error("Keine Verbindung zu Supabase.")
    except Exception as e:
      st.error(f"Fehler beim Verarbeiten des Wareneingangs: {e}")

# 5. AUTO-ABVERKAUF PER BERICHT (МАССОВЫЙ ВЫЧЕТ ПО ОТЧЕТУ О ПРОДАЖАХ — С ШАБЛОНОМ И ОТЧЕТОМ)
elif action == "📥 Auto-Abverkauf per Bericht":
  is_manager = st.session_state.get("role") == "manager"
  st.header("📥 Automatischer Abverkauf per Verkaufsbericht" + ("" if is_manager else " (Wartet auf Manager-Freigabe)"))
  st.markdown("Laden Sie einen Verkaufsbericht (Excel/CSV) hoch, der verkaufte Mengen enthält. Die verkauften Mengen werden **automatisch vom Bestand abgezogen**.")

  # 1. Кнопка скачивания шаблона Excel для продаж
  template_sales_df = pd.DataFrame(columns=["article", "sap", "quantity"])
  template_sales_df.loc[0] = ["4149", "1070438", 2]

  out_sales_tmpl = io.BytesIO()
  with pd.ExcelWriter(out_sales_tmpl, engine="openpyxl") as writer:
    template_sales_df.to_excel(writer, index=False, sheet_name="Verkäufe")
  
  st.download_button(
      label="📥 Excel-Vorlage für Verkaufsbericht herunterladen",
      data=out_sales_tmpl.getvalue(),
      file_name="KaDeWe_Verkaufsbericht_Vorlage.xlsx",
      mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
  )

  st.markdown("---")
  sales_file = st.file_uploader("Verkaufsbericht auswählen", type=["xlsx", "csv"], key="sales_report_upload_v2")

  if sales_file is not None:
    try:
      if sales_file.name.endswith(".csv"):
        report_df = pd.read_csv(sales_file)
      else:
        report_df = pd.read_excel(sales_file)

      # Нормализуем названия колонок
      report_df.columns = [str(c).strip().lower() for c in report_df.columns]
      st.write("📋 Vorschau des Verkaufsberichts:", report_df.head())

      if st.button("🚀 Abverkauf buchen & Bestände reduzieren"):
        items_sold = []
        
        def clean_val(val):
          if pd.isna(val):
            return ""
          s = str(val).strip()
          if s.endswith(".0"):
            s = s[:-2]
          return s

        for _, row in report_df.iterrows():
          art_val = clean_val(row.get("article", row.get("artikelnr", row.get("sku", ""))))
          sap_val = clean_val(row.get("sap", ""))
          
          code_to_use = art_val if art_val else sap_val
          if not code_to_use:
            continue

          q_raw = row.get("quantity", row.get("sold_qty", row.get("menge", 0)))
          try:
            sold_qty = int(float(str(q_raw).replace(',', '.'))) if not pd.isna(q_raw) else 0
          except:
            sold_qty = 0

          if sold_qty > 0:
            items_sold.append({
                "code": code_to_use,
                "sold_qty": sold_qty
            })

        if is_manager:
          if supabase is not None:
            success_count = 0
            updated_details = []
            not_found_count = 0

            for item in items_sold:
              code = item["code"]
              sold_qty = item["sold_qty"]
              
              # Ищем сначала по article, затем по sap
              existing = supabase.table("inventory").select("*").eq("article", code).execute()
              if not existing or not existing.data:
                existing = supabase.table("inventory").select("*").eq("sap", code).execute()

              if existing and existing.data:
                item_db = existing.data[0]
                item_id = item_db["id"]
                item_name = item_db.get("name", "Unbekannt")
                curr_q = int(item_db.get("quantity", 0))
                new_q = max(0, curr_q - sold_qty)
                
                res = supabase.table("inventory").update({"quantity": new_q}).eq("id", item_id).execute()
                if res.data:
                  success_count += 1
                  updated_details.append({
                      "Artikel": item_name,
                      "Code": code,
                      "Verkauft": sold_qty,
                      "Alter Bestand": curr_q,
                      "Neuer Bestand": new_q
                  })
              else:
                not_found_count += 1

            # Красивый блок подтверждения
            st.success(f"✅ Verkaufsbericht erfolgreich verarbeitet! Bestände für **{success_count}** Artikel aktualisiert.")
            
            if updated_details:
              st.markdown("### 📊 Details zur Bestandsreduzierung:")
              st.dataframe(pd.DataFrame(updated_details), use_container_width=True)

            if not_found_count > 0:
              st.warning(f"⚠ {not_found_count} Positionen aus dem Bericht wurden in der Datenbank nicht gefunden und übersprunken.")
          else:
            st.error("Keine Verbindung zu Supabase.")
        else:
          payload = {"items": items_sold}
          request_manager_approval("bulk_sales_report", payload)

    except Exception as e:
      st.error(f"Fehler beim Verarbeiten des Berichts: {e}")
# 6. KATALOG AUS DATEI HOCHLADEN (ВКЛЮЧАЯ 0 ЗНАЧЕНИЯ)
elif action == "📁 Katalog aus Datei hochladen":
  is_manager = st.session_state.get("role") == "manager"
  st.header("📂 Gesamtkatalog hochladen (inkl. 0 Bestände)" + ("" if is_manager else " (Wartet auf Manager-Freigabe)"))
  st.markdown("Laden Sie eine vollständige Excel- oder CSV-Datei des Katalogs hoch. Artikel mit Bestand `0` werden ebenfalls korrekt mit 0 eingetragen oder aktualisiert.")

  template_df = pd.DataFrame(columns=["article", "name", "brand", "quantity", "preis", "sap", "barcode", "location"])
  template_df.loc[0] = ["10001", "Teema Teller 21cm", "Iittala", 0, 19.50, "SAP001", "641192000001", "Etage 5 Lager"]

  out_tmpl = io.BytesIO()
  with pd.ExcelWriter(out_tmpl, engine="openpyxl") as writer:
    template_df.to_excel(writer, index=False, sheet_name="Katalog")
  st.download_button(
      label="📥 Excel-Vorlage für Katalog herunterladen",
      data=out_tmpl.getvalue(),
      file_name="KaDeWe_Katalog_Vorlage.xlsx",
      mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
  )

  catalog_file = st.file_uploader("Katalog-Datei auswählen", type=["xlsx", "csv"], key="catalog_upload")

  if catalog_file is not None:
    try:
      if catalog_file.name.endswith(".csv"):
        cat_df = pd.read_csv(catalog_file)
      else:
        cat_df = pd.read_excel(catalog_file)

      st.write("📋 Vorschau des Katalogs:", cat_df.head())

      if st.button("🚀 Katalog in Datenbank übernehmen / Freigabe anfordern"):
        catalog_items = []
        for _, row in cat_df.iterrows():
          catalog_items.append({
              "article": str(row.get("article", "")),
              "name": str(row.get("name", "Unbekannt")),
              "brand": str(row.get("brand", "Iittala")),
              "quantity": int(row.get("quantity", 0)),
              "preis": float(row.get("preis", 0.0)),
              "sap": str(row.get("sap", "")),
              "barcode": str(row.get("barcode", "")),
              "location": str(row.get("location", "Etage 5 Lager"))
          })

        if is_manager:
          if supabase is not None:
            for item in catalog_items:
              supabase.table("inventory").upsert(item, on_conflict="article").execute()
            st.success("✅ Gesamter Katalog erfolgreich aktualisiert (inkl. 0-Bestände)!")
            st.rerun()
        else:
          payload = {"items": catalog_items}
          request_manager_approval("catalog_upload", payload)

    except Exception as e:
      st.error(f"Fehler beim Verarbeiten des Katalogs: {e}")

# 7. LIVE-KAMERA-SCANNER
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
        cam_btn_lbl = "Aktualisieren (Manager)" if is_manager else "📤 Freigabe über App anfordern"
        request_cam_code = st.form_submit_button(cam_btn_lbl)

      if request_cam_code:
        new_qty = current_qty + int(delta_qty) if "hinzufügen" in change_type.lower() else max(0, current_qty - int(delta_qty))
        if is_manager:
          if supabase is not None:
            supabase.table("inventory").update({"quantity": int(new_qty)}).eq("id", item["id"]).execute()
            st.success(f"✅ Aktualisiert! Neuer Bestand: {new_qty} Stk.")
            st.rerun()
        else:
          payload = {
              "id": int(item["id"]),
              "name": str(item_name),
              "current_quantity": current_qty,
              "new_quantity": new_qty,
              "change_description": f"{change_type} ({delta_qty} Stk.)"
          }
          request_manager_approval("reduce_stock", payload)

# 8. ETIKETTEN DRUCKEN
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

# 9. QR-CODE FÜR KOLLEGEN
elif action == "📱 QR-Code für Kollegen":
  st.header("📱 App-Zugang für das Team")
  app_url = "https://mtcbfvpjnxlkvvtuknyv.streamlit.app"
  qr_code_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={urllib.parse.quote(app_url)}"
  st.image(qr_code_url, width=300)
  st.markdown(f"Direktlink: [{app_url}]({app_url})")

        # ==========================================
# KOMPLETT-BLOCK: MIN/MAX UPLOAD & AUTOMATISCHE BESTELLUNG
# ==========================================

st.sidebar.markdown("---")
st.sidebar.subheader("📦 Automatische Bestellung & Min/Max")

# 1. Sektion: Min/Max-Werte per Excel aktualisieren
st.sidebar.markdown("**1. Min/Max-Werte per Excel aktualisieren**")
uploaded_minmax = st.sidebar.file_uploader(
    "Excel-Datei (sap, min_stock, max_stock) hochladen", 
    type=["xlsx", "xls"],
    key="minmax_uploader_combined_v2"
)

if uploaded_minmax is not None:
  try:
    update_df = pd.read_excel(uploaded_minmax)
    # Alle Spaltennamen in Kleinbuchstaben umwandeln
    update_df.columns = [str(c).strip().lower() for c in update_df.columns]
    
    st.sidebar.success(f"Datei geladen! Zeilen: {len(update_df)}")
    
    if st.sidebar.button("💾 In Datenbank speichern", key="btn_save_minmax_db"):
      success_count = 0
      error_count = 0
      not_found_count = 0
      
      for _, row in update_df.iterrows():
        try:
          # SAP-Nummer auslesen und .0-Endung von Excel entfernen
          sap_val = str(row.get("sap", "")).strip()
          if sap_val.endswith(".0"):
            sap_val = sap_val[:-2]

          min_val = int(row.get("min_stock", 2))
          max_val = int(row.get("max_stock", 10))
          
          if sap_val and sap_val != "nan":
            # Prüfen, ob der Artikel in Supabase existiert
            existing = supabase.table("inventory").select("id, sap").eq("sap", sap_val).execute()
            
            if existing.data and len(existing.data) > 0:
              # Werte in der Datenbank aktualisieren
              supabase.table("inventory").update({
                  "min_stock": min_val,
                  "max_stock": max_val
              }).eq("sap", sap_val).execute()
              success_count += 1
            else:
              not_found_count += 1
          else:
            error_count += 1
        except Exception:
          error_count += 1
          
      st.sidebar.success(f"Aktualisiert: {success_count}")
      if not_found_count > 0:
        st.sidebar.warning(f"Nicht in DB gefunden: {not_found_count}")
      if error_count > 0:
        st.sidebar.error(f"Fehlerhafte Zeilen: {error_count}")
        
      # WICHTIG: Automatischer Neustart des Skripts, ohne F5 zu drücken!
      st.success("Änderungen gespeichert! Aktualisiere Ansicht...")
      st.rerun()
      
  except Exception as e:
    st.sidebar.error(f"Fehler beim Verlesen der Datei: {e}")

st.sidebar.markdown("---")

# 2. Sektion: Nachbestellung prüfen und generieren
st.sidebar.markdown("**2. Nachbestellung ausführen**")
if st.sidebar.button("🚀 Nachbestellung prüfen", key="btn_nachbestellung_pruefen"):
  if df.empty:
    st.sidebar.warning("⚠️ Keine Daten im Bestand gefunden.")
  else:
    check_df = df.copy()
    check_df["quantity"] = pd.to_numeric(check_df["quantity"], errors="coerce").fillna(0)
    
    # Standardwerte falls Spalten fehlen
    if "min_stock" not in check_df.columns:
      check_df["min_stock"] = 2
    if "max_stock" not in check_df.columns:
      check_df["max_stock"] = 10

    check_df["min_stock"] = pd.to_numeric(check_df["min_stock"], errors="coerce").fillna(2)
    check_df["max_stock"] = pd.to_numeric(check_df["max_stock"], errors="coerce").fillna(10)

    # WICHTIG: Nur Artikel berücksichtigen, deren Mindestbestand größer als 0 ist (min_stock > 0)
    active_check_df = check_df[check_df["min_stock"] > 0]

    # Filtern nach individuellem Mindestbestand (Bestand <= min_stock)
    reorder_df = active_check_df[active_check_df["quantity"] <= active_check_df["min_stock"]].copy()

    if reorder_df.empty:
      st.sidebar.success("✅ Alle aktiven Artikel über ihrem Mindestbestand!")
    else:
      # Bestellmenge bis zum individuellen Max-Bestand berechnen
      reorder_df["order_qty"] = reorder_df["max_stock"] - reorder_df["quantity"]
      reorder_df["order_qty"] = reorder_df["order_qty"].apply(lambda x: max(1, x))
      
      st.sidebar.error(f"🚨 {len(reorder_df)} Artikel unter Minimum!")
      
      # Anzeige im Hauptbereich
      st.markdown("---")
      st.header("🚨 Automatische Bestellliste (nach Min/Max-Werten)")
      st.markdown("Folgende Artikel haben ihren **individuellen Mindestbestand** unterschritten (Artikel mit Mindestbestand = 0 wurden ausgeschlossen):")
      
      display_cols = [c for c in ["article", "name", "brand", "quantity", "min_stock", "max_stock", "order_qty", "sap", "preis"] if c in reorder_df.columns]
      st.dataframe(reorder_df[display_cols], use_container_width=True)

      # Excel-Download vorbereiten
      out_excel = io.BytesIO()
      with pd.ExcelWriter(out_excel, engine="openpyxl") as writer:
        reorder_df[display_cols].to_excel(writer, index=False, sheet_name="Bestellung")
      
      st.download_button(
          label="📥 Bestellliste als Excel herunterladen",
          data=out_excel.getvalue(),
          file_name="KaDeWe_Individuelle_Bestellung.xlsx",
          mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          key="download_reorder_excel_btn"
      )

# ==========================================
# AUTOMATISCHE MIN/MAX-BERECHNUNG NACH LAGERABGANG
# ==========================================

st.sidebar.markdown("---")
st.sidebar.subheader("📈 Intelligente Min/Max-Berechnung")

st.sidebar.markdown(
    "Vergleicht den aktuellen Bestand mit dem vorherigen, berechnet die"
    " Verkaufsgeschwindigkeit und aktualisiert die Limits."
)

# Einstellung der gewünschten Reichweite in Tagen direkt im Interface
days_min = st.sidebar.slider("Reichweite in Tagen für MIN", 2, 14, 5, key="slider_days_min_v2")
days_max = st.sidebar.slider("Reichweite in Tagen für MAX", 10, 45, 20, key="slider_days_max_v2")

if st.sidebar.button("🚀 Automatische Neuberechnung starten", key="btn_neuberechnung_starten"):
  if df.empty:
    st.sidebar.warning("⚠ Keine Daten zur Analyse gefunden.")
  else:
    calc_df = df.copy()
    updated_count = 0
    from datetime import datetime

    today_str = datetime.now().strftime("%Y-%m-%d")

    for _, row in calc_df.iterrows():
      sap_val = str(row.get("sap", "")).strip()
      if not sap_val or sap_val == "nan":
        continue

      current_qty = float(row.get("quantity", 0))

      # Vorherigen Bestand abrufen (falls noch nicht in Supabase vorhanden, aktuellen als Startwert nutzen)
      last_qty = float(row.get("last_quantity", current_qty))

      # Verbrauch: Wenn der vorige Bestand größer als der aktuelle ist, wurde Ware verkauft
      sold_amount = last_qty - current_qty

      if sold_amount > 0:
        # Angenommen, es sind ca. 7 Tage seit der letzten Prüfung vergangen
        days_passed = 7
        daily_speed = sold_amount / days_passed

        # Neue Limits berechnen
        new_min = max(2, int(daily_speed * days_min))
        new_max = max(new_min + 5, int(daily_speed * days_max))

        # In Supabase aktualisieren: Neue Limits speichern und aktuellen Bestand als "alt" für die nächste Messung merken
        try:
          supabase.table("inventory").update({
              "min_stock": new_min,
              "max_stock": new_max,
              "last_quantity": current_qty, 
          }).eq("sap", sap_val).execute()
          updated_count += 1
        except Exception as e:
          pass
      else:
        # Auch wenn es keine Verkäufe gab, last_quantity aktualisieren, um die Basis für die kommenden Tage zu sichern
        try:
          supabase.table("inventory").update(
              {"last_quantity": current_qty}
          ).eq("sap", sap_val).execute()
        except:
          pass

    st.sidebar.success(
        f"✅ Erfolgreich aktualisierte Artikel nach Verkaufsgeschwindigkeit:"
        f" {updated_count}"
    )
    st.rerun()
    # ==========================================
# ==========================================
# UMSATZBERECHNUNG & AKKUMULATION (TAG & MONAT)
# ==========================================

st.sidebar.markdown("---")
st.sidebar.subheader("💶 Umsatz-Tracking (Tage & Monate)")

st.sidebar.markdown(
    "Laden Sie einen Verkaufsbericht hoch. Die Umsätze werden korrekt summiert und in Supabase gespeichert."
)

with st.sidebar.expander("ℹ️ Format-Hinweis"):
    st.markdown("""
    Ihre Datei sollte folgende Spalten enthalten:
    1. **Datum** (z. B. `02.10.2026`)
    2. **Gesamtpreis / Umsatz** (die fertige Summe pro Zeile)
    """)

sales_file = st.sidebar.file_uploader(
    "Verkaufsbericht hochladen (Excel / CSV)", type=["xlsx", "csv"], key="sales_report_accum"
)

if sales_file is not None:
    try:
        import pandas as pd

        if sales_file.name.endswith(".csv"):
            sales_report_df = pd.read_csv(sales_file)
        else:
            sales_report_df = pd.read_excel(sales_file)

        st.sidebar.success("✅ Bericht erfolgreich geladen!")

        columns_list = list(sales_report_df.columns)
        date_col = st.sidebar.selectbox("Spalte für das Datum", columns_list, key="acc_date_col")
        price_col = st.sidebar.selectbox("Spalte für Gesamtpreis / Umsatz", columns_list, key="acc_price_col")

        if st.sidebar.button("💾 Umsatz speichern & kumulieren"):
            # Очищаем и суммируем общую сумму брутто
            cleaned_prices = (
                sales_report_df[price_col]
                .astype(str)
                .str.replace('€', '', regex=False)
                .str.replace(' ', '', regex=False)
                .str.replace(',', '.', regex=False)
            )
            total_brutto = pd.to_numeric(cleaned_prices, errors='coerce').sum()

            sales_report_df[date_col] = pd.to_datetime(sales_report_df[date_col], errors='coerce')
            valid_dates = sales_report_df[date_col].dropna()
            
            if not valid_dates.empty:
                report_date = valid_dates.iloc[0].strftime('%Y-%m-%d')
                report_month = valid_dates.iloc[0].strftime('%Y-%m')
            else:
                report_date = pd.Timestamp.today().strftime('%Y-%m-%d')
                report_month = pd.Timestamp.today().strftime('%Y-%m')

            # Сохранение в Supabase
            if supabase is not None:
                try:
                    existing_day = supabase.table("daily_sales").select("*").eq("date", report_date).execute()
                    
                    if existing_day and existing_day.data:
                        supabase.table("daily_sales").update({
                            "brutto": float(total_brutto),
                            "month": report_month
                        }).eq("date", report_date).execute()
                    else:
                        supabase.table("daily_sales").insert({
                            "date": report_date,
                            "brutto": float(total_brutto),
                            "month": report_month
                        }).execute()
                    
                    st.sidebar.success(f"✔ Umsatz für {report_date} ({total_brutto:,.2f} €) gespeichert!")
                except Exception as db_err:
                    st.sidebar.warning(f"⚠ DB-Hinweis: {db_err}")

            total_netto = total_brutto / 1.19
            st.sidebar.markdown("---")
            st.sidebar.metric(label="Brutto (dieser Bericht)", value=f"{total_brutto:,.2f} €")
            st.sidebar.metric(label="Netto (exkl. 19% MwSt.)", value=f"{total_netto:,.2f} €")

    except Exception as e:
        st.sidebar.error(f"⚠ Fehler beim Verarbeiten: {e}")

# Блок отображения накопленной истории по месяцам
if supabase is not None:
    st.sidebar.markdown("---")
    st.sidebar.subheader("📈 Kumulierte Umsätze (Historie)")
    
    try:
        history_res = supabase.table("daily_sales").select("*").execute()
        if history_res and history_res.data:
            hist_df = pd.DataFrame(history_res.data)
            
            if not hist_df.empty and "month" in hist_df.columns and "brutto" in hist_df.columns:
                monthly_summary = hist_df.groupby("month")["brutto"].sum().reset_index()
                monthly_summary = monthly_summary.sort_values("month")

                st.sidebar.markdown("**Nach Monaten:**")
                for _, row in monthly_summary.iterrows():
                    m_name = row["month"]
                    m_brutto = row["brutto"]
                    m_netto = m_brutto / 1.19
                    st.sidebar.markdown(f"🗓 **{m_name}**: Netto **{m_netto:,.2f} €** *(Brutto: {m_brutto:,.2f} €)*")
        else:
            st.sidebar.info("ℹ Noch keine kumulierten Daten in der Datenbank.")
    except Exception as hist_err:
        st.sidebar.caption("💡 Tipp: Stellen Sie sicher, dass die Tabelle `daily_sales` in Supabase existiert.")

# --- ИСТОРИЯ ЗАГРУЖЕННЫХ ДАТ В UMSATZ-TRACKING ---
if supabase is not None:
    try:
        res_hist = supabase.table("daily_sales").select("date, brutto").order("date", desc=True).execute()
        if res_hist and res_hist.data:
            hist_df = pd.DataFrame(res_hist.data)
            with st.sidebar.expander("📅 Bereits geladene Tage anzeigen"):
                if not hist_df.empty:
                    for _, h_row in hist_df.iterrows():
                        d_str = h_row.get("date", "-")
                        b_val = float(h_row.get("brutto", 0) or 0)
                        n_val = b_val / 1.19
                        st.sidebar.markdown(f"• **{d_str}**: {n_val:,.2f} € Netto *(Brutto: {b_val:,.2f} €)*")
                else:
                    st.sidebar.info("Noch keine Tage erfasst.")
    except Exception as e:
        pass

# ==========================================
# БЛОК: ИНВЕНТУР-СКННЕЛЬВЕИС (ИНВЕНТАРИЗАЦИЯ ДЛЯ НЕСКОЛЬКИХ СОТРУДНИКОВ)
# ==========================================

if action == "📋 Inventur-Schnelleingabe":
    is_manager = st.session_state.get("role") == "manager"
    agent_name = st.session_state.get("user_name", "Mitarbeiter")
    
    st.header("📋 Inventur-Schnelleingabe (Multi-User)" + ("" if is_manager else f" (Agent: {agent_name})"))
    st.markdown("Hier können Mitarbeiter schnell den tatsächlichen Bestand vor Ort erfassen. Die Zählung wird zur Kontrolle an den Manager gesendet oder direkt verbucht.")

    with st.form("quick_inventory_form"):
        col_q1, col_q2 = st.columns([2, 1])
        with col_q1:
            inv_search = st.text_input(
                "🔍 Artikel suchen (Name, SAP, Artikelnummer oder Barcode):",
                placeholder="Suchbegriff eingeben...",
                key="quick_inv_search_input"
            )
        with col_q2:
            inv_counted_qty = st.number_input(
                "Gezählte Ist-Menge:",
                min_value=0,
                value=0,
                step=1,
                key="quick_inv_counted_qty_input"
            )
            
        inv_submitted = st.form_submit_button("📥 Zählung erfassen / absenden")

    if inv_search and not df.empty:
        matched_items = search_items(df, inv_search)
        if not matched_items.empty:
            st.markdown("### 📦 Ausgewählter Artikel:")
            sel_item = matched_items.iloc[0]
            
            st.info(
                f"**Name:** {sel_item.get('name')} | "
                f"**Art-Nr:** {sel_item.get('article')} | "
                f"**SAP:** {sel_item.get('sap')} | "
                f"**System-Bestand:** {int(sel_item.get('quantity', 0))} Stk."
            )
            
            if inv_submitted:
                new_counted = int(inv_counted_qty)
                item_id = int(sel_item.get("id")) if "id" in sel_item else None
                item_name = str(sel_item.get("name"))
                old_qty = int(sel_item.get("quantity", 0))
                
                if is_manager:
                    if supabase is not None and item_id:
                        try:
                            supabase.table("inventory").update({"quantity": new_counted}).eq("id", item_id).execute()
                            st.success(f"✅ Bestand für '{item_name}' direkt aktualisiert: Alt: {old_qty} ➔ Neu: {new_counted}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Fehler beim Aktualisieren: {e}")
                else:
                    # Отправляем запрос на подтверждение менеджеру от конкретного сотрудника
                    payload = {
                        "id": item_id,
                        "article": str(sel_item.get("article", "")),
                        "name": item_name,
                        "old_quantity": old_qty,
                        "new_quantity": new_counted,
                        "counted_by": agent_name
                    }
                    request_manager_approval("inventory_count", payload)
        else:
            if inv_submitted:
                st.warning("⚠️ Kein Artikel zu diesem Suchbegriff gefunden. Bitte prüfen Sie die Eingabe.")

