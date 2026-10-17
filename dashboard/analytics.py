"""Turn the orders db into the numbers a shop owner checks every Monday."""

from collections import defaultdict
from datetime import date, timedelta

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July",
               "August", "September", "October", "November", "December"]


def money(x):
    return f"${x:,.0f}"


def pct(new, old):
    if not old:
        return None
    return (new - old) / old


def _day(s):
    return date.fromisoformat(s)


def _sum_between(daily, start, end):
    total, d = 0.0, start
    while d <= end:
        total += daily.get(d, 0.0)
        d += timedelta(days=1)
    return total


def _month_end(y, m):
    return date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1)


def build(db):
    q = db.execute
    first_day, as_of = map(_day, q("SELECT MIN(day), MAX(day) FROM orders").fetchone())
    daily = {_day(d): r for d, r in q("SELECT day, SUM(revenue) FROM orders GROUP BY day")}

    # last complete Monday-Sunday week
    week_end = as_of - timedelta(days=(as_of.weekday() + 1) % 7)
    week_start = week_end - timedelta(days=6)

    out = {
        "as_of": as_of.isoformat(),
        "first_day": first_day.isoformat(),
        "week": {"start": week_start.isoformat(), "end": week_end.isoformat()},
    }
    out["kpis"] = _kpis(q, as_of)
    out["weekly"] = _weekly(daily, first_day, week_end)
    out["top_products"] = _top_products(q, as_of)
    out["customer_mix"] = _customer_mix(q, first_day, as_of)
    out["seasonality"] = _seasonality(daily, first_day, as_of)
    out["weekday"] = _weekday(daily, first_day, week_end)
    out["winback"] = _winback(q, as_of)
    out["insights"] = _insights(q, daily, first_day, week_start, week_end, out)
    return out


def _kpis(q, as_of):
    cur_start = as_of - timedelta(days=29)
    prev_start, prev_end = as_of - timedelta(days=59), as_of - timedelta(days=30)

    def window(a, b):
        rev, n, ret = q(
            "SELECT COALESCE(SUM(revenue),0), COUNT(*), COALESCE(SUM(revenue * is_returning),0) "
            "FROM orders WHERE day BETWEEN ? AND ?", (a.isoformat(), b.isoformat())).fetchone()
        return {"revenue": rev, "orders": n, "aov": rev / n if n else 0, "returning_share": ret / rev if rev else 0}

    cur, prev = window(cur_start, as_of), window(prev_start, prev_end)
    has_prev = prev["orders"] > 0
    customers, repeaters = q(
        "SELECT COUNT(*), SUM(n > 1) FROM (SELECT COUNT(*) n FROM orders GROUP BY customer)").fetchone()
    kpis = [
        {"id": "revenue", "label": "Revenue, last 30 days", "format": "money"},
        {"id": "orders", "label": "Orders, last 30 days", "format": "int"},
        {"id": "aov", "label": "Average order value", "format": "money2"},
        {"id": "returning_share", "label": "Revenue from returning customers", "format": "pct"},
    ]
    for k in kpis:
        k["value"] = cur[k["id"]]
        k["prior"] = prev[k["id"]] if has_prev else None
        if not has_prev:
            k["delta"] = None
        elif k["format"] == "pct":
            k["delta"] = cur[k["id"]] - prev[k["id"]]  # percentage points
        else:
            k["delta"] = pct(cur[k["id"]], prev[k["id"]])
    kpis.append({"id": "repeat_rate", "label": "Customers who came back", "format": "pct",
                 "value": (repeaters or 0) / customers if customers else 0, "prior": None, "delta": None,
                 "note": f"{repeaters or 0:,} of {customers:,} customers ordered more than once"})
    return kpis


def _weekly(daily, first_day, week_end):
    """Weekly revenue for up to the last 52 complete weeks, with the same week a year earlier."""
    first_monday = first_day + timedelta(days=(7 - first_day.weekday()) % 7)  # first full week
    weeks = []
    start = week_end - timedelta(days=6)
    while start >= first_monday and len(weeks) < 52:
        weeks.append(start)
        start -= timedelta(days=7)
    weeks.reverse()
    labels, revenue, last_year = [], [], []
    for w in weeks:
        labels.append(w.isoformat())
        revenue.append(round(_sum_between(daily, w, w + timedelta(days=6)), 2))
        ly = w - timedelta(weeks=52)
        last_year.append(round(_sum_between(daily, ly, ly + timedelta(days=6)), 2) if ly >= first_monday else None)
    return {"labels": labels, "revenue": revenue, "last_year": last_year}


def _top_products(q, as_of, n=8):
    cur_start = as_of - timedelta(days=89)
    prev_start, prev_end = as_of - timedelta(days=179), as_of - timedelta(days=90)
    prev = dict(q("SELECT product, SUM(revenue) FROM lines WHERE day BETWEEN ? AND ? GROUP BY product",
                  (prev_start.isoformat(), prev_end.isoformat())))
    rows = q("SELECT product, SUM(revenue) r, SUM(qty) FROM lines WHERE day BETWEEN ? AND ? "
             "GROUP BY product ORDER BY r DESC", (cur_start.isoformat(), as_of.isoformat())).fetchall()
    total = sum(r[1] for r in rows) or 1
    return [{"product": p, "revenue": round(r, 2), "units": u, "share": r / total,
             "change": pct(r, prev.get(p, 0))} for p, r, u in rows[:n]]


def _customer_mix(q, first_day, as_of):
    """New vs returning revenue for the last 12 calendar months (current month partial)."""
    rows = q("SELECT substr(day,1,7) m, SUM(revenue * (1 - is_returning)), SUM(revenue * is_returning) "
             "FROM orders GROUP BY m ORDER BY m").fetchall()
    rows = rows[-12:]
    labels = []
    for m, _, _ in rows:
        y, mo = int(m[:4]), int(m[5:])
        partial = (y, mo) == (as_of.year, as_of.month) and as_of != _month_end(y, mo)
        labels.append(f"{MONTHS[mo - 1]} {str(y)[2:]}" + ("*" if partial else ""))
    return {"labels": labels, "new": [round(r[1], 2) for r in rows], "returning": [round(r[2], 2) for r in rows]}


def _complete_months(daily, first_day, as_of):
    """{(year, month): revenue} for calendar months fully covered by the data."""
    months = {}
    y, m = first_day.year, first_day.month
    while (y, m) <= (as_of.year, as_of.month):
        start, end = date(y, m, 1), _month_end(y, m)
        if start >= first_day and end <= as_of:
            months[(y, m)] = _sum_between(daily, start, end)
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return months


def _seasonality(daily, first_day, as_of):
    months = _complete_months(daily, first_day, as_of)
    years = sorted({y for y, _ in months})[-3:]
    series = [{"year": y, "values": [round(months[(y, m)], 2) if (y, m) in months else None
                                     for m in range(1, 13)]} for y in years]
    return {"labels": MONTHS, "series": series}


def _weekday(daily, first_day, week_end, weeks=12):
    start = max(week_end - timedelta(days=7 * weeks - 1), first_day)
    totals, counts = [0.0] * 7, [0] * 7
    d = start
    while d <= week_end:
        totals[d.weekday()] += daily.get(d, 0.0)
        counts[d.weekday()] += 1
        d += timedelta(days=1)
    return {"labels": [w[:3] for w in WEEKDAYS],
            "avg_revenue": [round(t / c, 2) if c else 0 for t, c in zip(totals, counts)],
            "weeks": weeks}


def _winback(q, as_of):
    """Repeat customers who've gone quiet for 90-365 days: the cheapest sales to win back."""
    lo, hi = (as_of - timedelta(days=365)).isoformat(), (as_of - timedelta(days=90)).isoformat()
    count, spend = q(
        "SELECT COUNT(*), COALESCE(SUM(spend),0) FROM (SELECT customer, COUNT(*) n, MAX(day) last, "
        "SUM(revenue) spend FROM orders WHERE customer NOT LIKE 'guest-%' GROUP BY customer) "
        "WHERE n >= 2 AND last BETWEEN ? AND ?", (lo, hi)).fetchone()
    return {"count": count, "lifetime_value": round(spend, 2)}


def _insights(q, daily, first_day, week_start, week_end, out):
    """Plain-English notes about last week, each backed by a number on the page."""
    notes = []
    if week_start < first_day:
        return [{"tone": "neutral", "title": "Not enough history yet",
                 "text": "Upload at least one full Monday-to-Sunday week of orders to get weekly insights."}]

    ws, we = week_start.isoformat(), week_end.isoformat()
    week_rev = _sum_between(daily, week_start, week_end)
    prev_rev = _sum_between(daily, week_start - timedelta(days=7), week_end - timedelta(days=7))
    four = [_sum_between(daily, week_start - timedelta(days=7 * i), week_end - timedelta(days=7 * i))
            for i in range(1, 5)]
    four_avg = sum(four) / 4 if week_start - timedelta(days=28) >= first_day else None

    # 1. headline
    text = f"You took {money(week_rev)} last week"
    vs_prev = pct(week_rev, prev_rev) if week_start - timedelta(days=7) >= first_day else None
    if vs_prev is not None:
        text += f", {'up' if vs_prev >= 0 else 'down'} {abs(vs_prev):.0%} on the week before"
    if four_avg:
        d4 = pct(week_rev, four_avg)
        text += f" and {abs(d4):.0%} {'above' if d4 >= 0 else 'below'} your 4-week average"
    ly_start = week_start - timedelta(weeks=52)
    if ly_start >= first_day:
        ly = pct(week_rev, _sum_between(daily, ly_start, ly_start + timedelta(days=6)))
        if ly is not None:
            text += f". Compared with the same week last year you're {'up' if ly >= 0 else 'down'} {abs(ly):.0%}"
    tone = "neutral" if vs_prev is None else ("up" if vs_prev >= 0 else "down")
    notes.append({"tone": tone, "title": "Last week in one line", "text": text + "."})

    # 2. best seller
    rows = q("SELECT product, SUM(revenue) r, SUM(qty) FROM lines WHERE day BETWEEN ? AND ? "
             "GROUP BY product ORDER BY r DESC", (ws, we)).fetchall()
    if rows:
        p, r, u = rows[0]
        notes.append({"tone": "neutral", "title": "Best seller",
                      "text": f"{p} sold {u:,} units for {money(r)}, "
                              f"{r / (sum(x[1] for x in rows) or 1):.0%} of everything you sold last week."})

    # 3 & 4. movers: last week vs the weekly average of the 4 weeks before
    if four_avg:
        base_start = (week_start - timedelta(days=28)).isoformat()
        base_end = (week_start - timedelta(days=1)).isoformat()
        base = {p: r / 4 for p, r in q("SELECT product, SUM(revenue) FROM lines WHERE day BETWEEN ? AND ? "
                                        "GROUP BY product", (base_start, base_end))}
        cur = {p: r for p, r, _ in rows}
        floor = max(week_rev * 0.02, 50)
        moves = [(cur.get(p, 0) - base.get(p, 0), p) for p in set(cur) | set(base)
                 if max(cur.get(p, 0), base.get(p, 0)) >= floor]
        best = rows[0][0] if rows else None
        if best and base.get(best) and cur[best] / base[best] >= 1.15:
            notes[-1]["text"] = notes[-1]["text"][:-1] + f", up from about {money(base[best])} a week last month."
        gains = [m for m in moves if m[1] != best]
        if gains:
            gain, p = max(gains)
            if gain > 0 and (not base.get(p) or gain / base[p] >= 0.15):
                was = f"{money(base[p])} a week" if base.get(p) else "nothing"
                notes.append({"tone": "up", "title": "Picking up",
                              "text": f"{p} brought in {money(cur.get(p, 0))} last week, against {was} "
                                      f"over the previous month. Worth featuring it in your next email or post."})
        if moves:
            loss, p = min(moves)
            if loss < 0 and base.get(p) and -loss / base[p] >= 0.15:
                notes.append({"tone": "down", "title": "Slowing down",
                              "text": f"{p} fell to {money(cur.get(p, 0))} from about {money(base[p])} a week. "
                                      f"Check stock, price and whether it dropped off your homepage."})

    # 5. returning customers
    ret = q("SELECT COALESCE(SUM(revenue * is_returning),0), COALESCE(SUM(revenue),0) FROM orders "
            "WHERE day BETWEEN ? AND ?", (ws, we)).fetchone()
    base_start = max(first_day, week_start - timedelta(weeks=12)).isoformat()
    ret12 = q("SELECT COALESCE(SUM(revenue * is_returning),0), COALESCE(SUM(revenue),0) FROM orders "
              "WHERE day BETWEEN ? AND ?", (base_start, we)).fetchone()
    if ret[1]:
        share, share12 = ret[0] / ret[1], (ret12[0] / ret12[1] if ret12[1] else 0)
        notes.append({"tone": "up" if share >= share12 else "neutral", "title": "Loyal customers",
                      "text": f"{share:.0%} of last week's revenue came from people who had bought before "
                              f"(your 12-week average is {share12:.0%})."})

    # 6. best and quietest day
    days = [(daily.get(week_start + timedelta(days=i), 0.0), i) for i in range(7)]
    (hi, hi_i), (lo, lo_i) = max(days), min(days)
    wk = out["weekday"]["avg_revenue"]
    usual = WEEKDAYS[max(range(7), key=lambda i: wk[i])]
    notes.append({"tone": "neutral", "title": "Busiest day",
                  "text": f"{WEEKDAYS[hi_i]} was your strongest day ({money(hi)}) and {WEEKDAYS[lo_i]} "
                          f"the quietest ({money(lo)}). Over 12 weeks, {usual} is usually your best day, "
                          f"so that's the day to send emails and launch offers."})

    # 7. win-back
    wb = out["winback"]
    if wb["count"]:
        notes.append({"tone": "neutral", "title": "Customers to win back",
                      "text": f"{wb['count']:,} repeat customers haven't ordered in 3 to 12 months. Together "
                              f"they've spent {money(wb['lifetime_value'])} with you. A personal win-back "
                              f"email is the cheapest sale you'll make this month."})

    # 8. look-ahead from last year's seasonality
    months = _complete_months(daily, first_day, week_end)
    nxt = week_end.replace(day=1) + timedelta(days=32)
    nxt = nxt.replace(day=1)
    this_m, next_m = (week_end.year - 1, week_end.month), (nxt.year - 1, nxt.month)
    if this_m in months and next_m in months and months[this_m]:
        ratio = months[next_m] / months[this_m]
        if ratio >= 1.15:
            notes.append({"tone": "up", "title": "Coming up",
                          "text": f"Last year {MONTH_NAMES[nxt.month - 1]} sales were {ratio:.1f}x "
                                  f"{MONTH_NAMES[week_end.month - 1]}. Order stock and plan promotions now."})
        elif ratio <= 0.87:
            notes.append({"tone": "down", "title": "Coming up",
                          "text": f"Last year {MONTH_NAMES[nxt.month - 1]} was {1 - ratio:.0%} quieter than "
                                  f"{MONTH_NAMES[week_end.month - 1]}. A good month to run a win-back campaign."})
    return notes
