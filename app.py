import os
import csv
import json
import base64
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs
from datetime import datetime

PORT = 8099
DB_FILE = "lagerbestand.csv"
REVENUE_FILE = "umsatz_bericht.csv"
GOALS_FILE = "finanz_ziele.csv"
ORDERS_FILE = "bestellungen.csv"

# Настройки авторизации
USER_AUTH = "admin"
PASS_AUTH = "kadewe2026"

def read_db():
    products = []
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, mode='r', encoding='utf-8-sig') as f:
                reader = csv.reader(f, delimiter=';')
                header = next(reader, None)
                for row in reader:
                    if row and len(row) >= 8:
                        products.append({
                            "id": row[0].strip(), "sap": row[1].strip(), "name": row[2].strip(), "kat": row[3].strip(),
                            "menge": int(row[4] or 0), "min_menge": int(row[5] or 0),
                            "min_monat": int(row[6] or 2), "preis": float(row[7] or 0.0)
                        })
        except Exception:
            pass
    return products

def write_db(products):
    try:
        with open(DB_FILE, mode='w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(["Produkt-ID", "SAP-Nummer", "Name", "Kategorie", "Menge", "Mindestbestand", "Mindestbestand (Monat)", "Verkaufspreis (EUR)"])
            for p in products:
                writer.writerow([p["id"], p.get("sap", "-"), p["name"], p["kat"], p["menge"], p["min_menge"], p.get("min_monat", 2), p["preis"]])
    except Exception:
        pass

def read_orders():
    orders = []
    updated = False
    if os.path.exists(ORDERS_FILE):
        try:
            with open(ORDERS_FILE, mode='r', encoding='utf-8-sig') as f:
                reader = csv.reader(f, delimiter=';')
                header = next(reader, None)
                for row in reader:
                    if row and len(row) >= 6:
                        status_val = row[5].strip()
                        if "." in status_val or status_val == "" or status_val.isdigit():
                            status_val = "Unterwegs"
                            updated = True
                            
                        orders.append({
                            "order_id": row[0].strip(), "date": row[1].strip(), "p_id": row[2].strip(),
                            "name": row[3].strip(), "qty": int(row[4] or 0), "status": status_val
                        })
        except Exception:
            pass
            
    if updated:
        write_orders(orders)
    return orders

def write_orders(orders):
    try:
        with open(ORDERS_FILE, mode='w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(["Bestellnummer", "Datum", "Produkt-ID", "Name", "Menge", "Status"])
            for o in orders:
                writer.writerow([o["order_id"], o["date"], o["p_id"], o["name"], o["qty"], o["status"]])
    except Exception:
        pass

def read_goals():
    goals = {}
    if os.path.exists(GOALS_FILE):
        try:
            with open(GOALS_FILE, mode='r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f, delimiter=';')
                for row in reader:
                    if row and "Monat-Jahr" in row and "Ziel" in row:
                        goals[row["Monat-Jahr"]] = float(row["Ziel"])
        except Exception:
            pass
    return goals

def write_goals(goals):
    try:
        with open(GOALS_FILE, mode='w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(["Monat-Jahr", "Ziel"])
            for k, v in goals.items():
                writer.writerow([k, f"{v:.2f}"])
    except Exception:
        pass

def try_float(val):
    if not val: return 0.0
    try: return float(str(val).replace(',', '.'))
    except ValueError: return 0.0

def parse_multipart_generic(body_bytes, boundary, field_name):
    if not boundary or not body_bytes: return ""
    try:
        boundary_bytes = b"--" + boundary.encode('utf-8')
        parts = body_bytes.split(boundary_bytes)
        for part in parts:
            if f'name="{field_name}"'.encode('utf-8') in part:
                subparts = part.split(b'\r\n\r\n', 1)
                if len(subparts) == 2:
                    payload = subparts[1]
                    if payload.endswith(b'\r\n'): payload = payload[:-2]
                    if payload.endswith(b'--\r\n'): payload = payload[:-4]
                    return payload.decode('utf-8-sig', errors='ignore').strip()
    except Exception: pass
    return ""

def get_monthly_revenue_map():
    report = {}
    if os.path.exists(REVENUE_FILE):
        try:
            with open(REVENUE_FILE, mode='r', encoding='utf-8-sig') as f:
                reader = csv.reader(f, delimiter=';')
                next(reader, None)
                for row in reader:
                    if row and len(row) >= 10:
                        dt_str = row[0].strip()
                        n_val = try_float(row[9])
                        try:
                            dt = datetime.strptime(dt_str, "%d.%m.%Y %H:%M")
                            m_key = dt.strftime("%m.%Y")
                            report[m_key] = report.get(m_key, 0.0) + n_val
                        except Exception:
                            pass
        except Exception:
            pass
    return report

def generate_html(error_msg="", success_msg="", selected_product=None):
    products = read_db()
    orders = read_orders()
    rev_map = get_monthly_revenue_map()
    goals = read_goals()
    heute = datetime.now()
    
    monate_de = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
    err_div = f'<div style="color:red; background:#f8d7da; padding:10px; margin-bottom:15px; border-radius:4px;"><b>Fehler:</b> {error_msg}</div>' if error_msg else ''
    suc_div = f'<div style="color:green; background:#d4edda; padding:10px; margin-bottom:15px; border-radius:4px;"><b>Erfolg:</b> {success_msg}</div>' if success_msg else ''

    product_card_html = ""
    if selected_product:
        m, mm = selected_product.get('menge', 0), selected_product.get('min_menge', 5)
        is_low = m <= mm
        status_label = "🚨 Bestand kritisch niedrig!" if is_low else "✅ Bestand ausreichend"
        status_bg = "#fce8e6" if is_low else "#e8f5e9"
        status_color = "#c0392b" if is_low else "#27ae60"
        
        product_card_html = f"""
        <div class="box" style="background: {status_bg}; border: 2px solid {status_color}; margin-bottom: 25px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h3 style="margin: 0; color: #2c3e50;">🔍 Produktkarte &amp; Limit-Steuerung</h3>
                <span style="background: {status_color}; color: white; padding: 4px 10px; border-radius: 20px; font-weight: bold; font-size: 13px;">{status_label}</span>
            </div>
            
            <form action="/update_product_limits" method="POST">
                <input type="hidden" name="p_id" value="{selected_product['id']}">
                <table style="margin-top: 15px; background: white; border-radius: 4px; border: 1px solid #ccc;">
                    <tr style="background: #ecf0f1;"><th colspan="2" style="color: #2c3e50; background: #ecf0f1; border-bottom: 2px solid #bdc3c7;">{selected_product['name']}</th></tr>
                    <tr><td style="width: 30%;"><b>Produkt-ID (EAN):</b></td><td>{selected_product['id']}</td></tr>
                    <tr><td><b>SAP-Nummer:</b></td><td>{selected_product['sap']}</td></tr>
                    <tr><td><b>Kategorie:</b></td><td>{selected_product['kat']}</td></tr>
                    <tr><td><b>Aktueller Bestand:</b></td><td style="font-size: 18px; color: {status_color}; font-weight: bold;">{m} Stk.</td></tr>
                    
                    <tr>
                        <td><b>Mindestbestand (Monat):</b></td>
                        <td>
                            <input type="number" name="min_monat" value="{selected_product.get('min_monat', 2)}" min="0" style="width: 70px; text-align: center;"> Stk.
                        </td>
                    </tr>
                    <tr>
                        <td><b>Mindestbestand (Jahr / Standard):</b></td>
                        <td>
                            <input type="number" name="min_menge" value="{mm}" min="0" style="width: 70px; text-align: center;"> Stk.
                            <span style="font-size: 12px; color: #7f8c8d; margin-left: 10px;">(Auslöser für roten Alarm)</span>
                        </td>
                    </tr>
                    
                    <tr><td><b>Verkaufspreis:</b></td><td style="font-weight: bold; color: #2980b9;">{selected_product['preis']:.2f} EUR</td></tr>
                </table>
                
                <div style="margin-top: 12px; display: flex; justify-content: space-between; align-items: center;">
                    <a href="/" style="text-decoration: none; font-size: 13px; color: #7f8c8d; font-weight: bold;">✕ Karte schließen</a>
                    <button type="submit" class="btn" style="background: #27ae60; padding: 6px 15px;">💾 Limit speichern</button>
                </div>
            </form>
        </div>
        """

    rows = ""
    for p in products:
        m, mm = p.get('menge', 0), p.get('min_menge', 5)
        bg = 'style="background-color: #fce8e6;"' if m <= mm else ''
        rows += f"<tr {bg}><td><b>{p['id']}</b></td><td>{p['sap']}</td><td>{p['name']}</td><td>{p['kat']}</td><td>{m}</td><td>{p.get('min_monat',2)}</td><td>{mm}</td><td>{p['preis']:.2f}</td></tr>"

    order_rows = ""
    for o in orders:
        st_color = "#e67e22" if o["status"] == "Unterwegs" else "#27ae60" if o["status"] == "Geliefert" else "#7f8c8d"
        action_btn = ""
        if o["status"] == "Unterwegs":
            action_btn = f"""
            <div style="display: flex; gap: 5px;">
                <form action="/update_order_status" method="POST" style="display:inline;">
                    <input type="hidden" name="order_id" value="{o['order_id']}">
                    <input type="hidden" name="p_id" value="{o['p_id']}">
                    <input type="hidden" name="new_status" value="Geliefert">
                    <button type="submit" class="btn" style="background:#27ae60; padding:4px 8px; font-size:11px;">Einbuchen</button>
                </form>
                <form action="/update_order_status" method="POST" style="display:inline;">
                    <input type="hidden" name="order_id" value="{o['order_id']}">
                    <input type="hidden" name="p_id" value="{o['p_id']}">
                    <input type="hidden" name="new_status" value="Storniert">
                    <button type="submit" class="btn" style="background:#7f8c8d; padding:4px 8px; font-size:11px;">Stornieren</button>
                </form>
            </div>
            """
        order_rows += f"""<tr>
            <td>{o['order_id']}</td>
            <td>{o['date']}</td>
            <td>{o['p_id']}</td>
            <td>{o['name']}</td>
            <td>{o['qty']}</td>
            <td><span style="color:{st_color}; font-weight:bold;">{o['status']}</span></td>
            <td>{action_btn}</td>
        </tr>"""

    goals_html = ""
    for i in range(12):
        m_key = f"{i+1:02d}.{heute.year}"
        c_goal = goals.get(m_key, 0.0)
        c_ist = rev_map.get(m_key, 0.0)
        diff = c_ist - c_goal
        
        if c_goal > 0:
            pct = (c_ist / c_goal) * 100.0
            status_color = "#27ae60" if pct >= 100 else "#e67e22" if pct > 0 else "#7f8c8d"
        else:
            pct = 0.0
            status_color = "#7f8c8d"
            
        diff_text = f"+{diff:.2f}" if diff >= 0 else f"{diff:.2f}"
        diff_color = "green" if diff >= 0 else "red"

        goals_html += f"""
        <div style="display: flex; align-items: center; justify-content: space-between; padding: 8px; border-bottom: 1px solid #eee;">
            <span style="width: 120px; font-weight: bold;">{monate_de[i]} {heute.year}:</span>
            <div>
                <label>Soll (Netto): </label>
                <input type="number" step="0.01" name="goal_{m_key}" value="{c_goal}" style="width:100px; text-align:right;"> EUR
            </div>
            <div style="width: 450px; text-align: right;">
                Ist: <b>{c_ist:.2f} EUR</b> | 
                Abweichung: <span style="color:{diff_color}; font-weight:bold;">{diff_text} EUR</span> | 
                Fortschritt: <span style="color:{status_color}; font-weight:bold;">{pct:.1f}%</span>
            </div>
        </div>
        """

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Lagerverwaltungssystem v8.98</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background-color: #f4f6f9; margin: 0; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 25px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px; }}
        .box {{ border: 1px solid #e0e0e0; padding: 20px; border-radius: 6px; background: #fafafa; margin-bottom: 20px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; background: white; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #34495e; color: white; }}
        .btn {{ padding: 8px 12px; background: #3498db; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }}
        .btn:hover {{ background: #2980b9; }}
        input, select {{ padding: 6px; border: 1px solid #ccc; border-radius: 4px; }}
        
        .file-upload-wrapper {{ display: inline-block; position: relative; margin-bottom: 10px; }}
        .file-upload-input {{ position: absolute; left: 0; top: 0; opacity: 0; width: 100%; height: 100%; cursor: pointer; }}
        .file-upload-btn {{ display: inline-block; padding: 6px 12px; background: #7f8c8d; color: white; border-radius: 4px; font-weight: bold; font-size: 13px; }}
        .file-upload-text {{ margin-left: 10px; font-size: 13px; color: #555; font-style: italic; }}
    </style>
    <script>
        function updateFileName(input, textId) {{
            var fileName = input.files[0] ? input.files[0].name : "Keine Datei ausgewählt";
            document.getElementById(textId).innerText = fileName;
        }}
    </script>
</head>
<body>
    <div class="container">
        <h2>Lagerverwaltung &amp; Umsatz-Dashboard (Royal Copenhagen)</h2>
        {err_div} {suc_div}
        
        <div class="box">
            <h3>📦 1. Schnelle Buchung &amp; Produkt-Details</h3>
            <form action="/change" method="POST" id="main_booking_form">
                <table style="width:100%; margin:0; background:transparent;">
                    <tr>
                        <td style="width: 25%;"><label><b>Produkt-ID / SAP scannen:</b></label><br>
                        <input type="text" name="search_id" required autofocus style="width: 90%;"></td>
                        
                        <td style="width: 8%;"><label><b>Menge:</b></label><br>
                        <input type="number" name="qty" value="1" min="1" style="width: 60px;"></td>
                        
                        <td style="width: 22%;"><label><b>Transaktionstyp:</b></label><br>
                        <select name="action" style="width: 100%;">
                            <option value="out">Warenausgang / Verkauf (-)</option>
                            <option value="in">Wareneingang / Aufstockung (+)</option>
                            <option value="return">Retoure / Kundenrückgabe (+)</option>
                        </select></td>
                        
                        <td style="width: 12%;"><label><b>Manueller Preis:</b></label><br>
                        <input type="number" step="0.01" name="custom_price" placeholder="Optional" style="width: 100px;"></td>
                        
                        <td style="width: 15%;"><label><b>Rabatt:</b></label><br>
                        <select name="discount_pct" style="width: 100%;">
                            <option value="0">Kein Rabatt (0%)</option>
                            <option value="10">10% Rabatt</option>
                            <option value="20">20% Rabatt</option>
                            <option value="30">30% Rabatt</option>
                            <option value="40">40% Rabatt</option>
                            <option value="50">50% Rabatt</option>
                        </select></td>
                        
                        <td style="vertical-align: bottom; text-align: right; display: flex; gap: 5px; justify-content: flex-end;">
                            <button type="submit" name="submit_btn" value="show_card" class="btn" style="background:#2980b9; height:34px; white-space: nowrap;">Produktkarte anzeigen</button>
                            <button type="submit" name="submit_btn" value="book" class="btn" style="background:#34495e; height:34px;">Buchen</button>
                        </td>
                    </tr>
                </table>
            </form>
        </div>

        {product_card_html}

        <div class="box" style="border-left: 5px solid #e67e22;">
            <h3>🚚 2. Logistik &amp; Bestellungen verwalten (Hauptlager ➔ Abteilung)</h3>
            <form action="/add_order" method="POST" style="margin-bottom: 15px;">
                <div style="display:grid; grid-template-columns: 2fr 2fr 1fr 2fr; gap:10px;">
                    <input type="text" name="order_id" placeholder="Bestellnummer (z.B. PO-10023)" required>
                    <input type="text" name="p_id" placeholder="Produkt-ID (EAN) oder SAP-Nummer" required>
                    <input type="number" name="qty" placeholder="Menge" min="1" value="1" required>
                    <button type="submit" class="btn" style="background:#e67e22;">Neue Bestellung anlegen</button>
                </div>
            </form>
            
            <div style="background: #fff; padding: 12px; border: 1px dashed #ccc; margin-bottom: 15px; border-radius: 4px;">
                <b style="color: #e67e22;">📥 Bestellungen importieren (CSV):</b>
                <form action="/import_orders" method="POST" enctype="multipart/form-data" style="margin-top: 8px;">
                    <div class="file-upload-wrapper">
                        <span class="file-upload-btn">Datei auswählen</span>
                        <input type="file" name="orders_file" accept=".csv" class="file-upload-input" onchange="updateFileName(this, 'txt_orders')" required>
                    </div>
                    <span id="txt_orders" class="file-upload-text">Keine Datei ausgewählt</span>
                    <br>
                    <button type="submit" class="btn" style="background:#d35400; padding: 4px 10px; font-size:12px;">Alte Bestellungen laden</button>
                </form>
            </div>
            
            <table style="font-size: 13px;">
                <thead>
                    <tr><th>Bestellnummer</th><th>Datum</th><th>Produkt-ID</th><th>Name</th><th>Menge</th><th>Status</th><th>Aktion</th></tr>
                </thead>
                <tbody>
                    {order_rows if order_rows else "<tr><td colspan='7' style='text-align:center; color:#999;'>Keine Bestellungen vorhanden.</td></tr>"}
                </tbody>
            </table>
        </div>

        <div class="grid">
            <div class="box">
                <h3>📥 Produktbasis aktualisieren (Katalog CSV)</h3>
                <form action="/import_products" method="POST" enctype="multipart/form-data">
                    <div class="file-upload-wrapper">
                        <span class="file-upload-btn">Datei auswählen</span>
                        <input type="file" name="prod_file" accept=".csv" class="file-upload-input" onchange="updateFileName(this, 'txt_prod')" required>
                    </div>
                    <span id="txt_prod" class="file-upload-text">Keine Datei ausgewählt</span>
                    <br><br>
                    <button type="submit" class="btn" style="background:#2ecc71;">Katalog laden</button>
                </form>
            </div>
            
            <div class="box">
                <h3>📊 Kassenbericht einlesen (Umsatz-CSV)</h3>
                <form action="/import_sales" method="POST" enctype="multipart/form-data">
                    <div class="file-upload-wrapper">
                        <span class="file-upload-btn">Datei auswählen</span>
                        <input type="file" name="sales_file" accept=".csv" class="file-upload-input" onchange="updateFileName(this, 'txt_sales')" required>
                    </div>
                    <span id="txt_sales" class="file-upload-text">Keine Datei ausgewählt</span>
                    <br><br>
                    <button type="submit" class="btn" style="background:#e67e22;">Verkäufe buchen</button>
                </form>
            </div>
        </div>

        <div class="box">
            <h3>➕ 3. Neues Produkt manuell hinzufügen</h3>
            <form action="/add" method="POST">
                <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap: 10px;">
                    <input type="text" name="id" placeholder="Produkt-ID (EAN) *" required>
                    <input type="text" name="sap" placeholder="SAP-Nummer">
                    <input type="text" name="name" placeholder="Produktname *" required>
                    <input type="text" name="kat" value="Royal Copenhagen" placeholder="Kategorie">
                    <input type="number" name="menge" placeholder="Anfangsbestand" value="0">
                    <input type="number" name="min_menge" placeholder="Mindestbestand (Jahr)" value="5">
                    <input type="number" name="min_monat" placeholder="Mindestbestand (Monat)" value="2">
                    <input type="number" step="0.01" name="preis" placeholder="Verkaufspreis in EUR *" required>
                </div>
                <button type="submit" class="btn" style="margin-top:12px; background:#9b59b6;">Produkt manuell speichern</button>
            </form>
        </div>

        <div class="box">
            <h3>🎯 4. Finanzziele &amp; Abweichungsanalyse (Netto)</h3>
            <form action="/save_goals" method="POST">
                <div>{goals_html}</div>
                <button type="submit" class="btn" style="margin-top:15px; background:#2ecc71;">Ziele speichern</button>
            </form>
        </div>

        <h3 style="margin-top:30px;">📋 Aktueller Lagerbestand</h3>
        <table>
            <thead>
                <tr><th>ID (EAN)</th><th>SAP-Nummer</th><th>Name</th><th>Kategorie</th><th>Bestand</th><th>Soll (Monat)</th><th>Soll (Jahr)</th><th>Preis (EUR)</th></tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
    </div>
</body>
</html>"""

class LogHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args): return

    def check_authenticated(self):
        auth_header = self.headers.get('Authorization')
        if auth_header is None:
            self.send_auth_request()
            return False
        
        try:
            auth_type, encoded_credentials = auth_header.split(' ', 1)
            if auth_type.lower() == 'basic':
                decoded_credentials = base64.b64decode(encoded_credentials).decode('utf-8')
                username, password = decoded_credentials.split(':', 1)
                if username == USER_AUTH and password == PASS_AUTH:
                    return True
        except Exception:
            pass
            
        self.send_auth_request()
        return False

    def send_auth_request(self):
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm="Lagerverwaltung Login"')
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(b"<h1>401 Unauthorized</h1><p>Zugriff verweigert. Bitte Anmeldedaten eingeben.</p>")

    def do_GET(self):
        if not self.check_authenticated():
            return

        if self.path == '/':
            self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8'); self.end_headers()
            self.wfile.write(generate_html().encode('utf-8'))
        else:
            self.send_response(404); self.end_headers()

    def do_POST(self):
        if not self.check_authenticated():
            return

        content_length = int(self.headers['Content-Length'])
        content_type = self.headers.get('Content-Type', '')
        boundary = content_type.split('boundary=')[1].strip() if "boundary=" in content_type else ""
        body_bytes = self.rfile.read(content_length)
        
        success_msg = ""
        error_msg = ""

        if self.path == '/update_product_limits':
            body = body_bytes.decode('utf-8', errors='ignore')
            params = parse_qs(body)
            prods = read_db()
            
            p_id = params.get('p_id', [''])[0].strip()
            try:
                new_min_monat = int(params.get('min_monat', ['2'])[0] or 2)
                new_min_menge = int(params.get('min_menge', ['5'])[0] or 5)
            except ValueError:
                new_min_monat = 2
                new_min_menge = 5
                
            target = next((p for p in prods if p['id'] == p_id), None)
            if target:
                target['min_monat'] = new_min_monat
                target['min_menge'] = new_min_menge
                write_db(prods)
                success_msg = f"Mindestbestände für '{target['name']}' erfolgreich aktualisiert!"
                
            self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8'); self.end_headers()
            self.wfile.write(generate_html(success_msg=success_msg, selected_product=target).encode('utf-8')); return

        elif self.path == '/import_products':
            file_data = parse_multipart_generic(body_bytes, boundary, "prod_file")
            if file_data:
                prods = read_db()
                lines = file_data.splitlines()
                if lines:
                    delim = ';' if ';' in lines[0] else ','
                    reader = csv.reader(lines, delimiter=delim)
                    next(reader, None)
                    count = 0
                    for row in reader:
                        if row and len(row) >= 3:
                            p_id = row[0].strip()
                            if not p_id: continue
                            sap_val = row[1].strip() if row[1].strip() else "-"
                            name_val = row[2].strip()
                            preis_val = try_float(row[3].strip()) if len(row) >= 4 else 0.0
                            
                            existing = next((p for p in prods if p['id'] == p_id), None)
                            if existing:
                                existing['sap'] = sap_val
                                existing['name'] = name_val
                                if len(row) >= 4: existing['preis'] = preis_val
                            else:
                                prods.append({"id": p_id, "sap": sap_val, "name": name_val, "kat": "Royal Copenhagen", "menge": 0, "min_menge": 5, "min_monat": 2, "preis": preis_val})
                            count += 1
                    write_db(prods)
                    success_msg = f"{count} Produkte erfolgreich aus Katalog importiert."
            self.send_response(303); self.send_header('Location', '/'); self.end_headers(); return

        elif self.path == '/import_sales':
            file_data = parse_multipart_generic(body_bytes, boundary, "sales_file")
            if file_data:
                prods = read_db()
                lines = file_data.splitlines()
                if lines:
                    delim = ';' if ';' in lines[0] else ','
                    reader = csv.reader(lines, delimiter=delim)
                    next(reader, None)
                    for row in reader:
                        if row and len(row) >= 5:
                            p_id = row[1].strip()
                            qty = int(row[4] or 0)
                            target = next((p for p in prods if p['id'] == p_id or p['sap'] == p_id), None)
                            if target:
                                target['menge'] = max(0, target['menge'] - qty)
                                try:
                                    pr = try_float(row[7].strip()) if len(row) >= 8 else target['preis']
                                    br = pr * qty
                                    ne = br / 1.19
                                    f_ex = os.path.exists(REVENUE_FILE)
                                    with open(REVENUE_FILE, mode='a', newline='', encoding='utf-8-sig') as f:
                                        w = csv.writer(f, delimiter=';')
                                        if not f_ex:
                                            w.writerow(["Datum", "Produkt-ID", "SAP-Nummer", "Name", "Menge", "Originalpreis Stk", "Typ / Status", "Verkaufspreis Stk", "Umsatz Brutto (EUR)", "Umsatz Netto -19% MwSt (EUR)"])
                                        w.writerow([datetime.now().strftime("%d.%m.%Y %H:%M"), target['id'], target['sap'], target['name'], qty, f"{target['preis']:.2f}", "Kassenimport", f"{pr:.2f}", f"{br:.2f}", f"{ne:.2f}"])
                                except Exception: pass
                    write_db(prods)
                    success_msg = "Kassenbericht einlesen und Bestand aktualisiert."
            self.send_response(303); self.send_header('Location', '/'); self.end_headers(); return

        elif self.path == '/import_orders':
            file_data = parse_multipart_generic(body_bytes, boundary, "orders_file")
            if file_data:
                existing_orders = read_orders()
                lines = file_data.splitlines()
                if lines:
                    delim = ';' if ';' in lines[0] else ','
                    reader = csv.reader(lines, delimiter=delim)
                    next(reader, None)
                    count = 0
                    for row in reader:
                        if row and len(row) >= 6:
                            o_id = row[0].strip()
                            o_date = row[1].strip()
                            p_id = row[2].strip()
                            p_name = row[3].strip()
                            qty = int(row[4] or 0)
                            status = row[5].strip()
                            
                            if not o_id: continue
                            if "." in status or status == "" or status.isdigit():
                                status = "Unterwegs"
                            
                            dup = next((o for o in existing_orders if o['order_id'] == o_id and o['p_id'] == p_id), None)
                            if not dup:
                                existing_orders.append({
                                    "order_id": o_id, "date": o_date, "p_id": p_id,
                                    "name": p_name, "qty": qty, "status": status
                                })
                                count += 1
                    write_orders(existing_orders)
                    success_msg = f"{count} Bestellungen erfolgreich importiert."
            self.send_response(303); self.send_header('Location', '/'); self.end_headers(); return

        elif self.path == '/add_order':
            body = body_bytes.decode('utf-8', errors='ignore')
            params = parse_qs(body)
            orders = read_orders()
            prods = read_db()
            
            o_id = params.get('order_id', [''])[0].strip()
            p_search = params.get('p_id', [''])[0].strip()
            o_qty = int(params.get('qty', ['1'])[0] or 1)
            
            target_prod = next((p for p in prods if p['id'] == p_search or p['sap'] == p_search), None)
            p_name = target_prod['name'] if target_prod else "Unbekanntes Produkt"
            p_real_id = target_prod['id'] if target_prod else p_search
            
            orders.append({
                "order_id": o_id,
                "date": datetime.now().strftime("%d.%m.%Y"),
                "p_id": p_real_id,
                "name": p_name,
                "qty": o_qty,
                "status": "Unterwegs"
            })
            write_orders(orders)
            self.send_response(303); self.send_header('Location', '/'); self.end_headers(); return

        elif self.path == '/update_order_status':
            body = body_bytes.decode('utf-8', errors='ignore')
            params = parse_qs(body)
            o_id = params.get('order_id', [''])[0].strip()
            p_id = params.get('p_id', [''])[0].strip()
            new_status = params.get('new_status', [''])[0].strip()
            
            orders = read_orders()
            target_order = next((o for o in orders if o['order_id'] == o_id and o['p_id'] == p_id), None)
            
            if target_order and target_order['status'] == 'Unterwegs':
                target_order['status'] = new_status
                write_orders(orders)
                
                if new_status == 'Geliefert':
                    prods = read_db()
                    target_prod = next((p for p in prods if p['id'] == p_id or p['sap'] == p_id), None)
                    if target_prod:
                        target_prod['menge'] += target_order['qty']
                        write_db(prods)
            self.send_response(303); self.send_header('Location', '/'); self.end_headers(); return

        elif self.path == '/change':
            body = body_bytes.decode('utf-8', errors='ignore')
            params = parse_qs(body)
            
            search_id = params.get('search_id', [''])[0].strip()
            qty = int(params.get('qty', ['1'])[0] or 1)
            action = params.get('action', ['out'])[0]
            custom_price = params.get('custom_price', [''])[0].strip()
            discount = int(params.get('discount_pct', ['0'])[0] or 0)
            submit_btn = params.get('submit_btn', ['book'])[0]
            
            prods = read_db()
            target = next((p for p in prods if p['id'] == search_id or p['sap'] == search_id), None)
            
            if not target:
                error_msg = f"Produkt mit ID/SAP '{search_id}' nicht gefunden!"
                self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8'); self.end_headers()
                self.wfile.write(generate_html(error_msg=error_msg).encode('utf-8')); return
                
            if submit_btn == 'show_card':
                self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8'); self.end_headers()
                self.wfile.write(generate_html(selected_product=target).encode('utf-8')); return
                
            unit_price = try_float(custom_price) if custom_price else target['preis']
            if discount > 0:
                unit_price = unit_price * (1.0 - (discount / 100.0))
                
            if action == 'out':
                target['menge'] = max(0, target['menge'] - qty)
                tx_type = f"Verkauf ({discount}% Rabatt)" if discount > 0 else "Verkauf"
            else:
                target['menge'] += qty
                tx_type = "Wareneingang" if action == 'in' else "Retoure"
                
            write_db(prods)
            
            if action in ['out', 'return']:
                br = unit_price * (qty if action == 'out' else -qty)
                ne = br / 1.19
                f_ex = os.path.exists(REVENUE_FILE)
                with open(REVENUE_FILE, mode='a', newline='', encoding='utf-8-sig') as f:
                    w = csv.writer(f, delimiter=';')
                    if not f_ex:
                        w.writerow(["Datum", "Produkt-ID", "SAP-Nummer", "Name", "Menge", "Originalpreis Stk", "Typ / Status", "Verkaufspreis Stk", "Umsatz Brutto (EUR)", "Umsatz Netto -19% MwSt (EUR)"])
                    w.writerow([datetime.now().strftime("%d.%m.%Y %H:%M"), target['id'], target['sap'], target['name'], qty if action == 'out' else -qty, f"{target['preis']:.2f}", tx_type, f"{unit_price:.2f}", f"{br:.2f}", f"{ne:.2f}"])
                    
            success_msg = f"Buchung für '{target['name']}' ({tx_type}) erfolgreich durchgeführt."
            self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8'); self.end_headers()
            self.wfile.write(generate_html(success_msg=success_msg, selected_product=target).encode('utf-8')); return

        elif self.path == '/add':
            body = body_bytes.decode('utf-8', errors='ignore')
            params = parse_qs(body)
            prods = read_db()
            
            p_id = params.get('id', [''])[0].strip()
            if any(p['id'] == p_id for p in prods):
                error_msg = f"Produkt mit ID '{p_id}' existiert bereits!"
                self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8'); self.end_headers()
                self.wfile.write(generate_html(error_msg=error_msg).encode('utf-8')); return
                
            prods.append({
                "id": p_id,
                "sap": params.get('sap', ['-'])[0].strip() or "-",
                "name": params.get('name', [''])[0].strip(),
                "kat": params.get('kat', ['Royal Copenhagen'])[0].strip() or "Royal Copenhagen",
                "menge": int(params.get('menge', ['0'])[0] or 0),
                "min_menge": int(params.get('min_menge', ['5'])[0] or 5),
                "min_monat": int(params.get('min_monat', ['2'])[0] or 2),
                "preis": try_float(params.get('preis', ['0.0'])[0])
            })
            write_db(prods)
            success_msg = f"Produkt '{p_id}' erfolgreich hinzugefügt."
            self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8'); self.end_headers()
            self.wfile.write(generate_html(success_msg=success_msg).encode('utf-8')); return

        elif self.path == '/save_goals':
            body = body_bytes.decode('utf-8', errors='ignore')
            params = parse_qs(body)
            goals = {}
            for k, v in params.items():
                if k.startswith('goal_'):
                    m_key = k.replace('goal_', '')
                    goals[m_key] = try_float(v[0])
            write_goals(goals)
            success_msg = "Finanzziele erfolgreich gespeichert."
            self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8'); self.end_headers()
            self.wfile.write(generate_html(success_msg=success_msg).encode('utf-8')); return

if __name__ == '__main__':
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, LogHandler)
    print(f"Сервер запущен на http://localhost:{PORT}")
    webbrowser.open(f"http://localhost:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nСервер остановлен.")
