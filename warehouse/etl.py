"""Build the Walmart star schema in SQLite from the three source CSVs.

A port of original-warehouse-project/create_dw.sql and data_loader.py. The tables,
columns and DIM_TIME rules (2015-2025, Monday=0, weekend = Sat/Sun, meteorological
seasons) match the MySQL version. The original streamed transactions through a
HYBRIDJOIN; here the same equi-join on Customer_ID and Product_ID is done with
in-memory hash maps, which yields the same FACT_SALES rows.
"""

import csv
import sqlite3
from datetime import date, timedelta
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "warehouse"

SCHEMA = """
CREATE TABLE DIM_CUSTOMER (
    customer_key INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL UNIQUE,
    gender TEXT NOT NULL, age TEXT NOT NULL, occupation INTEGER NOT NULL,
    marital_status INTEGER NOT NULL, stay_in_current_city_years INTEGER NOT NULL,
    effective_date TEXT NOT NULL, expiry_date TEXT, is_current INTEGER DEFAULT 1
);
CREATE TABLE DIM_PRODUCT (
    product_key INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT NOT NULL UNIQUE, product_category TEXT NOT NULL, price REAL NOT NULL,
    effective_date TEXT NOT NULL, expiry_date TEXT, is_current INTEGER DEFAULT 1
);
CREATE TABLE DIM_TIME (
    time_key INTEGER PRIMARY KEY AUTOINCREMENT,
    date_value TEXT NOT NULL UNIQUE, day INTEGER NOT NULL, month INTEGER NOT NULL,
    quarter INTEGER NOT NULL, year INTEGER NOT NULL, week_number INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL, day_name TEXT NOT NULL, month_name TEXT NOT NULL,
    is_weekend INTEGER NOT NULL, season TEXT NOT NULL, is_holiday INTEGER DEFAULT 0
);
CREATE TABLE DIM_CITY (
    city_key INTEGER PRIMARY KEY AUTOINCREMENT,
    city_category TEXT NOT NULL UNIQUE, city_name TEXT, region TEXT
);
CREATE TABLE DIM_STORE (
    store_key INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id INTEGER NOT NULL UNIQUE, store_name TEXT NOT NULL,
    effective_date TEXT NOT NULL, expiry_date TEXT, is_current INTEGER DEFAULT 1
);
CREATE TABLE DIM_SUPPLIER (
    supplier_key INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER NOT NULL UNIQUE, supplier_name TEXT NOT NULL,
    effective_date TEXT NOT NULL, expiry_date TEXT, is_current INTEGER DEFAULT 1
);
CREATE TABLE FACT_SALES (
    sales_key INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_key INTEGER NOT NULL REFERENCES DIM_CUSTOMER(customer_key),
    product_key INTEGER NOT NULL REFERENCES DIM_PRODUCT(product_key),
    time_key INTEGER NOT NULL REFERENCES DIM_TIME(time_key),
    city_key INTEGER NOT NULL REFERENCES DIM_CITY(city_key),
    store_key INTEGER NOT NULL REFERENCES DIM_STORE(store_key),
    supplier_key INTEGER NOT NULL REFERENCES DIM_SUPPLIER(supplier_key),
    order_id INTEGER NOT NULL, quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL, total_amount REAL NOT NULL
);
CREATE INDEX idx_customer ON FACT_SALES(customer_key);
CREATE INDEX idx_product ON FACT_SALES(product_key);
CREATE INDEX idx_time ON FACT_SALES(time_key);
CREATE INDEX idx_city ON FACT_SALES(city_key);
CREATE INDEX idx_store ON FACT_SALES(store_key);
CREATE INDEX idx_supplier ON FACT_SALES(supplier_key);
CREATE INDEX idx_order_id ON FACT_SALES(order_id);
CREATE INDEX idx_time_product ON FACT_SALES(time_key, product_key);
"""

SEASONS = {12: "Winter", 1: "Winter", 2: "Winter", 3: "Spring", 4: "Spring", 5: "Spring",
           6: "Summer", 7: "Summer", 8: "Summer", 9: "Fall", 10: "Fall", 11: "Fall"}


def _rows(name):
    with (DATA / name).open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build():
    """Return (connection, stats) for a freshly loaded in-memory warehouse."""
    db = sqlite3.connect(":memory:", check_same_thread=False)
    db.executescript(SCHEMA)
    loaded = date(2024, 1, 1).isoformat()  # fixed effective_date keeps builds reproducible

    # DIM_TIME: every date 2015-2025, as in the original
    d, times = date(2015, 1, 1), []
    while d <= date(2025, 12, 31):
        times.append((d.isoformat(), d.day, d.month, (d.month - 1) // 3 + 1, d.year, d.isocalendar()[1],
                      d.weekday(), d.strftime("%A"), d.strftime("%B"), int(d.weekday() >= 5), SEASONS[d.month]))
        d += timedelta(days=1)
    db.executemany("INSERT INTO DIM_TIME (date_value, day, month, quarter, year, week_number, day_of_week, "
                   "day_name, month_name, is_weekend, season) VALUES (?,?,?,?,?,?,?,?,?,?,?)", times)

    customers = _rows("customer_master_data.csv")
    products = _rows("product_master_data.csv")
    db.executemany(
        "INSERT INTO DIM_CUSTOMER (customer_id, gender, age, occupation, marital_status, "
        "stay_in_current_city_years, effective_date) VALUES (?,?,?,?,?,?,?)",
        [(int(c["Customer_ID"]), c["Gender"], c["Age"], int(c["Occupation"]), int(c["Marital_Status"]),
          int(c["Stay_In_Current_City_Years"]), loaded) for c in customers])
    db.executemany(
        "INSERT INTO DIM_CITY (city_category, city_name) VALUES (?, ?)",
        [(cat, f"City Category {cat}") for cat in sorted({c["City_Category"] for c in customers})])
    db.executemany(
        "INSERT INTO DIM_PRODUCT (product_id, product_category, price, effective_date) VALUES (?,?,?,?)",
        [(p["Product_ID"], p["Product_Category"], float(p["price$"].replace("$", "")), loaded) for p in products])
    db.executemany("INSERT INTO DIM_STORE (store_id, store_name, effective_date) VALUES (?,?,?)",
                   sorted({(int(p["storeID"]), p["storeName"], loaded) for p in products}))
    db.executemany("INSERT INTO DIM_SUPPLIER (supplier_id, supplier_name, effective_date) VALUES (?,?,?)",
                   sorted({(int(p["supplierID"]), p["supplierName"], loaded) for p in products}))

    # lookups for the join (natural key -> surrogate keys)
    key = lambda sql: dict(db.execute(sql))  # noqa: E731
    cust_key = key("SELECT customer_id, customer_key FROM DIM_CUSTOMER")
    prod_key = key("SELECT product_id, product_key FROM DIM_PRODUCT")
    time_key = key("SELECT date_value, time_key FROM DIM_TIME")
    city_key = key("SELECT city_category, city_key FROM DIM_CITY")
    store_key = key("SELECT store_id, store_key FROM DIM_STORE")
    sup_key = key("SELECT supplier_id, supplier_key FROM DIM_SUPPLIER")
    cust = {int(c["Customer_ID"]): c for c in customers}
    prod = {p["Product_ID"]: p for p in products}

    facts, skipped = [], 0
    for t in _rows("transactional_data.csv"):
        c, p = cust.get(int(t["Customer_ID"])), prod.get(t["Product_ID"])
        if c is None or p is None or t["date"] not in time_key:
            skipped += 1
            continue
        qty, price = int(t["quantity"]), float(p["price$"].replace("$", ""))
        facts.append((cust_key[int(c["Customer_ID"])], prod_key[p["Product_ID"]], time_key[t["date"]],
                      city_key[c["City_Category"]], store_key[int(p["storeID"])], sup_key[int(p["supplierID"])],
                      int(t["orderID"]), qty, price, round(qty * price, 2)))
    db.executemany("INSERT INTO FACT_SALES (customer_key, product_key, time_key, city_key, store_key, "
                   "supplier_key, order_id, quantity, unit_price, total_amount) VALUES (?,?,?,?,?,?,?,?,?,?)", facts)
    db.commit()

    stats = {t: db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
             for t in ["DIM_CUSTOMER", "DIM_PRODUCT", "DIM_TIME", "DIM_CITY", "DIM_STORE", "DIM_SUPPLIER", "FACT_SALES"]}
    stats["skipped"] = skipped
    return db, stats
