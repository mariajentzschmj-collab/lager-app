import os
import csv
import json
import base64
import urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
import psycopg2
import psycopg2.extras

PORT = int(os.environ.get("PORT", 8099))
DB_FILE = "lagerbestand.csv"
REVENUE_FILE = "umsatz_bericht.csv"
GOALS_FILE = "finanz_ziele.csv"
ORDERS_FILE = "bestellungen.csv"

# Подключение к PostgreSQL на Render
def get_db_connection():
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        return psycopg2.connect(database_url, cursor_factory=psycopg2.extras.DictCursor)
    return None

# Функция чтения данных (берет из базы PostgreSQL на Render или из файла локально)
def read_db():
    conn = get_db_connection()
    if not conn:
        # Локальное чтение из CSV, если базы нет
        products = []
        if os.path.exists(DB_FILE):
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
                            "menge": int(row[4] or 0),
                            "soll_menge": int(row[5] or 0),
                            "min_monat": int(row[6] or 23),
                            "preis": float(row[7] or 0.0)
                        })
        return products
    
    # Чтение из базы PostgreSQL
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS lager (
                id SERIAL PRIMARY KEY,
                item_id TEXT,
                sap TEXT,
                name TEXT,
                kat TEXT,
                menge INT,
                soll_menge INT,
                min_monat INT,
                preis FLOAT
            );
        """)
        conn.commit()
        
        cur.execute("SELECT item_id, sap, name, kat, menge, soll_menge, min_monat, preis FROM lager")
        rows = cur.fetchall()
        products = []
        for row in rows:
            products.append({
                "id": row["item_id"],
                "sap": row["sap"],
                "name": row["name"],
                "kat": row["kat"],
                "menge": row["menge"],
                "soll_menge": row["soll_menge"],
                "min_monat": row["min_monat"],
                "preis": row["preis"]
            })
        cur.close()
        conn.close()
        return products
    except Exception as e:
        print(f"Ошибка чтения базы: {e}")
        return []

# Функция сохранения данных (записывает в базу PostgreSQL на Render или в файл)
def save_db(products_list):
    conn = get_db_connection()
    if not conn:
        # Локальное сохранение в CSV
        with open(DB_FILE, mode='w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(["ID", "SAP", "Name", "Kat", "Menge", "Soll", "Min", "Preis"])
            for p in products_list:
                writer.writerow([p["id"], p["sap"], p["name"], p["kat"], p["menge"], p["soll_menge"], p["min_monat"], p["preis"]])
        return

    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM lager")
        for p in products_list:
            cur.execute("""
                INSERT INTO lager (item_id, sap, name, kat, menge, soll_menge, min_monat, preis)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (p["id"], p["sap"], p["name"], p["kat"], p["menge"], p["soll_menge"], p["min_monat"], p["preis"]))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Ошибка сохранения в базу: {e}")

# Ваш стандартный класс обработчика запросов сервера
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Здесь работает ваш привычный вывод страниц и интерфейса
        if self.path == '/':
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            
            # Получаем данные из базы
            products = read_db()
            
            # Пример простой генерации страницы (вы можете использовать ваш HTML-шаблон)
            html = f"<html><body><h1>Lagerverwaltung</h1><p>Загружено товаров в базу: {len(products)}</p></body></html>"
            self.wfile.write(html.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        # Здесь обрабатываются сохранения с сайта или загрузка файлов
        self.send_response(302)
        self.send_header('Location', '/')
        self.end_headers()

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), SimpleHandler)
    print(f"Server started on port {PORT}")
    server.serve_forever()
