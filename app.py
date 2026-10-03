import hashlib
import io
import time
import urllib.parse
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client

# Seitanordnung
st.set_page_config(
    page_title="KaDeWe Lager — Iittala & Royal Copenhagen", layout="wide"
)

# --- ROLLEN- UND PASSWORT-LOGIN (MANAGER & AGENT) ---
def check_login():
  TIMEOUT_SECONDS = 300  # 5 Minuten Inaktivitäts-Timeout

  if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["role"] = None
    st.session_state["last_active"] = time.time()

  if st.session_state["logged_in"]:
    if (
        time.time() - st.session_state.get("last_active", time.time())
        > TIMEOUT_SECONDS
    ):
      st.session_state["logged_in"] = False
      st.session_state["role"] = None
      st.warning(
          "⏱️ Sitzung wegen Inaktivität abgelaufen (> 5 Min.). Bitte erneut"
          " anmelden."
      )

  if st.session_state["logged_in"]:
    st.session_state["last_active"] = time.time()
    return True

  st.title("🔐 KaDeWe Lagerverwaltung - Anmeldung")
  st.subheader(
      "Bitte wählen Sie Ihre Rolle und geben Sie das Passwort ein (Timeout nach"
      " 5 Min.)"
  )

  role_choice = st.selectbox("Zugriffsrolle:", ["Verkäufer / Agent", "Manager"])
  password = st.text_input("Passwort", type="password")

  if st.button("Anmelden"):
    if role_choice == "Manager" and password == "KaDeWe2026!Mgr":
      st.session_state["logged_in"] = True
      st.session_state["role"] = "Manager"
      st.session_state["last_active"] = time.time()
      st.rerun()
    elif role_choice == "Verkäufer / Agent" and password in [
        "agent2026",
        "kadewe2026",
    ]:
      st.session_state["logged_in"] = True
      st.session_state["role"] = "Agent"
      st.session_state["last_active"] = time.time()
      st.rerun()
    else:
      st.error("❌ Falsches Passwort oder ungültige Rolle")
  return False


if not check_login():
  st.stop()

# Aktuelle Rolle abrufen
current_role = st.session_state.get("role", "Agent")

# --- HAUPTCODE DER ANWENDUNG ---
st.title("📦 Lagerverwaltung (5. Etage)")
st.subheader(
    f"Iittala & Royal Copenhagen | Angemeldet als: **Maria Jentzsch**"
    f" ({current_role})"
)

# Abmelden-Button in der Seitenleiste
if st.sidebar.button("🚪 Abmelden"):
  st.session_state["logged_in"] = False
  st.session_state["role"] = None
  st.rerun()

SUPABASE_URL = "https://mtcbfvpjnxlkvvtuknyv.supabase.co"
SUPABASE_KEY = "sb_publishable_wChGuVU2FeW23S2bqdYqOg_B9-oMoKs"

supabase = None
try:
  supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
  pass


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
      "min_qty",
      "max_qty",
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
      for col in ["quantity", "min_qty", "max_qty"]:
        if col in df_loaded.columns:
          df_loaded[col] = (
              pd.to_numeric(df_loaded[col], errors="coerce")
              .fillna(0)
              .astype(int)
          )
        else:
          df_loaded[col] = 0
      if "preis" in df_loaded.columns:
        df_loaded["preis"] = pd.to_numeric(
            df_loaded["preis"], errors="coerce"
        ).fillna(0.0)
      return df_loaded

  except Exception as e:
    st.error(f"❌ Fehler beim Laden der Daten: {e}")

  return pd.DataFrame(columns=cols)


df = load_data()

# --- BENACHRICHTIGUNGEN FÜR MANAGER (AGENTEN-ANFRAGEN) ---
if current_role == "Manager" and supabase is not None:
  try:
    pending_reqs = (
        supabase.table("agent_requests")
        .select("*")
        .eq("status", "ausstehend")
        .execute()
    )
    req_count = (
        len(pending_reqs.data) if pending_reqs and pending_reqs.data else 0
    )
    if req_count > 0:
      if st.expander(f"🔔 Anfragen von Agenten verwalten ({req_count} ausstehend)"):
        for req in pending_reqs.data:
          st.write(
              f"**Artikel:** {req.get('article_name')} | **Menge:**"
              f" {req.get('requested_qty')} | **Typ:** {req.get('req_type')}"
          )
          col_app1, col_app2 = st.columns(2)
          if col_app1.button("Genehmigen", key=f"app_{req['id']}"):
            art_id = req.get("inventory_id")
            delta = int(req.get("requested_qty", 0))
            curr_item = (
                supabase.table("inventory")
                .select("quantity")
                .eq("id", art_id)
                .execute()
            )
            if curr_item.data:
              old_q = int(curr_item.data[0]["quantity"])
              new_q = (
                  old_q + delta
                  if req.get("req_type") == "Zuwachs"
                  else max(0, old_q - delta)
              )
              supabase.table("inventory").update({"quantity": new_q}).eq(
                  "id", art_id
              ).execute()
            supabase.table("agent_requests").update(
                {"status": "genehmigt"}
            ).eq("id", req["id"]).execute()
            st.success("Anfrage genehmigt!")
            st.rerun()
          if col_app2.button("Ablehnen", key=f"rej_{req['id']}"):
            supabase.table("agent_requests").update(
                {"status": "abgelehnt"}
            ).eq("id", req["id"]).execute()
            st.warning("Anfrage abgelehnt.")
            st.rerun()
  except Exception as e:
    pass

# --- SEITENMENÜ JE NACH ROLLE (ALLE 10 MENÜPUNKTE VORHANDEN) ---
st.sidebar.header("⚙️ Lagersteuerung")

if current_role == "Manager":
  menu_options = [
      "📊 Bestände anzeigen",
      "➕ Artikel hinzufügen",
      "📉 Artikel reduzieren (Verkauf)",
      "📥 Massen-Wareneingang (Zuwachs)",
      "📥 Auto-Abverkauf per Bericht",
      "📦 Automatischer Bestellvorschlag",
      "📁 Katalog & Min/Max hochladen",
      "📷 Live-Kamera-Scanner",
      "🖨 Etiketten drucken",
      "📱 QR-Code für Kollegen",
  ]
else:
  menu_options = [
      "📊 Bestände anzeigen",
      "➕ Artikel hinzufügen",
      "📉 Artikel reduzieren (Verkauf)",
      "📥 Massen-Wareneingang (Zuwachs)",
      "📷 Live-Kamera-Scanner",
      "🖨 Etiketten drucken",
  ]

action = st.sidebar.radio("Aktion auswählen:", menu_options)


# Hilfsfunktion zur präzisen Suche
def search_items(dataframe, query):
  if dataframe.empty or not query:
    return dataframe
  q = str(query).strip().lower()
  q_raw = str(query).strip()

  mask = (
      dataframe["name"].astype(str).str.lower().str.contains(q, na=False)
      | dataframe["barcode"].astype(str).str.strip() == q_raw
      | dataframe["sap"].astype(str).str.strip() == q_raw
      | dataframe["article"].astype(str).str.strip().str.lower() == q
  )
  return dataframe[mask]


# Funktion für Kamera-Widget
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
  st.header("📋 Aktuelles Sortiment & Bestände (inkl. Min/Max)")

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
  st.header("✨ Neuen Artikel hinzufügen oder Bestand anpassen")

  with st.form("search_add_form"):
    add_search = st.text_input(
        "🔍 Artikel suchen (Name, Artikel, SAP oder Barcode):",
        placeholder="Eingeben...",
    )
    add_submitted = st.form_submit_button("Artikel suchen")

  if add_submitted or "add_search_query" not in st.session_state:
    st.session_state["add_search_query"] = add_search

  active_add_search = st.session_state.get("add_search_query", "")

  (
      pre_article,
      pre_name,
      pre_brand,
      pre_sap,
      pre_barcode,
      pre_preis,
      pre_location,
      pre_qty,
      pre_min,
      pre_max,
  ) = ("", "", "Iittala", "", "", 0.0, "Etage 5 Lager", 0, 0, 0)

  if active_add_search and not df.empty:
    found_items = search_items(df, active_add_search)
    if not found_items.empty:
      item = found_items.iloc[0]
      st.success(
          f"📦 Gefunden: **{item.get('name')}** (Aktueller Bestand:"
          f" **{int(item.get('quantity', 0))} Stk.**)"
      )
      (
          pre_article,
          pre_name,
          pre_brand,
          pre_sap,
          pre_barcode,
          pre_preis,
          pre_location,
          pre_qty,
          pre_min,
          pre_max,
      ) = (
          str(item.get("article", "")),
          str(item.get("name", "")),
          str(item.get("brand", "Iittala")),
          str(item.get("sap", "")),
          str(item.get("barcode", "")),
          float(item.get("preis", 0.0)),
          str(item.get("location", "Etage 5 Lager")),
          int(item.get("quantity", 0)),
          int(item.get("min_qty", 0)),
          int(item.get("max_qty", 0)),
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
        "Menge (Bestand)", min_value=0, value=pre_qty, step=1
    )
    col_minmax1, col_minmax2 = st.columns(2)
    new_min = col_minmax1.number_input(
        "Min. Bestand (Soll)", min_value=0, value=pre_min, step=1
    )
    new_max = col_minmax2.number_input(
        "Max. Bestand (Soll)", min_value=0, value=pre_max, step=1
    )

    new_location = st.text_input("Lagerort", value=pre_location)
    new_preis = st.number_input(
        "Preis (€)", min_value=0.0, value=pre_preis, format="%.2f"
    )
    new_sap = st.text_input("SAP-Nummer", value=pre_sap)
    new_barcode = st.text_input("Barcode", value=pre_barcode)

    submit_label = (
        "Speichern / Aktualisieren"
        if current_role == "Manager"
        else "Änderung zur Freigabe einreichen"
    )
    if st.form_submit_button(submit_label):
      if not new_name:
        st.error("Bitte Artikelnamen eingeben.")
      elif current_role == "Manager":
        if supabase is not None:
          try:
            data = {
                "article": str(new_article),
                "name": str(new_name),
                "brand": str(new_brand),
                "quantity": int(new_qty),
                "min_qty": int(new_min),
                "max_qty": int(new_max),
                "location": str(new_location),
                "preis": float(new_preis),
                "sap": str(new_sap),
                "barcode": str(new_barcode),
            }
            existing = (
                supabase.table("inventory")
                .select("id")
                .eq("article", str(new_article))
                .execute()
            )
            if existing.data and len(existing.data) > 0:
              supabase.table("inventory").update(data).eq(
                  "article", str(new_article)
              ).execute()
            else:
              supabase.table("inventory").insert(data).execute()
            st.success("✅ Erfolgreich gespeichert!")
            st.rerun()
          except Exception as e:
            st.error(f"Fehler: {e}")
      else:
        if supabase is not None:
          try:
            supabase.table("agent_requests").insert({
                "article_name": new_name,
                "requested_qty": int(new_qty),
                "req_type": "Artikel Hinzufügen/Ändern",
                "status": "ausstehend",
            }).execute()
            st.success("📤 Anfrage an den Manager zur Freigabe gesendet!")
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

        submit_btn_text = (
            "Verkauf bestätigen"
            if current_role == "Manager"
            else "Verkauf anfragen"
        )
        if st.form_submit_button(submit_btn_text):
          if current_role == "Manager":
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
          else:
            if supabase is not None:
              try:
                supabase.table("agent_requests").insert({
                    "inventory_id": selected_row["id"],
                    "article_name": selected_row["name"],
                    "requested_qty": int(reduce_qty),
                    "req_type": "Verkauf",
                    "status": "ausstehend",
                }).execute()
                st.success(
                    "📤 Verkaufsanfrage zur Freigabe an Manager gesendet!"
                )
              except Exception as e:
                st.error(f"Fehler: {e}")

# 4. MASSEN-WARENEINGANG (ZUWACHS)
elif action == "📥 Massen-Wareneingang (Zuwachs)":
  st.header("📥 Massen-Wareneingang / Bestand erhöhen")
  with st.form("search_incoming_form"):
    inc_search = st.text_input("🔍 Artikel suchen:", placeholder="Eingeben...")
    inc_submitted = st.form_submit_button("Suchen")

  if inc_submitted or "inc_search_query" not in st.session_state:
    st.session_state["inc_search_query"] = inc_search

  active_inc_search = st.session_state.get("inc_search_query", "")

  if not df.empty:
    inc_df = df
    if active_inc_search:
      inc_df = search_items(df, active_inc_search)

    if not inc_df.empty:
      inc_options = [
          f"{r.get('name')} | Art: {r.get('article')} | SAP: {r.get('sap')} (Bestand: {int(r.get('quantity', 0))})"
          for _, r in inc_df.iterrows()
      ]
      with st.form("incoming_form"):
        sel_inc = st.selectbox("Artikel auswählen:", inc_options)
        sel_row = inc_df.iloc[inc_options.index(sel_inc)]
        add_q = st.number_input(
            "Anzahl Wareneingang (hinzufügen):", min_value=1, value=1
        )

        btn_txt = (
            "Wareneingang buchen"
            if current_role == "Manager"
            else "Wareneingang anfragen"
        )
        if st.form_submit_button(btn_txt):
          cur_q = int(sel_row.get("quantity", 0))
          if current_role == "Manager":
            new_q = cur_q + int(add_q)
            if supabase is not None:
              supabase.table("inventory").update({"quantity": new_q}).eq(
                  "id", sel_row["id"]
              ).execute()
              st.success(f"✅ Bestand erhöht! Neuer Bestand: {new_q} Stk.")
              st.rerun()
          else:
            if supabase is not None:
              supabase.table("agent_requests").insert({
                  "inventory_id": sel_row["id"],
                  "article_name": sel_row["name"],
                  "requested_qty": int(add_q),
                  "req_type": "Zuwachs",
                  "status": "ausstehend",
              }).execute()
              st.success("📤 Wareneingang zur Freigabe an Manager gesendet!")

# 5. AUTO-ABVERKAUF PER BERICHT
elif action == "📥 Auto-Abverkauf per Bericht":
  st.header("📥 Automatische Bestandsaktualisierung per Verkaufsbericht")
  sales_file = st.file_uploader(
      "Verkaufsbericht-Datei auswählen", type=["xlsx", "csv"], key="sales_upload"
  )

  if sales_file is not None:
    try:
      file_bytes = sales_file.getvalue()
      file_hash = hashlib.md5(file_bytes).hexdigest()

      if "processed_files" not in st.session_state:
        st.session_state["processed_files"] = set()

      if file_hash in st.session_state["processed_files"]:
        st.error("🚫 Diese Datei wurde bereits verarbeitet.")
      else:
        if sales_file.name.endswith(".csv"):
          sales_df = pd.read_csv(io.BytesIO(file_bytes))
        else:
          sales_df = pd.read_excel(io.BytesIO(file_bytes))

        st.write("📋 Vorschau:", sales_df.head())
        cols_lower = {c.lower().strip(): c for c in sales_df.columns}

        art_col = next(
            (
                cols_lower[k]
                for k in [
                    "article",
                    "art-nr",
                    "artikelnr",
                    "artikel",
                    "sap",
                    "sku",
                    "barcode",
                ]
                if k in cols_lower
            ),
            None,
        )
        qty_col = next(
            (
                cols_lower[k]
                for k in ["quantity", "qty", "menge", "sold", "anzahl", "verkauf"]
                if k in cols_lower
            ),
            None,
        )

        if not art_col or not qty_col:
          st.error("❌ Spalten konnten nicht ermittelt werden.")
        else:
          if st.button("🚀 Automatisches Abschreiben starten"):
            updated_count = 0
            for _, row in sales_df.iterrows():
              item_id_val = str(row[art_col]).strip()
              sold_qty = int(pd.to_numeric(row[qty_col], errors="coerce") or 0)
              if sold_qty <= 0 or not item_id_val:
                continue

              matched = df[
                  (df["article"].astype(str).str.strip() == item_id_val)
                  | (df["sap"].astype(str).str.strip() == item_id_val)
              ]
              if not matched.empty:
                db_item = matched.iloc[0]
                new_q = max(0, int(db_item["quantity"]) - sold_qty)
                if supabase is not None:
                  supabase.table("inventory").update(
                      {"quantity": int(new_q)}
                  ).eq("id", db_item["id"]).execute()
                  updated_count += 1

            st.session_state["processed_files"].add(file_hash)
            st.success(f"✅ Aktualisierte Artikel: {updated_count}")
    except Exception as e:
      st.error(f"Fehler: {e}")

# 6. AUTOMATISCHER BESTELLVORSCHLAG
elif action == "📦 Automatischer Bestellvorschlag":
  st.header("📦 Automatischer Bestellvorschlag (Min/Max)")
  if df.empty:
    st.warning("Keine Daten vorhanden.")
  else:
    order_df = df[df["quantity"] < df["min_qty"]].copy()
    if order_df.empty:
      st.success(
          "✅ Alle Bestände sind im grünen Bereich! Keine Nachbestellungen"
          " nötig."
      )
    else:
      order_df["Bestellmenge"] = order_df["max_qty"] - order_df["quantity"]
      st.warning(
          f"⚠ {len(order_df)} Artikel unterschreiten den Mindestbestand!"
      )
      st.dataframe(
          order_df[
              [
                  "article",
                  "name",
                  "brand",
                  "quantity",
                  "min_qty",
                  "max_qty",
                  "Bestellmenge",
                  "preis",
              ]
          ],
          use_container_width=True,
      )

      out_buf = io.BytesIO()
      with pd.ExcelWriter(out_buf, engine="openpyxl") as writer:
        order_df.to_excel(writer, index=False, sheet_name="Bestellliste")
      st.download_button(
          label="📥 Bestellvorschlag als Excel herunterladen",
          data=out_buf.getvalue(),
          file_name="KaDeWe_Bestellvorschlag.xlsx",
          mime=(
              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          ),
      )

# 7. KATALOG & MIN/MAX HOCHLADEN
elif action == "📁 Katalog & Min/Max hochladen":
  st.header("📂 Massen-Upload (Katalog & Min/Max)")
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
        upload_df = upload_df.drop_duplicates(subset=["article"], keep="last")

      st.write("Vorschau:", upload_df.head())

      if st.button("Daten in Supabase importieren"):
        if supabase is not None:
          for col in ["quantity", "min_qty", "max_qty"]:
            if col in upload_df.columns:
              upload_df[col] = (
                  pd.to_numeric(upload_df[col], errors="coerce")
                  .fillna(0)
                  .astype(int)
              )
            else:
              upload_df[col] = 0
          upload_df["preis"] = pd.to_numeric(
              upload_df.get("preis", 0.0), errors="coerce"
          ).fillna(0.0)

          for col in ["article", "name", "brand", "location", "sap", "barcode"]:
            if col in upload_df.columns:
              upload_df[col] = upload_df[col].fillna("").astype(str)
            else:
              upload_df[col] = ""

          records = upload_df.to_dict(orient="records")
          success_count = 0
          for rec in records:
            art = rec.get("article")
            try:
              existing = (
                  supabase.table("inventory")
                  .select("id")
                  .eq("article", art)
                  .execute()
              )
              if existing.data and len(existing.data) > 0:
                supabase.table("inventory").update(rec).eq(
                    "article", art
                ).execute()
              else:
                supabase.table("inventory").insert(rec).execute()
              success_count += 1
            except Exception:
              pass
          st.success(f"✅ Import erfolgreich! Datensätze: {success_count}")
          st.rerun()
    except Exception as e:
      st.error(f"Fehler: {e}")

# 8. LIVE-KAMERA-SCANNER
elif action == "📷 Live-Kamera-Scanner":
  st.header("📷 Live-Barcode-Scanner")
  camera_on = st.checkbox("🟢 Live-Kamera aktivieren", value=True)
  if camera_on:
    render_camera_scanner_widget("main")
  else:
    st.info("⏸️ Kamera aus.")

  st.markdown("---")
  scanned_input = st.text_input(
      "Gescannter Barcode, SAP-Nummer, Artikel oder Name manuell eingeben:",
      key="scanner_input_field",
  )

  if scanned_input and not df.empty:
    matched = search_items(df, scanned_input)
    if not matched.empty:
      item = matched.iloc[0]
      st.success(f"📦 Gefunden: **{item.get('name')}**")
      st.write(
          f"Bestand: {int(item.get('quantity', 0))} Stk. | Preis:"
          f" {item.get('preis', 0.0):.2f} € | SAP: {item.get('sap', '-')}"
      )

# 9. ETIKETTEN DRUCKEN
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

      label_html = f"""
            <div id="printable-label" style="border: 1px solid #000; width: 4cm; height: 1.4cm; padding: 2px; box-sizing: border-box; background: white; color: black; display: flex; flex-direction: column; justify-content: space-between; font-family: Arial, sans-serif;">
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
            <br>
            <button onclick="window.print();" style="background-color: #ff4b4b; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-weight: bold;">🖨 Etikett jetzt drucken</button>
            """
      components.html(label_html, height=150)

# 10. QR-CODE FÜR KOLLEGEN
elif action == "📱 QR-Code für Kollegen":
  st.header("📱 App-Zugang für das Team")
  st.write("Scannen Sie diesen QR-Code mit einem Smartphone:")
  app_url = "https://mtcbfvpjnxlkvvtuknyv.streamlit.app"
  qr_code_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={urllib.parse.quote(app_url)}"
  st.image(qr_code_url, width=300)
  st.markdown(f"Direktlink: [{app_url}]({app_url})")
