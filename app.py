# Copyright (c) 2026 Maria Jentzsch. All rights reserved.
# IQBestandPro™ — Proprietary Software.
import pandas as pd
import plotly.express as px
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
import streamlit as st

# ==========================================
# 📊 IQBestandPro - Konfiguration & Setup
# ==========================================
st.set_page_config(
    page_title="IQBestandPro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Hauptüberschrift der Anwendung
st.title("📊 IQBestandPro")
st.caption("Intelligentes Bestandsmanagement & Filialanalytik")
# ==========================================
# СТИЛИЗАЦИЯ ПОД СТИЛЬ FISKARS / IITTALA / ROYAL COPENHAGEN
# ==========================================
st.markdown("""
<style>
    /* Общий фон приложения (светлый, чистый скандинавский стиль) */
    .stApp {
        background-color: #F8F9FA;
        color: #1A1A1A;
    }
    
    /* Стилизация заголовков под премиальный бренд */
    h1, h2, h3 {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        color: #0F2537; /* Глубокий темно-синий в стиле Royal Copenhagen */
        font-weight: 500;
    }
    
    /* Оформление блоков с информацией (st.info) */
    div.stInfo {
        background-color: #E8F1F5;
        border-left: 4px solid #1B4965;
        color: #1A1A1A;
    }
    
    /* Кнопки в фирменном сдержанном стиле */
    .stButton>button {
        background-color: #1B4965;
        color: white;
        border-radius: 4px;
        border: none;
        font-weight: 500;
        padding: 0.5rem 1rem;
        transition: background-color 0.2s ease;
    }
    
    .stButton>button:hover {
        background-color: #112F41;
        color: white;
    }
    
    /* Карточки/формы */
    div[data-testid="stForm"] {
        background-color: #FFFFFF;
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        border: 1px solid #E2E8F0;
    }
</style>
""", unsafe_allow_html=True)

SUPABASE_URL = "https://mtcbfvpjnxlkvvtuknyv.supabase.co"
SUPABASE_KEY = "sb_publishable_wChGuVU2FeW23S2bqdYqOg_B9-oMoKs"

supabase = None
try:
  supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
  pass

# =========================================================
# 📢 НОВОСТНОЙ / АКЦИОННЫЙ БАННЕР (NEWS BANNER)
# =========================================================
try:
    # Запрашиваем последнюю новость из таблицы news
    res_news = supabase.table("news").select("*").order("created_at", desc=True).limit(1).execute()
    news_data = res_news.data if res_news and res_news.data else []
    
    if news_data:
        banner_text = news_data[0].get("message", "")
    else:
        # Текст по умолчанию, если таблица пустая
        banner_text = "🔥 **Aktuelle Aktion:** Royal Copenhagen & Iittala Sonderverkauf – Reduzierte Artikel bis zu -20%!"
        
    if banner_text:
        st.warning(f"📢 **Wichtige Information / Aktion:** {banner_text}")

except Exception:
    # Запасной вариант на случай, если таблицы news нет в базе
    st.warning("📢 **Wichtige Information / Aktion:** 🔥 **Aktuelle Aktion:** Royal Copenhagen & Iittala Sonderverkauf – Reduzierte Artikel bis zu -20%!")
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

  st.subheader("🔐 Anmeldung / Login")
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
# =========================================================
# 🌐 МУЛЬТИЯЗЫЧНОСТЬ И ЕДИНОЕ МЕНЮ (LANGUAGE & NAVIGATION)
# =========================================================
lang = st.sidebar.selectbox(
    "🌐 Sprache / Language / Язык",
    ["DE", "EN", "RU"],
    index=0
)

TEXTS = {
    "DE": {
        "header": "📊 Lagerbestand, Umsatz & Top-Seller",
        "tab_inv": "🏷️ Bestände nach Marken (Stk.)",
        "tab_rev": "💰 Umsatz nach Marken (€)",
        "tab_top": "🔝 Bestseller / Top-Verkäufe",
        "inv_title": "Gesamte Stückzahl im Lager nach Marken",
        "inv_tbl_title": "Bestandsübersicht in Stück:",
        "brand": "Marke",
        "quantity": "Stückzahl (Stk.)",
        "rev_title": "Monatlicher Umsatz nach Marken laut Barcode (€)",
        "monat": "Monat",
        "umsatz": "Umsatz (€)",
        "top_title": "🔥 Top 10 meistverkaufte Artikel",
        "top_col_art": "Artikel / Bezeichnung",
        "top_col_qty": "Verkaufte Stk.",
        "no_inv": "Keine Artikel in der Datenbank vorhanden.",
        "no_sales": "Keine Verkaufsdaten vorhanden.",
        "logged_as": "Angemeldet als",
        "role": "Rolle",
        "logout": "Abmelden",
        "nav_header": "Lagersteuerung",
        "nav_action_label": "Aktion auswählen:",
        "opt_show": "📊 Bestände anzeigen",
        "opt_add": "➕ Artikel hinzufügen",
        "opt_reduce": "📉 Artikel reduzieren (Verkauf)",
        "opt_intake": "📦 Massen-Wareneingang (Zuwachs)",
        "opt_report": "📊 Auto-Abverkauf per Bericht",
        "opt_catalog": "📁 Katalog aus Datei",
        "opt_scanner": "📷 Live-Kamera-Scanner",
        "opt_labels": "🖨️ Etiketten drucken",
        "opt_inventur": "📋 Inventur-Schnelleingabe",
        "opt_qr": "📲 QR-Code für Kollegen"
    },
    "EN": {
        "header": "📊 Inventory, Revenue & Top Sellers",
        "tab_inv": "🏷️ Stock by Brand (pcs)",
        "tab_rev": "💰 Revenue by Brand (€)",
        "tab_top": "🔝 Bestsellers / Top Sales",
        "inv_title": "Total Quantity in Stock by Brand",
        "inv_tbl_title": "Stock Overview in Pieces:",
        "brand": "Brand",
        "quantity": "Quantity (pcs)",
        "rev_title": "Monthly Revenue by Brand via Barcode (€)",
        "monat": "Month",
        "umsatz": "Revenue (€)",
        "top_title": "🔥 Top 10 Best-Selling Items",
        "top_col_art": "Item / Description",
        "top_col_qty": "Sold (pcs)",
        "no_inv": "No items found in the database.",
        "no_sales": "No sales data available.",
        "logged_as": "Logged in as",
        "role": "Role",
        "logout": "Log out",
        "nav_header": "Inventory Control",
        "nav_action_label": "Select action:",
        "opt_show": "📊 View inventory",
        "opt_add": "➕ Add item",
        "opt_reduce": "📉 Reduce item (Sale)",
        "opt_intake": "📦 Bulk goods receipt",
        "opt_report": "📊 Auto-sales report",
        "opt_catalog": "📁 Catalog from file",
        "opt_scanner": "📷 Live Camera Scanner",
        "opt_labels": "🖨️ Print Labels",
        "opt_inventur": "📋 Quick Inventory Entry",
        "opt_qr": "📲 QR Code for Colleagues"
    },
    "RU": {
        "header": "📊 Остатки, Выручка и Топ Продаж",
        "tab_inv": "🏷️ Остатки по брендам (шт.)",
        "tab_rev": "💰 Выручка по брендам (€)",
        "tab_top": "🔝 Бестселлеры / Топ продаж",
        "inv_title": "Общее количество на складе по брендам",
        "inv_tbl_title": "Обзор остатков в штуках:",
        "brand": "Бренд",
        "quantity": "Количество (шт.)",
        "rev_title": "Ежемесячная выручка по брендам по штрихкоду (€)",
        "monat": "Месяц",
        "umsatz": "Выручка (€)",
        "top_title": "🔥 Топ-10 самых продаваемых товаров",
        "top_col_art": "Товар / Наименование",
        "top_col_qty": "Продано (шт.)",
        "no_inv": "В базе данных нет товаров.",
        "no_sales": "Нет данных о продажах.",
        "logged_as": "Вы вошли как",
        "role": "Роль",
        "logout": "Выйти",
        "nav_header": "Управление складом",
        "nav_action_label": "Выберите действие:",
        "opt_show": "📊 Показать остатки",
        "opt_add": "➕ Добавить товар",
        "opt_reduce": "📉 Списать товар (Продажа)",
        "opt_intake": "📦 Массовый приход товара",
        "opt_report": "📊 Авто-списание по отчету",
        "opt_catalog": "📁 Каталог из файла",
        "opt_scanner": "📷 Сканер штрихкодов",
        "opt_labels": "🖨️ Печать этикеток",
        "opt_inventur": "📋 Быстрый ввод инвентаризации",
        "opt_qr": "📲 QR-код для коллег"
    }
}

t = TEXTS.get(lang, TEXTS["DE"])
# Подсчет незавершенных запросов от агентов
pending_count = 0
if st.session_state.get("role") == "manager" and supabase is not None:
    try:
        res = supabase.table("approvals").select("*", count="exact").eq("status", "pending").execute()
        pending_count = res.count if res.count is not None else len(res.data)
    except Exception:
        pending_count = 0

if pending_count > 0:
    st.sidebar.error(f"🔔 **{pending_count}** {t.get('opt_pending', 'Anfragen von Agenten')}")
# Вывод информации о пользователе с переводом
st.sidebar.markdown(f"👤 **{t['logged_as']}:** {st.session_state.get('user_name', 'User')}")
st.sidebar.markdown(f"🏷️ **{t['role']}:** {st.session_state.get('role', 'User')}")

if st.sidebar.button(f"🚪 {t['logout']}"):
    st.session_state["logged_in"] = False
    st.session_state["role"] = None
    st.session_state["user_name"] = None
    st.rerun()

# Единое переводимое меню управления складом
st.sidebar.markdown(f"### ⚙️ {t['nav_header']}")

menu_options = [
    t["opt_show"],
    t["opt_add"],
    t["opt_reduce"],
    t["opt_intake"],
    t["opt_report"],
    t["opt_catalog"],
    t["opt_scanner"],
    t["opt_labels"],
    t["opt_inventur"],
    t["opt_qr"]
]

action = st.sidebar.radio(t["nav_action_label"], menu_options)
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
                        not_found_codes = []

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
                                item_brand = item_db.get("brand", "Unbekannt")
                                item_price = float(item_db.get("preis", item_db.get("price", 0.0)))
                                curr_q = int(item_db.get("quantity", 0))
                                new_q = max(0, curr_q - sold_qty)
                                
                                res = supabase.table("inventory").update({"quantity": new_q}).eq("id", item_id).execute()
                                if res.data:
                                    success_count += 1
                                    
                                    # 📌 Автоматическая запись продажи в таблицу sales для аналитики по брендам
                                    try:
                                        supabase.table("sales").insert({
                                            "sap_number": str(code),
                                            "brand": str(item_brand),
                                            "quantity": int(sold_qty),
                                            "revenue": sold_qty * item_price,
                                            "sale_date": str(pd.Timestamp.today().date())
                                        }).execute()
                                    except Exception as db_err:
                                        print(f"Sales insert error: {db_err}")

                                    updated_details.append({
                                        "Artikel": item_name,
                                        "Code": code,
                                        "Verkauft": sold_qty,
                                        "Alter Bestand": curr_q,
                                        "Neuer Bestand": new_q
                                    })
                            else:
                                not_found_codes.append(code)

                        # Красивый блок подтверждения
                        st.success(f"✅ Verkaufsbericht erfolgreich verarbeitet! Bestände für **{success_count}** Artikel aktualisiert.")
                        
                        if updated_details:
                            st.markdown("### 📊 Details zur Bestandsreduzierung:")
                            st.dataframe(pd.DataFrame(updated_details), use_container_width=True)

                        if not_found_codes:
                            missing_str = ", ".join(not_found_codes)
                            st.warning(f"⚠️ **{len(not_found_codes)}** Position(en) wurden in der Datenbank nicht gefunden und übersprunken. **Fehlende SAP/Code(s):** {missing_str}")
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

# ==========================================
# KOMPLETT-BLOCK: MIN/MAX UPLOAD & AUTOMATISCHE BESTELLUNG
# ==========================================

st.sidebar.markdown("---")
st.sidebar.subheader("📦 Automatische Bestellung & Min/Max")

# 1. Sektion: Min/Max-Werte per Excel aktualisieren
st.sidebar.markdown("**1. Min/Max-Werte per Excel aktualisieren**")
uploaded_minmax = st.sidebar.file_uploader(
    "Excel-Datei (article/sap, min_stock, max_stock) hochladen", 
    type=["xlsx", "xls"],
    key="minmax_uploader_pagination_fix"
)

if uploaded_minmax is not None:
  try:
    update_df = pd.read_excel(uploaded_minmax)
    # Alle Spaltennamen in Kleinbuchstaben umwandeln
    update_df.columns = [str(c).strip().lower() for c in update_df.columns]
    
    st.sidebar.success(f"Datei geladen! Zeilen: {len(update_df)}")
    
    if st.sidebar.button("💾 In Datenbank speichern", key="btn_save_minmax_db_pagination_fix"):
      success_count = 0
      error_count = 0
      not_found_count = 0
      
      # Загружаем ВСЮ базу данных с помощью постраничной пагинации (обход лимитов Supabase)
      all_db_rows = []
      page_size = 1000
      start = 0
      
      try:
          while True:
              response = supabase.table("inventory").select("id, sap, article").range(start, start + page_size - 1).execute()
              if not response.data:
                  break
              all_db_rows.extend(response.data)
              if len(response.data) < page_size:
                  break
              start += page_size
      except Exception as e:
          st.sidebar.error(f"Fehler beim Laden der DB: {e}")

      sap_to_id = {}
      article_to_id = {}
      for item in all_db_rows:
          db_sap = str(item.get("sap", "")).strip()
          if "." in db_sap:
              db_sap = db_sap.split(".")[0]
          db_art = str(item.get("article", "")).strip()
          if "." in db_art:
              db_art = db_art.split(".")[0]
              
          item_id = item.get("id")
          
          if db_sap and db_sap != "None":
              sap_to_id[db_sap] = item_id
              try:
                  sap_to_id[str(int(db_sap))] = item_id
              except:
                  pass
                  
          if db_art and db_art != "None":
              article_to_id[db_art] = item_id
              try:
                  article_to_id[str(int(db_art))] = item_id
              except:
                  pass

      # Zeilen aus Excel durchgehen und abgleichen
      for _, row in update_df.iterrows():
        try:
          raw_code = row.get("sap", row.get("article", ""))
          if pd.isna(raw_code):
              continue
          
          code_val = str(raw_code).strip()
          if "." in code_val:
              code_val = code_val.split(".")[0]
          code_val = code_val.strip()

          min_val = int(row.get("min_stock", 0))
          max_val = int(row.get("max_stock", 0))
          
          if code_val and code_val != "nan":
            row_id = None
            try:
                int_code = str(int(float(code_val)))
                row_id = sap_to_id.get(int_code) or article_to_id.get(int_code)
            except:
                pass
                
            if not row_id:
                row_id = sap_to_id.get(code_val) or article_to_id.get(code_val)

            if row_id:
              supabase.table("inventory").update({
                  "min_stock": min_val,
                  "max_stock": max_val
              }).eq("id", row_id).execute()
              
              success_count += 1
            else:
              not_found_count += 1
          else:
            error_count += 1
        except Exception as e:
          error_count += 1
          
      st.sidebar.success(f"Aktualisiert: {success_count}")
      if not_found_count > 0:
        st.sidebar.warning(f"Nicht in DB gefunden: {not_found_count}")
      if error_count > 0:
        st.sidebar.error(f"Fehlerhafte Zeilen: {error_count}")
        
      if success_count > 0:
        st.success("Änderungen gespeichert! Aktualisiere Ansicht...")
        st.rerun()
      
  except Exception as e:
    st.sidebar.error(f"Fehler beim Verlesen der Datei: {e}")

st.sidebar.markdown("---")

# 2. Sektion: Nachbestellung prüfen und generieren
st.sidebar.markdown("**2. Nachbestellung ausführen**")
if st.sidebar.button("🚀 Nachbestellung prüfen", key="btn_nachbestellung_pruefen_pagination_fix"):
  if df.empty:
    st.sidebar.warning("⚠️ Keine Daten im Bestand gefunden.")
  else:
    check_df = df.copy()
    check_df["quantity"] = pd.to_numeric(check_df["quantity"], errors="coerce").fillna(0)
    
    if "min_stock" not in check_df.columns:
      check_df["min_stock"] = 2
    if "max_stock" not in check_df.columns:
      check_df["max_stock"] = 10

    check_df["min_stock"] = pd.to_numeric(check_df["min_stock"], errors="coerce").fillna(2)
    check_df["max_stock"] = pd.to_numeric(check_df["max_stock"], errors="coerce").fillna(10)

    active_check_df = check_df[check_df["min_stock"] > 0]
    reorder_df = active_check_df[active_check_df["quantity"] <= active_check_df["min_stock"]].copy()

    if reorder_df.empty:
      st.sidebar.success("✅ Alle aktiven Artikel über ihrem Mindestbestand!")
    else:
      reorder_df["order_qty"] = reorder_df["max_stock"] - reorder_df["quantity"]
      reorder_df["order_qty"] = reorder_df["order_qty"].apply(lambda x: max(1, x))
      
      st.sidebar.error(f"🚨 {len(reorder_df)} Artikel unter Minimum!")
      
      st.markdown("---")
      st.header("🚨 Automatische Bestellliste (nach Min/Max-Werten)")
      st.markdown("Folgende Artikel haben ihren **individuellen Mindestbestand** unterschritten:")
      
      display_cols = [c for c in ["article", "name", "brand", "quantity", "min_stock", "max_stock", "order_qty", "sap", "preis"] if c in reorder_df.columns]
      st.dataframe(reorder_df[display_cols], use_container_width=True)

      out_excel = io.BytesIO()
      with pd.ExcelWriter(out_excel, engine="openpyxl") as writer:
        reorder_df[display_cols].to_excel(writer, index=False, sheet_name="Bestellung")
      
      st.download_button(
          label="📥 Bestellliste als Excel herunterladen",
          data=out_excel.getvalue(),
          file_name="KaDeWe_Individuelle_Bestellung.xlsx",
          mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          key="download_reorder_excel_btn_pagination_fix"
      )
# ==========================================
# ==========================================
# AUTOMATISCHE MIN/MAX-BERECHNUNG NACH LAGERABGANG
# ==========================================

st.sidebar.markdown("---")
st.sidebar.subheader("📈 Intelligente Min/Max-Berechnung")

days_min = st.sidebar.slider("Reichweite in Tagen für MIN", 2, 14, 5, key="slider_days_min_v3")
days_max = st.sidebar.slider("Reichweite in Tagen für MAX", 10, 45, 20, key="slider_days_max_v3")

if st.sidebar.button("🚀 Automatische Neuberechnung starten", key="btn_neuberechnung_starten_v3"):
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

            try:
                current_qty = int(float(row.get("quantity", 0) or 0))
            except:
                current_qty = 0

            raw_last = row.get("last_quantity")
            
            # Если last_quantity пустой, сохраняем как целое число int
            if raw_last is None or pd.isna(raw_last) or str(raw_last).lower() == "none":
                try:
                    supabase.table("inventory").update({
                        "last_quantity": int(current_qty),
                        "last_check_date": today_str
                    }).eq("sap", sap_val).execute()
                    updated_count += 1
                except Exception as ex:
                    print(f"Fehler bei SAP {sap_val}: {ex}")
                continue

            try:
                last_qty = int(float(raw_last))
            except:
                last_qty = current_qty

            sold_amount = last_qty - current_qty

            if sold_amount > 0:
                daily_speed = sold_amount / 7
                new_min = max(2, int(daily_speed * days_min))
                new_max = max(new_min + 5, int(daily_speed * days_max))

                try:
                    supabase.table("inventory").update({
                        "min_stock": int(new_min),
                        "max_stock": int(new_max),
                        "last_quantity": int(current_qty), 
                        "last_check_date": today_str
                    }).eq("sap", sap_val).execute()
                    updated_count += 1
                except:
                    pass
            else:
                try:
                    supabase.table("inventory").update({
                        "last_quantity": int(current_qty),
                        "last_check_date": today_str
                    }).eq("sap", sap_val).execute()
                except:
                    pass

        st.sidebar.success(f"✅ Fertig! Aktualisiert/Initialisiert: {updated_count} Artikel")
        st.cache_data.clear()
        st.rerun()

# ==========================================
# UMSATZBERECHNUNG & AKKUMULATION (TAG & MONAT)
# ==========================================

st.sidebar.markdown("---")
st.sidebar.subheader("💶 Umsatz-Tracking (Tage & Monate)")

st.sidebar.markdown(
    "Laden Sie einen Verkaufsbericht hoch. Die Umsätze werden korrekt summiert, nach Marken aufgeschlüsselt und in Supabase gespeichert."
)

with st.sidebar.expander("ℹ️ Format-Hinweis"):
    st.markdown("""
    Ihre Datei sollte folgende Spalten enthalten:
    1. **Datum** (z. B. `02.10.2026`)
    2. **Barcode / Artikel / SAP** (zur Zuordnung der Marke)
    3. **Gesamtpreis / Umsatz** (oder Preis pro Zeile)
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

        # Нормализуем названия колонок для удобства поиска
        sales_report_df.columns = [str(c).strip().lower() for c in sales_report_df.columns]
        st.sidebar.success("✅ Bericht erfolgreich geladen!")

        columns_list = list(sales_report_df.columns)
        date_col = st.sidebar.selectbox("Spalte für das Datum", columns_list, key="acc_date_col")
        price_col = st.sidebar.selectbox("Spalte für Gesamtpreis / Umsatz", columns_list, key="acc_price_col")

        if st.sidebar.button("💾 Umsatz speichern & nach Marken aufteilen"):
            # Очищаем и суммируем общую сумму брутто
            cleaned_prices = (
                sales_report_df[price_col]
                .astype(str)
                .str.replace('€', '', regex=False)
                .str.replace(' ', '', regex=False)
                .str.replace(',', '.', regex=False)
            )
            sales_report_df['cleaned_price'] = pd.to_numeric(cleaned_prices, errors='coerce').fillna(0)
            total_brutto = sales_report_df['cleaned_price'].sum()

            sales_report_df[date_col] = pd.to_datetime(sales_report_df[date_col], errors='coerce')
            valid_dates = sales_report_df[date_col].dropna()
            
            if not valid_dates.empty:
                report_date = valid_dates.iloc[0].strftime('%Y-%m-%d')
                report_month = valid_dates.iloc[0].strftime('%Y-%m')
            else:
                report_date = pd.Timestamp.today().strftime('%Y-%m-%d')
                report_month = pd.Timestamp.today().strftime('%Y-%m')

            # 🏷️ Автоматическое распределение по брендам на основе каталога в Supabase
            brand_revenue_tracking = {}
            if supabase is not None:
                for _, row in sales_report_df.iterrows():
                    b_code = str(row.get("barcode", row.get("gtin", row.get("ean", "")))).strip()
                    a_code = str(row.get("article", row.get("artikelnr", row.get("sku", "")))).strip()
                    s_code = str(row.get("sap", "")).strip()
                    
                    line_price = float(row.get("cleaned_price", 0))
                    matched_brand = "Unbekannt"

                    # Ищем бренд по очереди: по баркоду, затем по артикулу, затем по SAP
                    inv_res = None
                    if b_code and b_code != "nan":
                        inv_res = supabase.table("inventory").select("brand").eq("barcode", b_code).execute()
                    if (not inv_res or not inv_res.data) and a_code and a_code != "nan":
                        inv_res = supabase.table("inventory").select("brand").eq("article", a_code).execute()
                    if (not inv_res or not inv_res.data) and s_code and s_code != "nan":
                        inv_res = supabase.table("inventory").select("brand").eq("sap", s_code).execute()

                    if inv_res and inv_res.data:
                        matched_brand = inv_res.data[0].get("brand", "Unbekannt")

                    brand_revenue_tracking[matched_brand] = brand_revenue_tracking.get(matched_brand, 0.0) + line_price

            # Сохранение общей суммы в Supabase (daily_sales)
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

            # 📊 Вывод распределения выручки по брендам прямо в боковой панели
            if brand_revenue_tracking:
                st.sidebar.markdown("**Umsatz nach Marken (dieser Bericht):**")
                for brand_name, b_rev in sorted(brand_revenue_tracking.items(), key=lambda x: x[1], reverse=True):
                    b_net = b_rev / 1.19
                    st.sidebar.markdown(f"• *{brand_name}*: **{b_net:,.2f} €** Netto *(Brutto: {b_rev:,.2f} €)*")

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

import streamlit as st

# ==========================================
# INVENTUR-SCHNELLEINGABE (MULTI-USER)
# ==========================================

st.markdown("---")
st.subheader("📦 Inventur-Schnelleingabe (Multi-User)")
st.caption("Geben Sie einen Suchbegriff oder SAP-Code ein, um den Bestand und alle Fundorte zu erfassen.")

# 1. Поиск товара по SAP или названию
search_query = st.text_input(
    "🔍 Artikel suchen (Name, SAP, Artikelnummer oder Barcode):",
    key="inventur_quick_search"
)

if search_query.strip():
    search_term = search_query.strip().lower()
    
    # Фильтрация датафрейма df (который загружен из Supabase)
    mask = (
        df['sap'].astype(str).str.lower().str.contains(search_term, na=False) |
        df['name'].astype(str).str.lower().str.contains(search_term, na=False) |
        df['barcode'].astype(str).str.lower().str.contains(search_term, na=False)
    )
    results = df[mask]
    
    st.write(f"Gefundene Artikel: {len(results)}")
    
    if not results.empty:
        # Берем первый найденный товар
        item = results.iloc[0]
        sap_val = str(item['sap'])
        current_qty = int(item['quantity']) if 'quantity' in item and not pd.isna(item['quantity']) else 0
        current_loc = str(item['location']) if 'location' in item and not pd.isna(item['location']) else "RC"
        
        # Разбираем текущую локацию на область и детали, если они записаны через пробел
        default_bereich = "Lager"
        default_detail = current_loc
        if " " in current_loc:
            parts = current_loc.split(" ", 1)
            default_bereich = parts[0]
            default_detail = parts[1]

        # Отображаем название и SAP
        col_info, col_qty, col_bereich, col_detail, col_btn = st.columns([3, 1.5, 2, 2, 1.5])
        
        with col_info:
            st.markdown(f"**{item['name']}**")
            st.caption(f"SAP: {sap_val}")
            
        with col_qty:
            # Управление количеством (Bestand)
            new_qty = st.number_input(
                "Bestand",
                min_value=0,
                value=current_qty,
                step=1,
                key=f"qty_{sap_val}"
            )
            
        with col_bereich:
            # Выбор области (Bereiche)
            bereich_options = ["Lager", "Shop", "Ex Sale", "Showroom", "Etage 5"]
            
            # Проверяем индекс по умолчанию
            default_index = 0
            if default_bereich in bereich_options:
                default_index = bereich_options.index(default_bereich)
                
            selected_bereich = st.selectbox(
                "Bereiche",
                options=bereich_options,
                index=default_index,
                key=f"bereich_{sap_val}"
            )
            
        with col_detail:
            # Детализация локации (Detail)
            selected_detail = st.text_input(
                "Detail (z.B. regal 3)",
                value=default_detail,
                key=f"detail_{sap_val}"
            )
            
        with col_btn:
            st.write("") # Смещение кнопки вниз
            st.write("")
            if st.button("💾 Speichern", key=f"save_btn_{sap_val}"):
                # Формируем итоговую строку местоположения
                final_location = f"{selected_bereich} {selected_detail}".strip()
                
                try:
                    # Обновляем запись в Supabase
                    supabase.table("inventory").update({
                        "quantity": new_qty,
                        "location": final_location
                    }).eq("sap", sap_val).execute()
                    
                    st.success(f"Gespeichert! ({final_location}, Qty: {new_qty})")
                    st.rerun() # Мгновенно перезагружаем данные
                except Exception as e:
                    st.error(f"Fehler beim Speichern: {e}")
# ==========================================
# SEKTION: WAREN IM ZULAUF / LIEFERUNG UPLOAD
# ==========================================
st.sidebar.markdown("---")
st.sidebar.subheader("🚚 Lieferung / Ware im Zulauf")

uploaded_incoming = st.sidebar.file_uploader(
    "Excel (sap, quantity/lieferung) hochladen", 
    type=["xlsx", "xls"],
    key="incoming_uploader_lieferung_v1"
)

if uploaded_incoming is not None:
    try:
        inc_df = pd.read_excel(uploaded_incoming)
        inc_df.columns = [str(c).strip().lower() for c in inc_df.columns]
        
        st.sidebar.success(f"Datei geladen! Zeilen: {len(inc_df)}")
        
        if st.sidebar.button("💾 Zulauf in DB speichern", key="btn_save_incoming_lieferung_db"):
            success_count = 0
            
            # Vollständiges Laden der DB über Pagination (Sicherheit gegen 1000er-Limit)
            all_db_rows = []
            page_size = 1000
            start = 0
            while True:
                resp = supabase.table("inventory").select("id, sap, article").range(start, start + page_size - 1).execute()
                if not resp.data:
                    break
                all_db_rows.extend(resp.data)
                if len(resp.data) < page_size:
                    break
                start += page_size

            sap_to_id = {}
            art_to_id = {}
            for item in all_db_rows:
                db_sap = str(item.get("sap", "")).strip().split(".")[0]
                db_art = str(item.get("article", "")).strip().split(".")[0]
                item_id = item.get("id")
                
                if db_sap and db_sap != "None":
                    sap_to_id[db_sap] = item_id
                if db_art and db_art != "None":
                    art_to_id[db_art] = item_id

            # Zeilen durchgehen und incoming_quantity aktualisieren
            for _, row in inc_df.iterrows():
                raw_sap = row.get("sap", "")
                if pd.isna(raw_sap):
                    continue
                
                sap_val = str(raw_sap).strip()
                if "." in sap_val:
                    sap_val = sap_val.split(".")[0]
                
                # Sichert die Entnahme aus quantity oder lieferung
                raw_qty = row.get("lieferung", row.get("quantity", 0))
                if pd.isna(raw_qty):
                    raw_qty = 0
                
                try:
                    qty_val = int(float(raw_qty))
                except:
                    qty_val = 0
                
                if sap_val and sap_val != "nan":
                    row_id = sap_to_id.get(sap_val)
                    if not row_id:
                        # Fallback auf integer-Umwandlung
                        try:
                            int_sap = str(int(float(sap_val)))
                            row_id = sap_to_id.get(int_sap)
                        except:
                            pass
                            
                    if row_id:
                        supabase.table("inventory").update({
                            "incoming_quantity": qty_val
                        }).eq("id", row_id).execute()
                        success_count += 1
                        
            st.sidebar.success(f"Aktualisiert (Zulauf): {success_count} Artikel")
            st.rerun()
            
    except Exception as e:
        st.sidebar.error(f"Fehler beim Verlesen der Excel-Datei: {e}")

# ==========================================
# SEKTION: WARENEINGANG BUCHEN (LIEFERUNG ANGEKOMMEN)
# ==========================================
st.sidebar.markdown("---")
st.sidebar.subheader("✅ Wareneingang buchen")

uploaded_received = st.sidebar.file_uploader(
    "Excel (angekommene Ware: sap, quantity/lieferung)", 
    type=["xlsx", "xls"],
    key="incoming_received_uploader_v1"
)

if uploaded_received is not None:
    try:
        rec_df = pd.read_excel(uploaded_received)
        rec_df.columns = [str(c).strip().lower() for c in rec_df.columns]
        
        st.sidebar.success(f"Eingang-Datei geladen! Zeilen: {len(rec_df)}")
        
        if st.sidebar.button("📦 Wareneingang in DB verbuchen", key="btn_save_wareneingang_db"):
            success_count = 0
            
            # Vollständiges Laden der DB über Pagination
            all_db_rows = []
            page_size = 1000
            start = 0
            while True:
                resp = supabase.table("inventory").select("id, sap, article, quantity, incoming_quantity").range(start, start + page_size - 1).execute()
                if not resp.data:
                    break
                all_db_rows.extend(resp.data)
                if len(resp.data) < page_size:
                    break
                start += page_size

            sap_to_item = {}
            for item in all_db_rows:
                db_sap = str(item.get("sap", "")).strip().split(".")[0]
                if db_sap and db_sap != "None":
                    sap_to_item[db_sap] = item

            for _, row in rec_df.iterrows():
                raw_sap = row.get("sap", "")
                if pd.isna(raw_sap):
                    continue
                
                sap_val = str(raw_sap).strip().split(".")[0]
                
                raw_qty = row.get("lieferung", row.get("quantity", 0))
                if pd.isna(raw_qty):
                    raw_qty = 0
                
                try:
                    delivered_qty = int(float(raw_qty))
                except:
                    delivered_qty = 0
                
                if sap_val and sap_val != "nan":
                    db_item = sap_to_item.get(sap_val)
                    if not db_item:
                        try:
                            int_sap = str(int(float(sap_val)))
                            db_item = sap_to_item.get(int_sap)
                        except:
                            pass
                            
                    if db_item:
                        item_id = db_item.get("id")
                        current_qty = int(db_item.get("quantity", 0) or 0)
                        current_incoming = int(db_item.get("incoming_quantity", 0) or 0)
                        
                        # Новый остаток = старый остаток + прибывший товар
                        new_qty = current_qty + delivered_qty
                        
                        # Убираем доставленное из пути (если пришло всё или часть)
                        new_incoming = max(0, current_incoming - delivered_qty)
                        
                        supabase.table("inventory").update({
                            "quantity": new_qty,
                            "incoming_quantity": new_incoming
                        }).eq("id", item_id).execute()
                        
                        success_count += 1
                        
            st.sidebar.success(f"Wareneingang gebucht: {success_count} Artikel aktualisiert!")
            st.rerun()
            
    except Exception as e:
        st.sidebar.error(f"Fehler beim Verarbeiten des Wareneingangs: {e}")

# ==========================================
# AKTIONSPREISE PER EXCEL HOCHLADEN (GEBUNDEN AN SAP)
# ==========================================

st.markdown("---")
st.subheader("🏷️ Aktionspreise nach SAP-Nummer hochladen")
st.markdown("Laden Sie eine Excel-Datei hoch, die die Spalten **sap**, **promo_price**, **promo_start** und **promo_end** enthält.")

uploaded_promo_file = st.file_uploader("Excel-Datei mit Aktionspreisen (.xlsx)", type=["xlsx", "xls"], key="uploader_promo_sap")

if uploaded_promo_file:
    try:
        promo_df = pd.read_excel(uploaded_promo_file)
        
        # Приводим названия колонок к нижнему регистру
        promo_df.columns = [str(c).strip().lower() for c in promo_df.columns]
        
        required_cols = ["sap", "promo_price", "promo_start", "promo_end"]
        if all(col in promo_df.columns for col in required_cols):
            updated_promos = 0
            for _, p_row in promo_df.iterrows():
                # Привязка strictly по SAP-номеру
                sap_val = str(p_row.get("sap", "")).strip()
                if not sap_val or sap_val.lower() == "nan":
                    continue
                
                try:
                    p_price = float(p_row.get("promo_price"))
                    p_start = str(p_row.get("promo_start")).split()[0]  # Формат YYYY-MM-DD
                    p_end = str(p_row.get("promo_end")).split()[0]      # Формат YYYY-MM-DD
                    
                    # Обновляем акционные данные по SAP
                    supabase.table("inventory").update({
                        "promo_price": p_price,
                        "promo_start": p_start,
                        "promo_end": p_end
                    }).eq("sap", sap_val).execute()
                    
                    updated_promos += 1
                except Exception as ex:
                    print(f"Fehler bei SAP {sap_val}: {ex}")
            
            st.success(f"✅ Aktionspreise für {updated_promos} SAP-Nummern erfolgreich gespeichert!")
            st.cache_data.clear()
            st.rerun()
        else:
            st.error("⚠ Die Excel-Datei muss unbedingt folgende Spalten enthalten: sap, promo_price, promo_start, promo_end")
    except Exception as e:
        st.error(f"Fehler beim Verarbeiten der Datei: {e}")

import pandas as pd
import numpy as np
import streamlit as st

# =========================================================
# ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ: ЗАЩИТА ОТ NaN / ПУСТЫХ ЯЧЕЕК
# =========================================================
def clean_val(val, default, val_type=str):
    if pd.isna(val) or val is None:
        return default
    try:
        return val_type(val)
    except:
        return default

# Определяем текущего пользователя и роль
current_role = st.session_state.get("user_role", "Agent")
current_user_name = st.session_state.get("username", "Unbekannt")

# =========================================================
# БЛОК 1: ПРОВЕРКА ЗАКАЗА И ДОБАВЛЕНИЕ НЕДОСТАЮЩИХ ТОВАРОВ
# =========================================================

st.markdown("---")
st.subheader("🔍 Abgleich: Bestellte Artikel ohne SAP im Bestand")
st.caption("Laden Sie eine Bestelldatei hoch, um neue Artikel zu prüfen und zuzuordnen.")

with st.container():
    order_file = st.file_uploader(
        "Bestelldatei auswählen (.xlsx oder .csv):",
        type=["xlsx", "csv"],
        key="missing_check_uploader"
    )

    if order_file is not None:
        try:
            if order_file.name.endswith(".csv"):
                df_order = pd.read_csv(order_file)
            else:
                df_order = pd.read_excel(order_file)

            df_order.columns = [str(c).strip().lower() for c in df_order.columns]

            if "sap" not in df_order.columns:
                st.error("❌ In der Datei fehlt die Spalte 'sap'.")
            else:
                db_saps = set(df['sap'].astype(str).str.strip().tolist()) if not df.empty else set()
                df_order['sap_clean'] = df_order['sap'].astype(str).str.strip()
                
                missing_df = df_order[~df_order['sap_clean'].isin(db_saps)].copy()

                if missing_df.empty:
                    st.success("✅ Alle bestellten Artikel sind bereits in der Bestandsdatenbank vorhanden!")
                else:
                    st.warning(f"⚠️ Es wurden **{len(missing_df)}** neue Positionen gefunden, die noch **nicht** in `inventory` existieren:")
                    
                    st.dataframe(
                        missing_df[['sap_clean'] + [c for c in missing_df.columns if c in ['name', 'brand', 'quantity', 'preis', 'barcode']]], 
                        use_container_width=True
                    )

                    st.markdown("### Status für den Import festlegen:")
                    import_status_choice = st.radio(
                        "Wie soll der Status / Lagerort für diese neuen Artikel gesetzt werden?",
                        options=[
                            "Bestellt (Unterwegs / Noch nicht eingetroffen)",
                            "Wareneingang / Unbekannt (Eingetroffen, aber noch nicht einsortiert)"
                        ],
                        key="import_status_radio"
                    )
                    
                    default_location_value = "Bestellt (Unterwegs)" if "Unterwegs" in import_status_choice else "Wareneingang (Unbekannt)"

                    action_tab1, action_tab2 = st.tabs(["⚡ Automatischer Import", "✏️ Manuelle Einzelerfassung"])

                    with action_tab1:
                        st.info(f"Fügt alle Positionen mit dem Status **'{default_location_value}'** hinzu.")
                        if st.button("🚀 Fehlende Artikel in inventory eintragen", key="btn_add_all_missing", type="primary"):
                            try:
                                new_records = []
                                for _, r in missing_df.iterrows():
                                    new_records.append({
                                        "sap": clean_val(r.get("sap_clean"), "", str),
                                        "name": clean_val(r.get("name", r.get("artikelname")), "Neuer Artikel", str),
                                        "brand": clean_val(r.get("brand", r.get("marke")), "Royal Copenhagen / Iittala", str),
                                        "quantity": clean_val(r.get("quantity", r.get("menge")), 0, int),
                                        "preis": clean_val(r.get("preis", r.get("price")), 0.0, float),
                                        "barcode": clean_val(r.get("barcode"), "", str),
                                        "location": default_location_value,
                                        "min_stock": 0,
                                        "max_stock": 0
                                    })

                                if "Agent" in current_role:
                                    res = supabase.table("pending_approvals").insert({
                                        "agent_name": current_user_name,
                                        "action_type": "insert_new_items_batch",
                                        "payload": new_records,
                                        "status": "pending"
                                    }).execute()
                                    st.warning("⏳ Ihre Anfrage wurde an den Administrator gesendet und wartet auf Freigabe!")
                                    st.caption(f"Debug Info Supabase: {res}")
                                else:
                                    supabase.table("inventory").insert(new_records).execute()
                                    st.success(f"🎉 Erfolgreich {len(new_records)} neue Artikel hinzugefügt!")
                                    st.rerun()

                            except Exception as ex:
                                st.error(f"❌ Fehler beim Speichern: {ex}")

                    with action_tab2:
                        st.write("Wählen Sie eine spezifische Position aus der Liste:")
                        selected_missing_sap = st.selectbox(
                            "SAP auswählen:",
                            options=missing_df['sap_clean'].tolist(),
                            key="select_missing_single"
                        )

                        if selected_missing_sap:
                            row_info = missing_df[missing_df['sap_clean'] == selected_missing_sap].iloc[0]

                            with st.form("single_add_form"):
                                col_a, col_b = st.columns(2)
                                with col_a:
                                    init_name = clean_val(row_info.get("name", row_info.get("artikelname")), "", str)
                                    s_name = st.text_input("Artikelname (Name)", value=init_name)
                                    s_brand = st.selectbox("Marke (Brand)", ["Royal Copenhagen", "Iittala", "Moomin Arabia", "Georg Jensen"])
                                    init_qty = clean_val(row_info.get("quantity", row_info.get("menge")), 1, int)
                                    s_qty = st.number_input("Menge (Quantity)", min_value=0, value=init_qty)
                                with col_b:
                                    s_loc = st.selectbox(
                                        "Lagerort / Status (Location)",
                                        ["Bestellt (Unterwegs)", "Wareneingang (Unbekannt)", "RC Lager", "Shop Lager"]
                                    )
                                    init_price = clean_val(row_info.get("preis", row_info.get("price")), 0.0, float)
                                    s_price = st.number_input("Preis (€)", min_value=0.0, value=init_price)
                                    init_barcode = clean_val(row_info.get("barcode"), "", str)
                                    s_barcode = st.text_input("Barcode", value=init_barcode)

                                if st.form_submit_button("💾 Diesen Artikel speichern"):
                                    try:
                                        single_record = [{
                                            "sap": selected_missing_sap,
                                            "name": s_name if s_name else "Neuer Artikel",
                                            "brand": s_brand,
                                            "quantity": s_qty,
                                            "location": s_loc,
                                            "preis": s_price,
                                            "barcode": s_barcode,
                                            "min_stock": 0,
                                            "max_stock": 0
                                        }]

                                        if "Agent" in current_role:
                                            res = supabase.table("pending_approvals").insert({
                                                "agent_name": current_user_name,
                                                "action_type": "insert_single_item",
                                                "payload": single_record,
                                                "status": "pending"
                                            }).execute()
                                            st.warning("⏳ Ihre Einzelauswahl wurde zur Freigabe an den Administrator gesendet!")
                                            st.caption(f"Debug Info Supabase: {res}")
                                        else:
                                            supabase.table("inventory").insert(single_record[0]).execute()
                                            st.success(f"✅ Artikel mit SAP {selected_missing_sap} erfolgreich hinzugefügt!")
                                            st.rerun()

                                    except Exception as ex:
                                        st.error(f"❌ Fehler beim Speichern: {ex}")

        except Exception as e:
            st.error(f"❌ Fehler beim Lesen der Datei: {e}")

# =========================================================
# БЛОК 2: ЗАКАЗ НОВЫХ ТОВАРОВ (ОТДЕЛЬНЫЙ ИМПОРТ ФАЙЛА)
# =========================================================

st.markdown("---")
st.subheader("📦 Neue Artikel aus Bestellung erfassen")
st.caption("Laden Sie die Bestelldatei hoch, um neue Artikel mit SAP-Nummer automatisch anzulegen.")

order_file_new = st.file_uploader(
    "Bestelldatei hochladen (.xlsx / .csv):",
    type=["xlsx", "csv"],
    key="new_items_order_uploader"
)

if order_file_new is not None:
    try:
        if order_file_new.name.endswith(".csv"):
            df_order_new = pd.read_csv(order_file_new)
        else:
            df_order_new = pd.read_excel(order_file_new)

        df_order_new.columns = [str(c).strip().lower() for c in df_order_new.columns]

        if "sap" not in df_order_new.columns:
            st.error("❌ Die Spalte 'sap' ist in der Datei zwingend erforderlich!")
        else:
            existing_saps = set(df['sap'].astype(str).str.strip().tolist()) if not df.empty else set()
            df_order_new['sap_clean'] = df_order_new['sap'].astype(str).str.strip()
            
            new_items_df = df_order_new[~df_order_new['sap_clean'].isin(existing_saps)].copy()

            if new_items_df.empty:
                st.info("ℹ️ Alle Artikel aus dieser Datei sind bereits in Ihrer Datenbank vorhanden.")
            else:
                st.warning(f"🆕 Es wurden **{len(new_items_df)} neue Artikel** (nach SAP) gefunden, die noch nicht in der Datenbank existieren:")
                
                display_cols = [c for c in ['sap_clean', 'name', 'brand', 'quantity', 'preis', 'barcode'] if c in new_items_df.columns]
                st.dataframe(new_items_df[display_cols], use_container_width=True)

                col1, col2 = st.columns(2)

                with col1:
                    if st.button("🚀 Alle neuen Artikel mit Bestand eintragen", type="primary", key="btn_add_new_with_qty"):
                        try:
                            records = []
                            for _, row in new_items_df.iterrows():
                                records.append({
                                    "sap": clean_val(row.get("sap_clean"), "", str),
                                    "name": clean_val(row.get("name", row.get("artikelname")), "Neuer Artikel", str),
                                    "brand": clean_val(row.get("brand", row.get("marke")), "Royal Copenhagen / Iittala", str),
                                    "quantity": clean_val(row.get("quantity", row.get("menge")), 0, int),
                                    "preis": clean_val(row.get("preis", row.get("price")), 0.0, float),
                                    "barcode": clean_val(row.get("barcode"), "", str),
                                    "location": "Bestellt",
                                    "min_stock": 0,
                                    "max_stock": 0
                                })

                            if "Agent" in current_role:
                                res = supabase.table("pending_approvals").insert({
                                    "agent_name": current_user_name,
                                    "action_type": "insert_new_items_with_qty",
                                    "payload": records,
                                    "status": "pending"
                                }).execute()
                                st.warning("⏳ Ihre Anfrage wurde an den Administrator gesendet und wartet auf Freigabe!")
                                st.caption(f"Debug Info Supabase: {res}")
                            else:
                                supabase.table("inventory").insert(records).execute()
                                st.success(f"🎉 Erfolgreich {len(records)} neue Artikel in die Datenbank eingetragen!")
                                st.rerun()

                        except Exception as ex:
                            st.error(f"Fehler beim Speichern: {ex}")

                with col2:
                    if st.button("📋 Als Stammdaten anlegen (Bestand = 0)", key="btn_add_new_zero_qty"):
                        try:
                            records = []
                            for _, row in new_items_df.iterrows():
                                records.append({
                                    "sap": clean_val(row.get("sap_clean"), "", str),
                                    "name": clean_val(row.get("name", row.get("artikelname")), "Neuer Artikel", str),
                                    "brand": clean_val(row.get("brand", row.get("marke")), "Royal Copenhagen / Iittala", str),
                                    "quantity": 0,
                                    "preis": clean_val(row.get("preis", row.get("price")), 0.0, float),
                                    "barcode": clean_val(row.get("barcode"), "", str),
                                    "location": "Bestellt",
                                    "min_stock": 0,
                                    "max_stock": 0
                                })

                            if "Agent" in current_role:
                                res = supabase.table("pending_approvals").insert({
                                    "agent_name": current_user_name,
                                    "action_type": "insert_new_items_zero_qty",
                                    "payload": records,
                                    "status": "pending"
                                }).execute()
                                st.warning("⏳ Ihre Anfrage wurde an den Administrator gesendet und wartet auf Freigabe!")
                                st.caption(f"Debug Info Supabase: {res}")
                            else:
                                supabase.table("inventory").insert(records).execute()
                                st.success(f"🎉 {len(records)} neue Artikel-Stammdaten mit Bestand 0 erstellt!")
                                st.rerun()

                        except Exception as ex:
                            st.error(f"Fehler beim Speichern: {ex}")

    except Exception as e:
        st.error(f"Fehler bei der Dateiverarbeitung: {e}")

# =========================================================
# БЛОК: УПРАВЛЕНИЕ ЗАПРОСАМИ АГЕНТОВ (ТОЧНАЯ ПРОВЕРКА РОЛЕЙ)
# =========================================================
st.markdown("---")
st.subheader("🔔 Anfragen von Agenten verwalten")

try:
    # 1. Получаем все записи из таблицы модерации
    res = supabase.table("pending_approvals").select("*").execute()
    data = res.data if res and res.data else []
    
    # 2. Отбираем только записи со статусом 'pending'
    pending_items = [
        item for item in data 
        if str(item.get("status", "")).strip().lower() == "pending"
    ]
    
    count_pending = len(pending_items)
    st.write(f"Ausstehende Anfragen gefunden: **{count_pending}**")
    
    if not pending_items:
        st.info("Keine ausstehenden Anfragen von Agenten.")
    else:
        # Сбираем абсолютно все источники сведений о текущей роли для 100% надежности
        role_sources = [
            str(globals().get('current_role', '')),
            str(st.session_state.get('role', '')),
            str(st.session_state.get('user_role', '')),
            str(st.session_state.get('user', '')),
            str(st.session_state.get('username', ''))
        ]
        combined_role_info = " ".join(role_sources).lower()
        
        # Если в боковом меню выбрана роль менеджера / полный доступ OR нет явной метки строгого агента
        # Менеджером является пользователь, у которого в данных есть manager / vollzugriff / admin / maria
        is_manager = any(keyword in combined_role_info for keyword in ["manager", "vollzugriff", "admin", "maria"])
        
        # Если при этом явно НЕ включен режим чистого агента (Agent без Vollzugriff)
        if "agent (freigabe" in combined_role_info or combined_role_info.strip() == "agent":
            is_manager = False

        for item in pending_items:
            item_id = item.get("id")
            agent = item.get("agent_name", "Unbekannt")
            action = item.get("action_type", "-")
            payload = item.get("payload", [])
            
            with st.expander(f"📋 Anfrage ID: {item_id} | Agent: {agent} | Typ: {action}"):
                st.json(payload)
                
                if is_manager:
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Genehmigen (Freigeben)", key=f"ok_{item_id}", type="primary"):
                            if isinstance(payload, list):
                                supabase.table("inventory").insert(payload).execute()
                            else:
                                supabase.table("inventory").insert([payload]).execute()
                            
                            supabase.table("pending_approvals").update({"status": "approved"}).eq("id", item_id).execute()
                            st.success(f"Anfrage ID {item_id} erfolgreich genehmigt!")
                            st.rerun()
                            
                    with col2:
                        if st.button("❌ Ablehnen", key=f"no_{item_id}"):
                            supabase.table("pending_approvals").update({"status": "rejected"}).eq("id", item_id).execute()
                            st.warning(f"Anfrage ID {item_id} wurde abgelehnt.")
                            st.rerun()
                else:
                    st.caption("🔒 Nur für Manager: Freigabe ausstehend.")

except Exception as err:
    st.error(f"❌ Fehler beim Laden der Anfragen: {err}")

# =========================================================
# BLOCK: LAGERANALYSE & KRITISCHE BESTÄNDE (DEUTSCH)
# =========================================================
import pandas as pd
import plotly.express as px

st.markdown("---")
st.header("📊 Lageranalyse & Kritische Bestände")

try:
    # 1. Alle Artikel aus der Tabelle 'inventory' abrufen
    res_inv = supabase.table("inventory").select("*").execute()
    inv_data = res_inv.data if res_inv and res_inv.data else []

    if not inv_data:
        st.info("Keine Artikel in der Datenbank vorhanden.")
    else:
        df_inv = pd.DataFrame(inv_data)

        # Numerische Spalten umwandeln
        numeric_cols = ["quantity", "min_stock", "max_stock", "preis"]
        for col in numeric_cols:
            if col in df_inv.columns:
                df_inv[col] = pd.to_numeric(df_inv[col], errors="coerce").fillna(0)

        # -----------------------------------------------------
        # 1. WARNUNGEN FÜR KRITISCHE BESTÄNDE (LOW STOCK)
        # -----------------------------------------------------
        st.subheader("⚠️ Kritische Bestände (Unter Min-Stock)")

        # Filtern: Bestand <= min_stock und min_stock > 0
        low_stock_df = df_inv[
            (df_inv["quantity"] <= df_inv["min_stock"]) & (df_inv["min_stock"] > 0)
        ]

        out_of_stock_df = df_inv[df_inv["quantity"] == 0]

        # Kennzahlen (Metrics) anzeigen
        m1, m2, m3 = st.columns(3)
        m1.metric("Gesamte Artikelanzahl", len(df_inv))
        m2.metric("Artikel unter Min-Stock", len(low_stock_df), delta_color="inverse")
        m3.metric("Ausverkauft (0 Stk.)", len(out_of_stock_df), delta_color="inverse")

        if not low_stock_df.empty:
            st.error(f"🚨 Achtung: **{len(low_stock_df)}** Positionen müssen dringend nachbestellt werden!")
            
            display_cols = [c for c in ["article", "sap", "name", "brand", "quantity", "min_stock", "location"] if c in low_stock_df.columns]
            st.dataframe(
                low_stock_df[display_cols].rename(columns={
                    "article": "Artikel-Nr.",
                    "sap": "SAP",
                    "name": "Bezeichnung",
                    "brand": "Marke",
                    "quantity": "Bestand (Stk.)",
                    "min_stock": "Min.-Bestand",
                    "location": "Lagerort"
                }),
                use_container_width=True
            )
        else:
            st.success("✅ Alle Artikel liegen im normalen Bereich (über Min-Stock).")

        # -----------------------------------------------------
        # 2. INTERAKTIVE DIAGRAMME UND ANALYSE
        # -----------------------------------------------------
        st.subheader("📈 Bestands- und Sortimentsvisualisierung")

        tab_brand, tab_loc, tab_top = st.tabs(["🏷️ Bestände nach Marken", "📍 Verteilung nach Lagerort", "🔝 Top-Positionen"])

        with tab_brand:
            if "brand" in df_inv.columns and "quantity" in df_inv.columns:
                brand_summary = df_inv.groupby("brand")["quantity"].sum().reset_index()
                brand_summary = brand_summary.sort_values(by="quantity", ascending=False)

                fig_brand = px.bar(
                    brand_summary,
                    x="brand",
                    y="quantity",
                    title="Gesamte Stückzahl nach Marken",
                    labels={"brand": "Marke", "quantity": "Stückzahl"},
                    color="brand",
                    text_auto=True
                )
                fig_brand.update_layout(showlegend=False)
                st.plotly_chart(fig_brand, use_container_width=True)

        with tab_loc:
            if "location" in df_inv.columns and "quantity" in df_inv.columns:
                loc_summary = df_inv.groupby("location")["quantity"].sum().reset_index()

                fig_loc = px.pie(
                    loc_summary,
                    names="location",
                    values="quantity",
                    title="Verteilung der Artikel nach Lagerzonen",
                    hole=0.4
                )
                st.plotly_chart(fig_loc, use_container_width=True)

        with tab_top:
            if "name" in df_inv.columns and "quantity" in df_inv.columns:
                top_items = df_inv.nlargest(10, "quantity")[["name", "brand", "quantity", "location"]]
                st.markdown("**Top 10 Artikel mit dem höchsten Lagerbestand:**")
                st.dataframe(
                    top_items.rename(columns={
                        "name": "Bezeichnung",
                        "brand": "Marke",
                        "quantity": "Bestand (Stk.)",
                        "location": "Lagerort"
                    }),
                    use_container_width=True
                )

except Exception as e:
    st.error(f"❌ Fehler beim Laden der Lageranalyse: {e}")

# =========================================================
# 📊 ДОПОЛНИТЕЛЬНЫЙ БЛОК ФИНАНСОВОЙ АНАЛИТИКИ И ПРОДАЖ
# =========================================================
if action in ["📊 Bestände anzeigen", "📊 Показать остатки", "📊 View inventory"]:
    st.markdown("---")
    st.header(t.get("header_sales", "💰 Umsatz & Top-Seller Analytik"))

    # Создаем 2 вкладки: Выручка и Бестселлеры
    tab_rev, tab_top = st.tabs([
        t.get("tab_rev", "💰 Umsatz nach Marken (€)"),
        t.get("tab_top", "🔝 Bestseller / Top-Verkäufe")
    ])

    # --- Вкладка 1: Выручка по брендам (€) ---
    with tab_rev:
        st.subheader(t.get("rev_title", "Monatlicher Umsatz nach Marken laut Barcode (€)"))
        try:
            if supabase is not None:
                sales_data = []
                for tbl in ["daily_sales", "sales", "operations_log"]:
                    try:
                        res = supabase.table(tbl).select("*").execute()
                        if res.data:
                            sales_data.extend(res.data)
                    except Exception:
                        pass
                
                if sales_data:
                    import pandas as pd
                    df_sales = pd.DataFrame(sales_data)
                    
                    rev_col = None
                    for c in ["revenue", "price", "amount", "umsatz", "summe", "total"]:
                        if c in df_sales.columns:
                            rev_col = c
                            break
                    
                    brand_col = None
                    for c in ["brand", "marke", "manufacturer", "category"]:
                        if c in df_sales.columns:
                            brand_col = c
                            break

                    if rev_col and brand_col:
                        df_sales[brand_col] = df_sales[brand_col].astype(str).str.strip().str.title()
                        df_rev_brand = df_sales.groupby(brand_col)[rev_col].sum().reset_index()
                        df_rev_brand.columns = [t.get("brand", "Marke"), t.get("umsatz", "Umsatz (€)")]
                        
                        st.bar_chart(df_rev_brand.set_index(t.get("brand", "Marke")))
                        st.dataframe(df_rev_brand, use_container_width=True)
                    else:
                        st.info(t.get("no_sales", "Keine Verkaufsdaten vorhanden."))
                else:
                    st.info(t.get("no_sales", "Keine Verkaufsdaten vorhanden."))
            else:
                st.warning("Supabase Connection Error")
        except Exception as e:
            st.info(t.get("no_sales", "Keine Verkaufsdaten vorhanden."))

    # --- Вкладка 2: Бестселлеры (Топ-10) ---
    with tab_top:
        st.subheader(t.get("top_title", "🔥 Top 10 meistverkaufte Artikel"))
        try:
            if supabase is not None:
                sales_data = []
                for tbl in ["daily_sales", "sales", "operations_log"]:
                    try:
                        res = supabase.table(tbl).select("*").execute()
                        if res.data:
                            sales_data.extend(res.data)
                    except Exception:
                        pass

                if sales_data:
                    import pandas as pd
                    df_top = pd.DataFrame(sales_data)
                    
                    name_col = None
                    for c in ["article_name", "name", "title", "bezeichnung", "sap_number"]:
                        if c in df_top.columns:
                            name_col = c
                            break
                            
                    qty_col = None
                    for c in ["quantity", "anzahl", "stk", "count"]:
                        if c in df_top.columns:
                            qty_col = c
                            break

                    if name_col and qty_col:
                        df_top_10 = df_top.groupby(name_col)[qty_col].sum().reset_index()
                        df_top_10 = df_top_10.sort_values(by=qty_col, ascending=False).head(10)
                        df_top_10.columns = [t.get("top_col_art", "Artikel"), t.get("top_col_qty", "Verkaufte Stk.")]
                        
                        st.dataframe(df_top_10, use_container_width=True)
                    else:
                        st.info(t.get("no_sales", "Keine Verkaufsdaten vorhanden."))
                else:
                    st.info(t.get("no_sales", "Keine Verkaufsdaten vorhanden."))
            else:
                st.warning("Supabase Connection Error")
        except Exception as e:
            st.info(t.get("no_sales", "Keine Verkaufsdaten vorhanden."))
            # ==========================================
# ==========================================
# 📊 SEPARATER BLOCK: Tagesumsätze der Historie (Brutto)
# ==========================================
st.markdown("---")
st.subheader("📊 Verlauf der hochgeladenen Tagesumsätze")

try:
    import pandas as pd
    import streamlit as st

    # Загружаем данные из daily_sales
    daily_res = supabase.table("daily_sales").select("*").execute()

    if daily_res.data:
        df_daily = pd.DataFrame(daily_res.data)
        
        if not df_daily.empty and "date" in df_daily.columns and "brutto" in df_daily.columns:
            # Преобразуем формат данных
            df_daily["date"] = pd.to_datetime(df_daily["date"]).dt.strftime('%Y-%m-%d')
            df_daily["brutto"] = pd.to_numeric(df_daily["brutto"], errors='coerce').fillna(0)
            
            # Группируем по датам
            df_grouped = df_daily.groupby("date")["brutto"].sum().reset_index()
            df_grouped = df_grouped.sort_values("date")
            df_grouped.columns = ["Datum", "Brutto-Umsatz (€)"]
            
            # Строим график и таблицу
            st.bar_chart(df_grouped.set_index("Datum"))
            st.dataframe(df_grouped, use_container_width=True)
        else:
            st.info("Таблица пуста или в ней нет нужных колонок.")
            st.write("Доступные колонки:", list(df_daily.columns))
    else:
        st.info("Нет данных в таблице daily_sales.")

except Exception as e:
    st.error(f"Fehler: {e}")
st.caption("© 2026 Maria Jentzsch. Alle Rechte vorbehalten. IQBestandPro™")
