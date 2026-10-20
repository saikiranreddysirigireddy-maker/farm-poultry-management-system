import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "poultry.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with get_connection() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS poultry_batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_name TEXT NOT NULL,
            breed TEXT NOT NULL,
            initial_birds INTEGER NOT NULL CHECK(initial_birds > 0),
            arrival_date TEXT NOT NULL,
            notes TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS mortality (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id INTEGER NOT NULL,
            count INTEGER NOT NULL CHECK(count > 0),
            loss_date TEXT NOT NULL,
            reason TEXT DEFAULT '',
            FOREIGN KEY(batch_id) REFERENCES poultry_batches(id)
        );
        CREATE TABLE IF NOT EXISTS feed_purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feed_type TEXT NOT NULL,
            quantity_kg REAL NOT NULL CHECK(quantity_kg > 0),
            cost REAL NOT NULL CHECK(cost >= 0),
            purchase_date TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS feed_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feed_type TEXT NOT NULL,
            quantity_kg REAL NOT NULL CHECK(quantity_kg > 0),
            usage_date TEXT NOT NULL,
            notes TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS egg_production (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id INTEGER NOT NULL,
            production_date TEXT NOT NULL,
            egg_count INTEGER NOT NULL CHECK(egg_count >= 0),
            broken_eggs INTEGER NOT NULL CHECK(broken_eggs >= 0),
            notes TEXT DEFAULT '',
            FOREIGN KEY(batch_id) REFERENCES poultry_batches(id)
        );
        CREATE TABLE IF NOT EXISTS vaccinations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id INTEGER,
            vaccine_name TEXT NOT NULL,
            due_date TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Scheduled',
            notes TEXT DEFAULT '',
            FOREIGN KEY(batch_id) REFERENCES poultry_batches(id)
        );
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product TEXT NOT NULL,
            quantity REAL NOT NULL CHECK(quantity > 0),
            unit TEXT DEFAULT '',
            amount REAL NOT NULL CHECK(amount >= 0),
            sale_date TEXT NOT NULL,
            buyer TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            amount REAL NOT NULL CHECK(amount >= 0),
            expense_date TEXT NOT NULL,
            description TEXT DEFAULT ''
        );
        """)

def _rows(query, params=()):
    with get_connection() as conn:
        return [dict(row) for row in conn.execute(query, params).fetchall()]

def _execute(query, params=()):
    with get_connection() as conn:
        cur = conn.execute(query, params)
        return cur.lastrowid

def add_batch(batch_name, breed, initial_birds, arrival_date, notes=""):
    return _execute(
        "INSERT INTO poultry_batches(batch_name, breed, initial_birds, arrival_date, notes) VALUES(?,?,?,?,?)",
        (batch_name, breed, initial_birds, arrival_date, notes)
    )

def get_batches():
    return _rows("""
        SELECT b.id, b.batch_name, b.breed, b.initial_birds, b.arrival_date, b.notes,
               b.initial_birds - COALESCE(SUM(m.count), 0) AS live_birds
        FROM poultry_batches b
        LEFT JOIN mortality m ON b.id = m.batch_id
        GROUP BY b.id
        ORDER BY b.id DESC
    """)

def record_mortality(batch_id, count, loss_date, reason=""):
    batch = next((b for b in get_batches() if b["id"] == batch_id), None)
    if batch is None:
        raise ValueError("Poultry batch not found.")
    if count <= 0 or count > batch["live_birds"]:
        raise ValueError("Mortality count must be positive and no greater than live birds.")
    return _execute(
        "INSERT INTO mortality(batch_id, count, loss_date, reason) VALUES(?,?,?,?)",
        (batch_id, count, loss_date, reason)
    )

def get_mortality_records():
    return _rows("""
        SELECT m.id, b.batch_name, m.count, m.loss_date, m.reason
        FROM mortality m JOIN poultry_batches b ON b.id = m.batch_id
        ORDER BY m.loss_date DESC, m.id DESC
    """)

def add_feed_purchase(feed_type, quantity_kg, cost, purchase_date):
    return _execute(
        "INSERT INTO feed_purchases(feed_type, quantity_kg, cost, purchase_date) VALUES(?,?,?,?)",
        (feed_type, quantity_kg, cost, purchase_date)
    )

def record_feed_usage(feed_type, quantity_kg, usage_date, notes=""):
    available = next((x["quantity_kg"] for x in get_feed_stock() if x["feed_type"] == feed_type), 0)
    if quantity_kg <= 0 or quantity_kg > available:
        raise ValueError("Feed usage must be positive and cannot exceed available stock.")
    return _execute(
        "INSERT INTO feed_usage(feed_type, quantity_kg, usage_date, notes) VALUES(?,?,?,?)",
        (feed_type, quantity_kg, usage_date, notes)
    )

def get_feed_stock():
    return _rows("""
        SELECT p.feed_type,
               ROUND(SUM(p.quantity_kg) - COALESCE(u.used, 0), 2) AS quantity_kg,
               ROUND(SUM(p.cost), 2) AS purchase_cost
        FROM feed_purchases p
        LEFT JOIN (
            SELECT feed_type, SUM(quantity_kg) AS used
            FROM feed_usage GROUP BY feed_type
        ) u ON u.feed_type = p.feed_type
        GROUP BY p.feed_type
        ORDER BY p.feed_type
    """)

def record_eggs(batch_id, production_date, egg_count, broken_eggs, notes=""):
    if broken_eggs > egg_count:
        raise ValueError("Broken eggs cannot exceed total eggs.")
    return _execute(
        "INSERT INTO egg_production(batch_id, production_date, egg_count, broken_eggs, notes) VALUES(?,?,?,?,?)",
        (batch_id, production_date, egg_count, broken_eggs, notes)
    )

def get_egg_records(limit=None):
    query = """
        SELECT e.id, b.batch_name, e.production_date, e.egg_count, e.broken_eggs, e.notes
        FROM egg_production e JOIN poultry_batches b ON b.id = e.batch_id
        ORDER BY e.production_date DESC, e.id DESC
    """
    if limit is not None:
        query += " LIMIT ?"
        return _rows(query, (limit,))
    return _rows(query)

def add_vaccination(batch_id, vaccine_name, due_date, status, notes=""):
    return _execute(
        "INSERT INTO vaccinations(batch_id, vaccine_name, due_date, status, notes) VALUES(?,?,?,?,?)",
        (batch_id, vaccine_name, due_date, status, notes)
    )

def get_vaccinations():
    return _rows("""
        SELECT v.id, COALESCE(b.batch_name, 'All batches') AS batch_name,
               v.vaccine_name, v.due_date, v.status, v.notes
        FROM vaccinations v LEFT JOIN poultry_batches b ON b.id = v.batch_id
        ORDER BY v.due_date ASC, v.id DESC
    """)

def record_sale(product, quantity, unit, amount, sale_date, buyer=""):
    return _execute(
        "INSERT INTO sales(product, quantity, unit, amount, sale_date, buyer) VALUES(?,?,?,?,?,?)",
        (product, quantity, unit, amount, sale_date, buyer)
    )

def get_sales(limit=None):
    query = "SELECT id, product, quantity, unit, amount, sale_date, buyer FROM sales ORDER BY sale_date DESC, id DESC"
    if limit is not None:
        query += " LIMIT ?"
        return _rows(query, (limit,))
    return _rows(query)

def add_expense(category, amount, expense_date, description=""):
    return _execute(
        "INSERT INTO expenses(category, amount, expense_date, description) VALUES(?,?,?,?)",
        (category, amount, expense_date, description)
    )

def get_expenses():
    return _rows("SELECT id, category, amount, expense_date, description FROM expenses ORDER BY expense_date DESC, id DESC")

def get_summary():
    with get_connection() as conn:
        live = conn.execute("""
            SELECT COALESCE(SUM(initial_birds), 0) -
                   COALESCE((SELECT SUM(count) FROM mortality), 0)
            FROM poultry_batches
        """).fetchone()[0]
        today_eggs = conn.execute(
            "SELECT COALESCE(SUM(egg_count), 0) FROM egg_production WHERE production_date = date('now','localtime')"
        ).fetchone()[0]
        total_sales = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM sales").fetchone()[0]
    feed_stock = sum(float(x["quantity_kg"] or 0) for x in get_feed_stock())
    return {
        "live_birds": max(0, int(live or 0)),
        "eggs_today": int(today_eggs or 0),
        "feed_stock": feed_stock,
        "total_sales": float(total_sales or 0),
    }
