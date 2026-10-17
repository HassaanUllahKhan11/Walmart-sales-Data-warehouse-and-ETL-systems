"""Recreate the warehouse project's three source CSVs (they were never committed).

Writes data/warehouse/ in the exact column layout the original ETL reads:

    customer_master_data.csv   Customer_ID, Gender, Age, Occupation, City_Category,
                               Stay_In_Current_City_Years, Marital_Status
    product_master_data.csv    Product_ID, Product_Category, price$, storeID, storeName,
                               supplierID, supplierName
    transactional_data.csv     orderID, Customer_ID, Product_ID, quantity, date

This is a stand-in at reduced scale (the report describes 550,068 rows): the same
customer count, 8 stores, 7 suppliers and city categories A/B/C, with orders from
2017 to 2020 so every query in queries_dw.sql has data. Seeded, so reruns match.

    python scripts/generate_warehouse_data.py
"""

import csv
import math
import random
from datetime import date, timedelta
from itertools import accumulate
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "warehouse"
START, END = date(2017, 1, 1), date(2020, 12, 31)
N_CUSTOMERS = 5891
ORDERS_PER_DAY = 30.0

AGES = [("0-17", 3), ("18-25", 18), ("26-35", 40), ("36-45", 20), ("46-50", 8), ("51-55", 7), ("55+", 4)]
OCCUPATIONS = [(i, w) for i, w in enumerate(
    [13, 8, 5, 3, 13, 2, 4, 11, 1, 1, 2, 2, 6, 1, 5, 2, 5, 7, 1, 2, 6])]

STORES = [(1, "Riverside Supercenter"), (2, "Oak Park"), (3, "Lakeview"), (4, "Hillcrest"),
          (5, "Downtown Market"), (6, "Westfield"), (7, "Northgate"), (8, "Harbor Point")]
# store demand weight and quarterly shape (used to give 2017 store growth some story)
STORE_SHAPE = {1: (1.5, 0.00), 2: (1.0, 0.04), 3: (0.9, -0.03), 4: (0.8, 0.02),
               5: (1.2, 0.10), 6: (0.7, 0.00), 7: (0.6, 0.18), 8: (0.9, -0.06)}

# category: supplier, price range, demand weight, seasonal months boost, product count
CATEGORIES = {
    "Electronics":          (2, (29, 449), 7, {11: 1.9, 12: 1.6}, 50),
    "Grocery":              (1, (2, 25), 22, {11: 1.2, 12: 1.3}, 80),
    "Home & Kitchen":       (3, (9, 199), 10, {5: 1.2, 11: 1.3, 12: 1.3}, 55),
    "Clothing":             (7, (8, 79), 12, {3: 1.3, 4: 1.3, 9: 1.3, 10: 1.2}, 60),
    "Health & Beauty":      (5, (4, 59), 9, {2: 1.2, 5: 1.2, 12: 1.2}, 45),
    "Toys & Games":         (6, (8, 119), 6, {11: 2.3, 12: 2.8}, 40),
    "Sports & Outdoors":    (4, (12, 249), 6, {5: 1.4, 6: 1.7, 7: 1.7, 8: 1.4}, 35),
    "Household Essentials": (1, (3, 29), 14, {}, 35),
}
SUPPLIERS = {1: "Meridian Foods", 2: "Brightline Electronics", 3: "Evergreen Home", 4: "Summit Sports",
             5: "Pure Care Labs", 6: "Playmakers Toys", 7: "Threadline Apparel"}

# demographic taste: multiplier on category demand
TASTE = {
    "M": {"Electronics": 1.5, "Sports & Outdoors": 1.4, "Health & Beauty": 0.6, "Clothing": 0.8},
    "F": {"Health & Beauty": 1.7, "Clothing": 1.4, "Home & Kitchen": 1.2, "Electronics": 0.6},
    "0-17": {"Toys & Games": 2.0, "Electronics": 1.3, "Grocery": 0.5, "Household Essentials": 0.3},
    "18-25": {"Electronics": 1.4, "Clothing": 1.3, "Household Essentials": 0.7},
    "36-45": {"Toys & Games": 1.6, "Home & Kitchen": 1.2},
    "46-50": {"Home & Kitchen": 1.3, "Grocery": 1.2},
    "51-55": {"Grocery": 1.3, "Health & Beauty": 1.2, "Toys & Games": 0.7},
    "55+": {"Grocery": 1.4, "Health & Beauty": 1.3, "Electronics": 0.6, "Toys & Games": 0.8},
}


def bf_factor(d):
    nov1 = date(d.year, 11, 1)
    bf = nov1 + timedelta(days=(3 - nov1.weekday()) % 7 + 22)  # day after 4th Thursday
    if bf <= d <= bf + timedelta(days=3):
        return 2.6
    if d.month == 12 and 8 <= d.day <= 22:
        return 1.35
    return 1.0


def poisson(rng, lam):
    return max(0, round(rng.gauss(lam, math.sqrt(lam)))) if lam > 30 else _knuth(rng, lam)


def _knuth(rng, lam):
    limit, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


def main():
    rng = random.Random(1695)
    OUT.mkdir(parents=True, exist_ok=True)

    # customers
    customers = []
    for i in range(N_CUSTOMERS):
        gender = "M" if rng.random() < 0.72 else "F"
        age = rng.choices([a for a, _ in AGES], [w for _, w in AGES])[0]
        city = rng.choices("ABC", [27, 42, 31])[0]
        customers.append({
            "Customer_ID": 1000001 + i, "Gender": gender, "Age": age,
            "Occupation": rng.choices([o for o, _ in OCCUPATIONS], [w for _, w in OCCUPATIONS])[0],
            "City_Category": city,
            "Stay_In_Current_City_Years": rng.choices(range(5), [14, 35, 18, 17, 16])[0],
            "Marital_Status": 1 if rng.random() < 0.41 else 0,
            # spend propensity: city C shops less often but spends more per basket
            "_weight": rng.paretovariate(1.4) * {"A": 1.0, "B": 1.1, "C": 0.8}[city],
            "_basket": {"A": 0.95, "B": 1.0, "C": 1.15}[city],
        })

    # products (each product is stocked by one store and one supplier, as in the original master data)
    products, by_cat, used = [], {}, set()
    for cat, (sup, (lo, hi), _, _, n) in CATEGORIES.items():
        # deal each category's products across stores so every store carries a mix
        deck = []
        while len(deck) < n:
            batch = [s for s, _ in STORES for _ in range(round(STORE_SHAPE[s][0] * 2))]
            rng.shuffle(batch)
            deck += batch
        for i in range(n):
            pid = None
            while pid is None or pid in used:
                pid = f"P00{rng.randint(10000, 399999):06d}"
            used.add(pid)
            store = STORES[deck[i] - 1]
            price = round(math.exp(rng.uniform(math.log(lo), math.log(hi))), 2)
            p = {"Product_ID": pid, "Product_Category": cat, "price$": f"${price:.2f}",
                 "storeID": store[0], "storeName": store[1], "supplierID": sup, "supplierName": SUPPLIERS[sup],
                 "_price": price, "_pop": rng.paretovariate(1.8)}
            products.append(p)
            by_cat.setdefault(cat, []).append(p)

    # a few products that are usually bought together (for the affinity query)
    pairs = {}
    for a_cat, b_cat in [("Electronics", "Electronics"), ("Grocery", "Household Essentials"),
                         ("Home & Kitchen", "Home & Kitchen"), ("Toys & Games", "Electronics"),
                         ("Sports & Outdoors", "Clothing"), ("Health & Beauty", "Health & Beauty"),
                         ("Grocery", "Grocery")]:
        a = max(by_cat[a_cat], key=lambda p: p["_pop"] if p["Product_ID"] not in pairs else -1)
        b = max((p for p in by_cat[b_cat] if p is not a and p["Product_ID"] not in pairs),
                key=lambda p: p["_pop"])
        pairs[a["Product_ID"]], pairs[b["Product_ID"]] = b, a

    cust_cum = list(accumulate(c["_weight"] for c in customers))
    cats = list(CATEGORIES)
    rows, order_id = [], 100001
    d = START
    while d <= END:
        t = (d - START).days / 365.0
        weekend = 1.25 if d.weekday() >= 5 else 1.0
        lam = ORDERS_PER_DAY * (1 + 0.09 * t) * weekend * bf_factor(d)
        q = (d.month - 1) // 3
        # per-store multiplier drifts by quarter so stores grow at different rates
        store_mult = {s: max(0.3, 1 + g * (4 * (d.year - 2017) + q)) for s, (_, g) in STORE_SHAPE.items()}
        cat_season = {c: CATEGORIES[c][2] * CATEGORIES[c][3].get(d.month, 1.0) for c in cats}
        pool_cum = {k: list(accumulate(x["_pop"] * store_mult[x["storeID"]] for x in by_cat[k])) for k in cats}
        for _ in range(poisson(rng, lam)):
            c = rng.choices(customers, cum_weights=cust_cum)[0]
            w = [cat_season[k] * TASTE[c["Gender"]].get(k, 1) * TASTE.get(c["Age"], {}).get(k, 1) for k in cats]
            n_items = rng.choices([1, 2, 3, 4], [50, 30, 14, 6])[0]
            basket = []
            for _ in range(n_items):
                cat = rng.choices(cats, w)[0]
                p = rng.choices(by_cat[cat], cum_weights=pool_cum[cat])[0]
                if p not in basket:
                    basket.append(p)
                partner = pairs.get(p["Product_ID"])
                if partner and partner not in basket and rng.random() < 0.25:
                    basket.append(partner)
            for p in basket:
                qty = rng.choices([1, 2, 3, 4], [70, 20, 7, 3])[0]
                if c["_basket"] > 1 and rng.random() < 0.15:
                    qty += 1
                rows.append({"orderID": order_id, "Customer_ID": c["Customer_ID"], "Product_ID": p["Product_ID"],
                             "quantity": qty, "date": d.isoformat()})
            order_id += 1
        d += timedelta(days=1)

    def write(name, data):
        fields = [k for k in data[0] if not k.startswith("_")]
        with (OUT / name).open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(data)

    write("customer_master_data.csv", customers)
    write("product_master_data.csv", products)
    write("transactional_data.csv", rows)
    print(f"{len(customers):,} customers, {len(products):,} products, "
          f"{order_id - 100001:,} orders, {len(rows):,} transaction rows -> {OUT}")


if __name__ == "__main__":
    main()
