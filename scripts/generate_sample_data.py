"""Generate the demo store's order history as a Shopify-style orders export.

The store ("Loom & Ember", home fragrance and ceramics) is fictional. The data
is seeded, so every run produces the same CSV. Patterns are baked in on purpose
so the dashboard has something real to find: steady growth, weekend peaks, a
Black Friday / December rush, a summer product, a new product taking off and an
old one fading.

    python scripts/generate_sample_data.py
"""

import csv
import math
import random
from datetime import date, datetime, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "sample_orders.csv"
START = date(2024, 10, 1)
END = date(2026, 10, 11)  # a Sunday, so the last week is complete
BASE_ORDERS_PER_DAY = 9.0

# name, sku, price, popularity, seasonal profile, launch date, yearly trend
PRODUCTS = [
    ("Cedar & Smoke Candle", "LE-CAN-01", 28.00, 10, "winter", None, 0.0),
    ("Fig Leaf Candle", "LE-CAN-02", 28.00, 8, "flat", None, 0.05),
    ("Sea Salt & Sage Candle", "LE-CAN-03", 28.00, 7, "summer", None, 0.0),
    ("Classic Pillar Candle", "LE-CAN-04", 18.00, 7, "flat", None, -0.55),
    ("Amber Reed Diffuser", "LE-DIF-01", 36.00, 6, "flat", None, 0.10),
    ("Summer Linen Room Mist", "LE-MST-01", 22.00, 5, "summer", None, 0.0),
    ("Hand-thrown Ceramic Mug", "LE-CER-01", 32.00, 6, "flat", None, 0.0),
    ("Matcha Ceramic Mug", "LE-CER-02", 34.00, 9, "flat", date(2026, 3, 2), 0.9),
    ("Stoneware Incense Holder", "LE-CER-03", 24.00, 4, "flat", None, 0.0),
    ("Speckled Bud Vase", "LE-CER-04", 26.00, 4, "spring", None, 0.0),
    ("Winter Gift Set", "LE-GFT-01", 68.00, 3, "holiday", None, 0.0),
    ("Self-care Gift Box", "LE-GFT-02", 54.00, 3, "gifting", None, 0.15),
    ("Wick Trimmer", "LE-ACC-01", 14.00, 4, "flat", None, 0.0),
    ("Candle Refill (3-pack)", "LE-ACC-02", 39.00, 3, "flat", None, 0.25),
]

CITIES = [
    ("Austin", "TX", 6), ("Brooklyn", "NY", 8), ("Portland", "OR", 6),
    ("Denver", "CO", 5), ("Chicago", "IL", 6), ("Seattle", "WA", 5),
    ("Los Angeles", "CA", 7), ("Atlanta", "GA", 4), ("Minneapolis", "MN", 3),
    ("Nashville", "TN", 3), ("Boston", "MA", 4), ("San Diego", "CA", 3),
]

SOURCES = [("web", 70), ("instagram", 18), ("pos", 12)]

# relative demand by month for the whole store (Jan..Dec)
STORE_MONTH = [0.78, 0.92, 0.85, 0.88, 1.02, 0.86, 0.80, 0.82, 0.92, 1.05, 1.45, 1.75]
WEEKDAY = [0.86, 0.82, 0.88, 0.95, 1.08, 1.22, 1.19]  # Mon..Sun


def season_factor(profile, d):
    m = d.month
    if profile == "winter":
        return 1.7 if m in (10, 11, 12, 1) else 0.75
    if profile == "summer":
        return 2.2 if m in (6, 7, 8) else (1.1 if m in (5, 9) else 0.45)
    if profile == "spring":
        return 1.8 if m in (3, 4, 5) else 0.8
    if profile == "holiday":
        return 6.0 if m in (11, 12) else 0.25
    if profile == "gifting":  # Valentine's, Mother's Day, December
        return 2.4 if m in (2, 5, 12) else 0.85
    return 1.0


def special_day(d):
    # Black Friday through Cyber Monday: the Friday after the 4th Thursday of November
    nov1 = date(d.year, 11, 1)
    thanksgiving = nov1 + timedelta(days=(3 - nov1.weekday()) % 7 + 21)
    bf = thanksgiving + timedelta(days=1)
    if bf <= d <= bf + timedelta(days=3):
        return 3.2, 0.20
    if (d.month, d.day) in ((2, 12), (2, 13)):
        return 1.6, 0.0
    if d.month == 12 and 10 <= d.day <= 20:
        return 1.3, 0.0
    if d.month == 12 and d.day >= 24:
        return 0.55, 0.0
    return 1.0, 0.0


def poisson(rng, lam):
    if lam > 30:
        return max(0, round(rng.gauss(lam, math.sqrt(lam))))
    limit, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


def pick(rng, weighted):
    return rng.choices([w[0] for w in weighted], weights=[w[-1] for w in weighted])[0]


def main():
    rng = random.Random(2708)
    total_days = (END - START).days
    customers = []  # [email, loyalty weight, city, province]
    order_no = 1001
    rows = []

    for i in range(total_days + 1):
        d = START + timedelta(days=i)
        t = i / 365.0
        growth = 1 + 0.32 * t
        spike, discount_rate = special_day(d)
        lam = BASE_ORDERS_PER_DAY * growth * STORE_MONTH[d.month - 1] * WEEKDAY[d.weekday()] * spike

        product_weights = []
        for name, sku, price, pop, profile, launch, trend in PRODUCTS:
            if launch and d < launch:
                product_weights.append(0)
                continue
            years_in = ((d - launch).days / 365.0) if launch else t
            w = pop * season_factor(profile, d) * max(0.15, 1 + trend * years_in)
            if launch:  # new products ramp up over their first ~4 months
                w *= min(1.0, 0.25 + (d - launch).days / 120)
            product_weights.append(w)

        for _ in range(poisson(rng, lam)):
            returning_p = min(0.42, 0.08 + 0.02 * len(customers) ** 0.5)
            if customers and rng.random() < returning_p:
                cust = rng.choices(customers, weights=[c[1] for c in customers])[0]
            else:
                city, prov = pick(rng, [(c[:2], c[2]) for c in CITIES])
                cust = [f"customer{len(customers) + 1:05d}@example.com",
                        rng.paretovariate(1.6), city, prov]
                customers.append(cust)

            n_lines = rng.choices([1, 2, 3, 4], weights=[58, 28, 10, 4])[0]
            idxs = set()
            while len(idxs) < n_lines:
                idxs.add(rng.choices(range(len(PRODUCTS)), weights=product_weights)[0])
            lines = []
            for idx in sorted(idxs):
                qty = rng.choices([1, 2, 3], weights=[78, 17, 5])[0]
                lines.append((PRODUCTS[idx], qty))

            subtotal_gross = sum(p[2] * q for p, q in lines)
            discount = round(subtotal_gross * discount_rate, 2)
            subtotal = round(subtotal_gross - discount, 2)
            shipping = 0.0 if subtotal >= 50 else 6.95
            created = datetime(d.year, d.month, d.day, rng.randint(7, 22), rng.randint(0, 59), rng.randint(0, 59))
            source = pick(rng, SOURCES)

            for li, (prod, qty) in enumerate(lines):
                first = li == 0
                rows.append({
                    "Name": f"#{order_no}",
                    "Email": cust[0],
                    "Financial Status": "paid",
                    "Created at": created.strftime("%Y-%m-%d %H:%M:%S -0500"),
                    "Subtotal": f"{subtotal:.2f}" if first else "",
                    "Shipping": f"{shipping:.2f}" if first else "",
                    "Total": f"{subtotal + shipping:.2f}" if first else "",
                    "Discount Amount": f"{discount:.2f}" if first else "",
                    "Lineitem quantity": qty,
                    "Lineitem name": prod[0],
                    "Lineitem price": f"{prod[2]:.2f}",
                    "Lineitem sku": prod[1],
                    "Billing City": cust[2] if first else "",
                    "Billing Province": cust[3] if first else "",
                    "Source": source if first else "",
                })
            order_no += 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {order_no - 1001} orders, {len(rows)} line items, {len(customers)} customers -> {OUT}")


if __name__ == "__main__":
    main()
