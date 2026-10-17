"""Read an orders CSV (Shopify export or a simple one-row-per-item file) into SQLite.

Columns are matched by name, so most exports work without editing:

    order id   Name, Order ID, order_id, Order
    date       Created at, Date, order_date, Paid at
    customer   Email, Customer, customer_id, Customer Email
    product    Lineitem name, Product, product_name, Item
    quantity   Lineitem quantity, Quantity, qty
    price      Lineitem price, Price, unit_price
    subtotal   Subtotal (optional; order-level net sales after discounts)
"""

import csv
import io
import sqlite3
from datetime import datetime

ALIASES = {
    "order": ["name", "order id", "order_id", "order", "order number", "orderid"],
    "date": ["created at", "date", "order_date", "order date", "paid at", "created_at"],
    "customer": ["email", "customer", "customer_id", "customer email", "customer id"],
    "product": ["lineitem name", "product", "product_name", "product name", "item", "title"],
    "qty": ["lineitem quantity", "quantity", "qty"],
    "price": ["lineitem price", "price", "unit_price", "unit price"],
    "subtotal": ["subtotal"],
}
REQUIRED = ["order", "date", "product", "qty", "price"]
LABELS = {"order": "order id", "date": "order date", "product": "product name", "qty": "quantity", "price": "unit price"}
DATE_FORMATS = ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d", "%m/%d/%y"]


class CSVError(ValueError):
    """The file can't be read as orders; the message is shown to the user."""


def _map_columns(header):
    lookup = {h.strip().lower().lstrip("﻿"): h for h in header}
    cols = {}
    for key, names in ALIASES.items():
        for n in names:
            if n in lookup:
                cols[key] = lookup[n]
                break
    missing = [k for k in REQUIRED if k not in cols]
    if missing:
        raise CSVError(
            "Couldn't find a column for: " + ", ".join(LABELS[k] for k in missing)
            + ". Expected a Shopify orders export or columns like order_id, date, product, quantity, price."
        )
    return cols


def _parse_date(value):
    value = value.strip()
    head = value[:10]
    for fmt in DATE_FORMATS:
        for candidate in (head, value.split(" ")[0]):
            try:
                return datetime.strptime(candidate, fmt).date()
            except ValueError:
                pass
    raise ValueError(value)


def _money(value):
    return float(value.replace("$", "").replace(",", "").strip() or 0)


def load(text):
    """Parse CSV text into an in-memory SQLite db with `orders` and `lines` tables."""
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise CSVError("The file is empty.")
    cols = _map_columns(reader.fieldnames)

    orders = {}  # order id -> [day, customer, subtotal or None]
    lines = []
    skipped = 0
    for row in reader:
        oid = (row.get(cols["order"]) or "").strip()
        product = (row.get(cols["product"]) or "").strip()
        if not oid or not product:
            skipped += 1
            continue
        try:
            qty = int(float(row[cols["qty"]] or 0))
            price = _money(row[cols["price"]])
        except (ValueError, TypeError):
            skipped += 1
            continue
        if oid not in orders:
            try:
                day = _parse_date(row[cols["date"]] or "")
            except ValueError:
                skipped += 1
                continue
            customer = (row.get(cols.get("customer", ""), "") or "").strip().lower() or f"guest-{oid}"
            subtotal = None
            if "subtotal" in cols and (row.get(cols["subtotal"]) or "").strip():
                try:
                    subtotal = _money(row[cols["subtotal"]])
                except ValueError:
                    pass
            orders[oid] = [day, customer, subtotal]
        lines.append((oid, orders[oid][0].isoformat(), product, qty, round(qty * price, 2)))

    if not orders:
        raise CSVError("No usable order rows found in the file.")

    db = sqlite3.connect(":memory:", check_same_thread=False)
    db.executescript("""
        CREATE TABLE lines (order_id TEXT, day TEXT, product TEXT, qty INTEGER, revenue REAL);
        CREATE TABLE orders (order_id TEXT PRIMARY KEY, day TEXT, customer TEXT, revenue REAL,
                             is_returning INTEGER DEFAULT 0);
    """)
    db.executemany("INSERT INTO lines VALUES (?,?,?,?,?)", lines)
    gross = dict(db.execute("SELECT order_id, SUM(revenue) FROM lines GROUP BY order_id"))
    db.executemany(
        "INSERT INTO orders (order_id, day, customer, revenue) VALUES (?,?,?,?)",
        [(oid, d.isoformat(), c, s if s is not None else gross.get(oid, 0)) for oid, (d, c, s) in orders.items()],
    )
    # an order is "returning" when the same customer has an earlier order
    db.executescript("""
        CREATE INDEX idx_orders_day ON orders(day);
        CREATE INDEX idx_lines_day ON lines(day);
        UPDATE orders SET is_returning = 1 WHERE order_id IN (
            SELECT order_id FROM (
                SELECT order_id, ROW_NUMBER() OVER (PARTITION BY customer ORDER BY day, order_id) AS n
                FROM orders
            ) WHERE n > 1
        );
    """)
    return db, {"orders": len(orders), "lines": len(lines), "skipped_rows": skipped}
