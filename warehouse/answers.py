"""Turn each query's result rows into a one-line answer and chart data for the page."""

from collections import defaultdict

from . import etl, queries

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
AGES = ["0-17", "18-25", "26-35", "36-45", "46-50", "51-55", "55+"]
SEASONS = ["Spring", "Summer", "Fall", "Winter"]


def money(x):
    if abs(x) >= 1e6:
        return f"${x / 1e6:.2f}M"
    if abs(x) >= 1e4:
        return f"${x / 1e3:.0f}K"
    return f"${x:,.0f}"


def as_dicts(res):
    cols = res["columns"]
    return [dict(zip(cols, r)) for r in res["rows"]]


def share(a, b):
    return a / b if b else 0


def q1(rows):
    months = []
    data = {}
    leaders = {"Weekday": defaultdict(int), "Weekend": defaultdict(int)}
    for r in rows:
        m = r["month_name"][:3]
        if m not in data:
            months.append(m)
            data[m] = {"Weekday": [], "Weekend": []}
        data[m][r["day_type"]].append({"label": r["product_id"], "sub": r["product_category"],
                                       "value": round(r["total_revenue"], 2)})
        if r["revenue_rank"] == 1:
            leaders[r["day_type"]][(r["product_id"], r["product_category"])] += 1
    (wd, wdc), wd_n = max(leaders["Weekday"].items(), key=lambda kv: kv[1])
    (we, wec), we_n = max(leaders["Weekend"].items(), key=lambda kv: kv[1])
    text = (f"{wd} ({wdc}) was the top weekday product in {wd_n} of {len(months)} months of 2020"
            + (f", and it also led weekends in {we_n}." if we == wd else f"; {we} ({wec}) led weekends in {we_n}."))
    return text, {"type": "ranking", "months": months, "data": data, "groups": ["Weekday", "Weekend"]}


def q2(rows):
    top = rows[0]
    by_age = {g: [0.0] * len(AGES) for g in ("M", "F")}
    city_spend, city_cust = defaultdict(float), defaultdict(int)
    for r in rows:
        by_age[r["gender"]][AGES.index(r["age"])] += r["total_purchase_amount"]
        city_spend[r["city_category"]] += r["total_purchase_amount"]
        city_cust[r["city_category"]] += r["customer_count"]
    per = {c: city_spend[c] / city_cust[c] for c in city_spend}
    best_city = max(per, key=per.get)
    gender = "Men" if top["gender"] == "M" else "Women"
    text = (f"{gender} aged {top['age']} in city category {top['city_category']} spent the most: "
            f"{money(top['total_purchase_amount'])} from {top['customer_count']:,} customers. "
            f"Per customer, city {best_city} spends the most ({money(per[best_city])}).")
    return text, {"type": "bars", "labels": AGES, "format": "money", "series": [
        {"name": "Men", "values": [round(v, 2) for v in by_age["M"]]},
        {"name": "Women", "values": [round(v, 2) for v in by_age["F"]]}]}


def q3(rows):
    occs = sorted({r["occupation"] for r in rows})
    cats = sorted({r["product_category"] for r in rows})
    grid = {(r["occupation"], r["product_category"]): r["total_sales"] for r in rows}
    totals = {o: sum(grid.get((o, c), 0) for c in cats) for o in occs}
    top_occ = max(totals, key=totals.get)
    top_cat = defaultdict(int)
    for o in occs:
        top_cat[max(cats, key=lambda c: grid.get((o, c), 0))] += 1
    cat, n = max(top_cat.items(), key=lambda kv: kv[1])
    text = (f"Occupation {top_occ} spends the most overall ({money(totals[top_occ])}). "
            + (f"{cat} is the biggest category for every one of the {n} occupation groups."
               if n == len(occs) else f"{cat} is the biggest category for {n} of {len(occs)} occupation groups."))
    return text, {"type": "matrix", "rows": [f"Occupation {o}" for o in occs], "cols": cats, "scale": "seq",
                  "format": "money", "values": [[round(grid.get((o, c), 0), 2) for c in cats] for o in occs]}


def q4(rows):
    qs = [1, 2, 3, 4]
    by_g = {g: [0.0] * 4 for g in ("M", "F")}
    by_age_q4 = defaultdict(float)
    for r in rows:
        by_g[r["gender"]][r["quarter"] - 1] += r["total_purchases"]
        if r["quarter"] == 4:
            by_age_q4[r["age"]] += r["total_purchases"]
    tot = [by_g["M"][i] + by_g["F"][i] for i in range(4)]
    best = max(range(4), key=lambda i: tot[i])
    top_age = max(by_age_q4, key=by_age_q4.get)
    growth = share(tot[best] - tot[best - 1], tot[best - 1]) if best else None
    text = (f"Q{best + 1} was the biggest quarter of 2020 at {money(tot[best])}"
            + (f", up {growth:.0%} on Q{best}" if growth is not None else "")
            + f". In Q4, {top_age}-year-olds made {share(by_age_q4[top_age], sum(by_age_q4.values())):.0%} of purchases.")
    return text, {"type": "bars", "labels": [f"Q{q}" for q in qs], "format": "money", "series": [
        {"name": "Men", "values": [round(v, 2) for v in by_g["M"]]},
        {"name": "Women", "values": [round(v, 2) for v in by_g["F"]]}]}


def q5(rows):
    groups = defaultdict(list)
    for r in rows:
        groups[r["product_category"]].append({"label": f"Occupation {r['occupation']}", "value": round(r["total_sales"], 2)})
    count = defaultdict(int)
    for items in groups.values():
        for it in items:
            count[it["label"]] += 1
    everywhere = [k.split()[-1] for k, v in sorted(count.items(), key=lambda kv: int(kv[0].split()[-1]))
                  if v == len(groups)]
    if everywhere:
        names = ", ".join(everywhere[:-1]) + (" and " if len(everywhere) > 1 else "") + everywhere[-1]
        text = (f"Occupation{'s' if len(everywhere) > 1 else ''} {names} "
                f"{'appear' if len(everywhere) > 1 else 'appears'} in the top 5 of all {len(groups)} categories.")
    else:
        lead, n = max(count.items(), key=lambda kv: kv[1])
        text = f"{lead} makes the top 5 in {n} of {len(groups)} categories."
    return text, {"type": "minilists", "format": "money",
                  "groups": [{"title": k, "items": v} for k, v in groups.items()]}


def q6(rows):
    months = sorted({(r["year"], r["month"]) for r in rows if r["month"] >= 7})
    cities = sorted({r["city_category"] for r in rows})
    grid = defaultdict(float)
    single = total = 0.0
    lead = defaultdict(int)
    for r in rows:
        if r["month"] < 7:
            continue
        grid[(r["month"], r["city_category"])] += r["total_purchase_amount"]
        total += r["total_purchase_amount"]
        if r["marital_status"] == "Single":
            single += r["total_purchase_amount"]
    for _, m in months:
        lead[max(cities, key=lambda c: grid[(m, c)])] += 1
    city, n = max(lead.items(), key=lambda kv: kv[1])
    text = (f"Single customers made {share(single, total):.0%} of spending from July to December 2020. "
            f"City category {city} led in {n} of {len(months)} months.")
    return text, {"type": "bars", "labels": [MONTHS[m - 1] for _, m in months], "format": "money",
                  "series": [{"name": f"City {c}", "values": [round(grid[(m, c)], 2) for _, m in months]} for c in cities],
                  "footnote": "June 30 (one day) is in the result rows but left out of the chart."}


def q7(rows):
    stays = sorted({r["stay_in_current_city_years"] for r in rows})
    val = {(r["stay_in_current_city_years"], r["gender"]): r["avg_purchase_amount"] for r in rows}
    labels = [f"{s}+ yrs" if s == 4 else f"{s} yr{'s' if s != 1 else ''}" for s in stays]
    m = [val.get((s, "M"), 0) for s in stays]
    f = [val.get((s, "F"), 0) for s in stays]
    text = (f"Time in the city barely moves the average purchase: men spend ${min(m):.0f} to ${max(m):.0f} "
            f"per line item and women ${min(f):.0f} to ${max(f):.0f}, whatever their length of stay.")
    return text, {"type": "bars", "labels": labels, "format": "money2", "series": [
        {"name": "Men", "values": [round(v, 2) for v in m]}, {"name": "Women", "values": [round(v, 2) for v in f]}]}


def q8(rows):
    cats = sorted({r["product_category"] for r in rows})
    cities = sorted({r["city_category"] for r in rows})
    val = {(r["product_category"], r["city_category"]): r["total_revenue"] for r in rows}
    firsts = defaultdict(int)
    for r in rows:
        if r["city_rank"] == 1:
            firsts[r["city_category"]] += 1
    city, n = max(firsts.items(), key=lambda kv: kv[1])
    text = (f"City category {city} is the top earner in {n} of {len(cats)} product categories. "
            f"With only three city categories, the top-5 ranking returns all of them.")
    pct = []
    for c in cities:
        pct.append({"name": f"City {c}", "values": [
            round(share(val.get((k, c), 0), sum(val.get((k, x), 0) for x in cities)) * 100, 1) for k in cats]})
    return text, {"type": "bars", "labels": cats, "format": "pct100", "series": pct, "stacked": True, "horizontal": True}


def q9(rows):
    cats = sorted({r["product_category"] for r in rows})
    grid = {(r["product_category"], r["month"]): r["growth_percentage"] for r in rows}
    cells = [(v, c, m) for (c, m), v in grid.items() if v is not None]
    hi, lo = max(cells), min(cells)
    text = (f"The biggest jump: {hi[1]} grew {hi[0]:.0f}% in {MONTHS[hi[2] - 1]}. "
            f"The sharpest drop: {lo[1]} fell {abs(lo[0]):.0f}% in {MONTHS[lo[2] - 1]}.")
    return text, {"type": "matrix", "rows": cats, "cols": MONTHS, "scale": "div", "format": "pct",
                  "values": [[None if grid.get((c, m)) is None else round(grid[(c, m)], 1) for m in range(1, 13)]
                             for c in cats]}


def q10(rows):
    val = {(r["age"], r["day_type"]): r["total_sales"] for r in rows}
    ages = [a for a in AGES if (a, "Weekday") in val or (a, "Weekend") in val]
    wd = [val.get((a, "Weekday"), 0) for a in ages]
    we = [val.get((a, "Weekend"), 0) for a in ages]
    overall = share(sum(we), sum(we) + sum(wd))
    shares = {a: share(e, e + d) for a, d, e in zip(ages, wd, we)}
    lean = max(shares, key=shares.get)
    text = (f"Weekends brought {overall:.0%} of 2020 sales from 29% of the days. "
            f"The {lean} group leans on weekends most ({shares[lean]:.0%} of their spend).")
    return text, {"type": "bars", "labels": ages, "format": "money", "series": [
        {"name": "Weekday", "values": [round(v, 2) for v in wd]}, {"name": "Weekend", "values": [round(v, 2) for v in we]}]}


def q11(rows):
    top = max(rows, key=lambda r: r["total_quantity"])
    units = sum(r["total_quantity"] for r in rows)
    text = (f"The 120 ranked product-months moved {units:,} units. The single biggest was "
            f"{top['product_id']} ({top['product_category']}): {top['total_quantity']:,} units on "
            f"{top['day_type'].lower()}s in {top['month_name']}.")
    return text, None


def q12(rows):
    stores = []
    grid = {}
    for r in rows:
        if r["store_name"] not in stores:
            stores.append(r["store_name"])
        grid[(r["store_name"], r["current_quarter"])] = r["growth_rate_percentage"]
    rev = {(r["store_name"], r["current_quarter"]): r["current_quarter_revenue"] for r in rows}
    change = {s: share(rev[(s, 4)] - rev[(s, 1)], rev[(s, 1)]) for s in stores if (s, 1) in rev and (s, 4) in rev}
    up, down = max(change, key=change.get), min(change, key=change.get)
    text = (f"From Q1 to Q4 2017, {up} grew fastest ({change[up]:+.0%}) while {down} "
            f"{'shrank' if change[down] < 0 else 'grew slowest'} ({change[down]:+.0%}).")
    return text, {"type": "matrix", "rows": stores, "cols": ["Q2", "Q3", "Q4"], "scale": "div", "format": "pct",
                  "values": [[None if grid.get((s, q)) is None else round(grid[(s, q)], 1) for q in (2, 3, 4)]
                             for s in stores]}


def q13(rows):
    stores, sups = [], []
    val = defaultdict(float)
    for r in rows:
        if r["store_name"] not in stores:
            stores.append(r["store_name"])
        if r["supplier_name"] not in sups:
            sups.append(r["supplier_name"])
        val[(r["store_name"], r["supplier_name"])] += r["total_sales"]
    sups.sort(key=lambda s: -sum(val[(x, s)] for x in stores))
    leader = defaultdict(int)
    for s in stores:
        leader[max(sups, key=lambda p: val[(s, p)])] += 1
    sup, n = max(leader.items(), key=lambda kv: kv[1])
    text = f"{sup} is the largest supplier at {n} of {len(stores)} stores, across {len(rows)} store-supplier-product rows."
    return text, {"type": "bars", "labels": stores, "format": "money", "stacked": True, "horizontal": True,
                  "series": [{"name": p, "values": [round(val[(s, p)], 2) for s in stores]} for p in sups]}


def q14(rows):
    cats = sorted({r["product_category"] for r in rows})
    val = defaultdict(float)
    for r in rows:
        val[(r["product_category"], r["season"])] += r["total_sales"]
    pct = {c: [share(val[(c, s)], sum(val[(c, x)] for x in SEASONS)) * 100 for s in SEASONS] for c in cats}
    peak = {c: max(range(4), key=lambda i: pct[c][i]) for c in cats}
    strongest = max(cats, key=lambda c: pct[c][peak[c]])
    steady = min(cats, key=lambda c: max(pct[c]) - min(pct[c]))
    text = (f"{strongest} is the most seasonal: {pct[strongest][peak[strongest]]:.0f}% of its sales land in "
            f"{SEASONS[peak[strongest]]}. {steady} is the steadiest, selling about the same in every season.")
    return text, {"type": "matrix", "rows": cats, "cols": SEASONS, "scale": "seq", "format": "pct",
                  "values": [[round(v, 1) for v in pct[c]] for c in cats],
                  "footnote": "Share of each category's 2017–2020 sales by season; rows add to 100%."}


def q15(rows):
    stores, sups = [], []
    vols = defaultdict(list)
    for r in rows:
        if r["store_name"] not in stores:
            stores.append(r["store_name"])
        if r["supplier_name"] not in sups:
            sups.append(r["supplier_name"])
        if r["volatility_percentage"] is not None:
            vols[(r["store_name"], r["supplier_name"])].append(r["volatility_percentage"])
    avg = {k: sum(v) / len(v) for k, v in vols.items() if len(v) >= 6}
    hi, lo = max(avg, key=avg.get), min(avg, key=avg.get)
    text = (f"{hi[1]} at {hi[0]} swings the most, {avg[hi]:.0f}% month to month on average. "
            f"The steadiest pair is {lo[1]} at {lo[0]} ({avg[lo]:.0f}%).")
    return text, {"type": "matrix", "rows": stores, "cols": sups, "scale": "seq", "format": "pct",
                  "values": [[round(avg[(s, p)], 1) if (s, p) in avg else None for p in sups] for s in stores],
                  "footnote": "Average absolute month-over-month change; blank where a store doesn't carry that supplier."}


def q16(rows):
    top = rows[0]
    text = (f"{top['product1_id']} ({top['product1_category']}) and {top['product2_id']} "
            f"({top['product2_category']}) were bought together in {top['co_purchase_count']:,} orders, "
            f"the strongest pairing in the warehouse.")
    return text, {"type": "pairs", "items": [
        {"a": r["product1_id"], "a_cat": r["product1_category"], "b": r["product2_id"],
         "b_cat": r["product2_category"], "value": r["co_purchase_count"]} for r in rows]}


def q17(rows):
    stores = [r for r in rows if r["supplier_name"] == "ALL SUPPLIERS" and r["store_name"] != "ALL STORES"]
    grand = next(r for r in rows if r["store_name"] == "ALL STORES")
    stores.sort(key=lambda r: -r["total_revenue"])
    top = stores[0]
    sup_rows = [r for r in rows if r["store_name"] == top["store_name"] and r["supplier_name"] != "ALL SUPPLIERS"
                and r["product_category"] == "ALL PRODUCTS"]
    best_sup = max(sup_rows, key=lambda r: r["total_revenue"])
    text = (f"The ROLLUP grand total is {money(grand['total_revenue'])}. {top['store_name']} is the largest store "
            f"({share(top['total_revenue'], grand['total_revenue']):.0%}), and {best_sup['supplier_name']} "
            f"supplies {share(best_sup['total_revenue'], top['total_revenue']):.0%} of it.")
    return text, {"type": "bars", "labels": [r["store_name"] for r in stores], "format": "money", "horizontal": True,
                  "series": [{"name": "Revenue, 2017–2020", "values": [round(r["total_revenue"], 2) for r in stores]}]}


def q18(rows):
    cats = sorted({r["product_category"] for r in rows})
    val = defaultdict(float)
    for r in rows:
        val[(r["product_category"], r["half_year"][:2])] += r["total_revenue"]
    h1, h2 = sum(val[(c, "H1")] for c in cats), sum(val[(c, "H2")] for c in cats)
    growth = {c: share(val[(c, "H2")] - val[(c, "H1")], val[(c, "H1")]) for c in cats}
    lead = max(growth, key=growth.get)
    text = (f"Second-half 2020 revenue was {share(h2 - h1, h1):+.0%} against the first half, "
            f"led by {lead} ({growth[lead]:+.0%}).")
    return text, {"type": "bars", "labels": cats, "format": "money", "series": [
        {"name": "H1 (Jan–Jun)", "values": [round(val[(c, "H1")], 2) for c in cats]},
        {"name": "H2 (Jul–Dec)", "values": [round(val[(c, "H2")], 2) for c in cats]}]}


def q19(rows):
    high = [r for r in rows if r["outlier_flag"].endswith("High Spike")]
    cats = sorted({r["product_category"] for r in rows})
    count = defaultdict(int)
    for r in high:
        count[r["product_category"]] += 1
    top = max(high, key=lambda r: r["deviation_percentage"])
    holiday = share(sum(1 for r in high if r["date_value"][5:7] in ("11", "12")), len(high))
    text = (f"{len(high):,} product-days ran above twice their daily average ({len(rows) - len(high):,} fell below half). "
            f"The biggest spike: {top['product_id']} on {top['date_value']}, {top['deviation_percentage']:+.0f}%. "
            f"{holiday:.0%} of high spikes fall in November and December.")
    return text, {"type": "bars", "labels": cats, "format": "int", "horizontal": True,
                  "series": [{"name": "High-spike days", "values": [count[c] for c in cats]}]}


def q20(rows):
    stores = sorted({r["store_name"] for r in rows})
    quarters = sorted({(r["year"], r["quarter"]) for r in rows})
    val = {(r["store_name"], r["year"], r["quarter"]): r["total_revenue"] for r in rows}
    first, last = quarters[0], quarters[-1]
    growth = {s: share(val.get((s, *last), 0) - val.get((s, *first), 0), val.get((s, *first), 0)) for s in stores}
    fast = max(growth, key=growth.get)
    text = (f"The view returns {len(rows)} store-quarters. {fast} grew the most, "
            f"{growth[fast]:+.0%} from Q{first[1]} {first[0]} to Q{last[1]} {last[0]}.")
    return text, {"type": "matrix", "rows": stores, "cols": [f"Q{q} {str(y)[2:]}" for y, q in quarters],
                  "scale": "seq", "format": "money",
                  "values": [[round(val.get((s, y, q), 0), 2) for y, q in quarters] for s in stores]}


SHAPERS = {f"q{i}": globals()[f"q{i}"] for i in range(1, 21)}


def _overview(db):
    q = lambda sql, *a: db.execute(sql, a).fetchall()  # noqa: E731
    yearly = {y: (s, o, c, p) for y, s, o, c, p in q(
        "SELECT t.year, SUM(f.total_amount), COUNT(DISTINCT f.order_id), COUNT(DISTINCT f.customer_key), "
        "COUNT(DISTINCT f.product_key) FROM FACT_SALES f JOIN DIM_TIME t ON f.time_key = t.time_key GROUP BY t.year")}
    last, prev = max(yearly), max(yearly) - 1
    # sales, orders, active customers, average order value
    vals = {y: (s, o, c, s / o) for y, (s, o, c, _) in yearly.items()}
    labels = ["Total sales", "Total orders", "Active customers", "Average order value"]
    formats = ["money", "int", "int", "money2"]
    kpis = [{"label": f"{labels[i]}, {last}", "value": vals[last][i], "format": formats[i],
             "delta": share(vals[last][i] - vals[prev][i], vals[prev][i]), "vs": str(prev)} for i in range(4)]
    totals = q("SELECT SUM(total_amount), COUNT(DISTINCT order_id), COUNT(DISTINCT customer_key) FROM FACT_SALES")[0]

    monthly = q("SELECT t.year, t.month, SUM(f.total_amount) FROM FACT_SALES f JOIN DIM_TIME t "
                "ON f.time_key = t.time_key GROUP BY t.year, t.month ORDER BY t.year, t.month")
    cats = q("SELECT p.product_category, SUM(f.total_amount) s FROM FACT_SALES f JOIN DIM_PRODUCT p "
             "ON f.product_key = p.product_key GROUP BY 1 ORDER BY s DESC")
    cat_total = sum(s for _, s in cats)
    donut = [{"label": c, "value": round(s, 2), "share": s / cat_total} for c, s in cats[:4]]
    donut.append({"label": "Other", "value": round(sum(s for _, s in cats[4:]), 2),
                  "share": sum(s for _, s in cats[4:]) / cat_total, "detail": ", ".join(c for c, _ in cats[4:])})
    top_products = q("SELECT p.product_id, p.product_category, SUM(f.total_amount) s FROM FACT_SALES f "
                     "JOIN DIM_PRODUCT p ON f.product_key = p.product_key GROUP BY 1, 2 ORDER BY s DESC LIMIT 5")
    stores = q("SELECT store_name, SUM(total_revenue) s FROM STORE_QUARTERLY_SALES GROUP BY 1 ORDER BY s DESC")
    cities = q("SELECT c.city_category, SUM(f.total_amount) s, COUNT(DISTINCT f.customer_key) FROM FACT_SALES f "
               "JOIN DIM_CITY c ON f.city_key = c.city_key GROUP BY 1 ORDER BY s DESC")
    recent = q("SELECT f.order_id, c.customer_id, COUNT(*), SUM(f.total_amount), t.date_value FROM FACT_SALES f "
               "JOIN DIM_CUSTOMER c ON f.customer_key = c.customer_key JOIN DIM_TIME t ON f.time_key = t.time_key "
               "GROUP BY f.order_id ORDER BY f.order_id DESC LIMIT 6")
    span = q("SELECT MIN(t.date_value), MAX(t.date_value) FROM FACT_SALES f JOIN DIM_TIME t ON f.time_key = t.time_key")[0]
    return {
        "span": span, "kpis": kpis,
        "totals": {"sales": totals[0], "orders": totals[1], "customers": totals[2]},
        "monthly": {"labels": [f"{MONTHS[m - 1]} {y}" for y, m, _ in monthly], "values": [round(v, 2) for _, _, v in monthly]},
        "categories": donut,
        "top_products": [{"id": p, "category": c, "value": round(s, 2)} for p, c, s in top_products],
        "stores": [{"name": n, "value": round(s, 2)} for n, s in stores],
        "cities": [{"name": f"City {c}", "value": round(s, 2), "customers": n} for c, s, n in cities],
        "recent": [{"order": o, "customer": c, "items": i, "amount": round(a, 2), "date": d} for o, c, i, a, d in recent],
    }


def _clean(v):
    return round(v, 2) if isinstance(v, float) else v


def build(preview_rows=12):
    db, stats = etl.build()
    results = queries.run(db)
    out = []
    for q in queries.Q:
        res = results[q["id"]]
        headline, chart = SHAPERS[q["id"]](as_dicts(res))
        out.append({**{k: q[k] for k in ("id", "title", "view", "tags", "question", "sql", "note", "setup")},
                    "headline": headline, "chart": chart, "columns": res["columns"],
                    "preview": [[_clean(v) for v in r] for r in res["rows"][:preview_rows]],
                    "row_count": len(res["rows"]), "ms": res["ms"]})
    overview = _overview(db)
    overview["insights"] = [
        {"title": "Sales growth", "query": "q9", "text": out[8]["headline"]},
        {"title": "Bought together", "query": "q16", "text": out[15]["headline"]},
        {"title": "Customer trend", "query": "q10", "text": out[9]["headline"]},
        {"title": "Seasonality", "query": "q14", "text": out[13]["headline"]},
    ]
    return {"stats": stats, "queries": out, "overview": overview,
            "query_ms": round(sum(r["ms"] for r in results.values()), 0)}, db, results
