import csv
import json
import base64
import os
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs
import urllib.parse
from datetime import datetime

PORT = int(os.environ.get("PORT", 8099))
DB_FILE = "lagerbestand.csv"
REVENUE_FILE = "umsatz_bericht.csv"
GOALS_FILE = "finanz_ziele.csv"
ORDERS_FILE = "bestellungen.csv"

# Настройки авторизации
USER_AUTH = "admin"
PASS_AUTH = "kadewe2026"

# Чтение данных из локального файла (который вы можете легко выгружать из Google Таблиц в формате CSV)
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
                            "id": row[0].strip(),
                            "sap": row[1].strip(),
                            "name": row[2].strip(),
                            "kat": row[3].strip(),
                            "menge": int(row[4].strip() or 0),
                            "soll_menge": int(row[5].strip() or 5),
                            "min_monat": int(row[6].strip() or 2),
                            "preis": float(row[7].strip().replace(',', '.') or 0.0)
                        })
        except Exception as e:
            print(f"Ошибка чтения файла склада: {e}")
    return products

# Сохранение данных в локальный файл
def save_db(products_list):
    try:
        with open(DB_FILE, mode='w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(["Produkt-ID", "SAP-Nummer", "Name", "Kategorie", "Menge", "Mindestbestand", "Mindestbestand (Monat)", "Verkaufspreis (EUR)"])
            for p in products_list:
                writer.writerow([
                    p["id"], 
                    p.get("sap", "-"), 
                    p["name"], 
                    p["kat"], 
                    p["menge"], 
                    p.get("soll_menge", 5), 
                    p.get("min_monat", 2), 
                    p["preis"]
                ])
    except Exception as e:
        print(f"Ошибка сохранения файла склада: {e}")

# Чтение и запись заказов
def read_orders():
    orders = []
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
                        orders.append({
                            "order_id": row[0].strip(), 
                            "date": row[1].strip(), 
                            "p_id": row[2].strip(),
                            "name": row[3].strip(), 
                            "qty": int(row[4].strip() or 0), 
                            "status": status_val
                        })
        except Exception:
            pass
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

# Чтение и запись целей
def read_goals():
    goals = {}
    if os.path.exists(GOALS_FILE):
        try:
            with open(GOALS_FILE, mode='r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f, delimiter=';')
                for row in reader:
                    if row and "Monat-Jahr" in row and "Ziel" in row:
                        goals[row["Monat-Jahr"]] = float(str(row["Ziel"]).replace(',', '.') or 0.0)
        except Exception:
            pass
    return goals

def write_goals(goals):
    try:
        with open(GOALS_FILE, mode='w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(["Monat-Jahr", "Ziel"])
            for k, v in goals.items():
                writer.writerow([k, f"{v:.2f}".replace('.', ',')])
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
