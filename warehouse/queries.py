"""The 20 OLAP queries from original-warehouse-project/queries_dw.sql, ported to SQLite.

Most run unchanged. Where MySQL syntax had no SQLite equivalent the change is
recorded in `note`, and the query still returns the same columns.
"""

Q = []


def query(qid, title, view, tags, question, sql, note=None, setup=None):
    Q.append({"id": qid, "title": title, "view": view, "tags": tags, "question": question,
              "sql": sql.strip(), "note": note, "setup": setup.strip() if setup else None})


TOP_PRODUCTS_2020 = """
WITH ranked_products AS (
    SELECT
        t.month_name, t.year, t.month,
        CASE WHEN t.is_weekend = 1 THEN 'Weekend' ELSE 'Weekday' END AS day_type,
        p.product_id, p.product_category,
        SUM(f.total_amount) AS total_revenue,{qty}
        ROW_NUMBER() OVER (
            PARTITION BY t.year, t.month, t.is_weekend
            ORDER BY SUM(f.total_amount) DESC
        ) AS revenue_rank
    FROM FACT_SALES f
    JOIN DIM_PRODUCT p ON f.product_key = p.product_key
    JOIN DIM_TIME t ON f.time_key = t.time_key
    WHERE t.year = 2020
    GROUP BY t.year, t.month, t.month_name, t.is_weekend, p.product_id, p.product_category
)
SELECT month_name, year, {month}day_type, product_id, product_category, total_revenue,{qty_out} revenue_rank
FROM ranked_products
WHERE revenue_rank <= 5
ORDER BY year, month, day_type, total_revenue DESC
"""

query("q1", "Top products on weekdays vs weekends, by month", "sales", ["Window function", "Drill-down"],
      "Which 5 products earned the most each month of 2020, split by weekdays and weekends?",
      TOP_PRODUCTS_2020.format(qty="", month="", qty_out=""))

query("q2", "Customer demographics by purchase amount and city", "customers", ["Dice"],
      "How much do customers spend by gender and age, broken down by city category?", """
SELECT
    c.gender, c.age, city.city_category,
    COUNT(DISTINCT f.customer_key) AS customer_count,
    SUM(f.total_amount) AS total_purchase_amount,
    AVG(f.total_amount) AS avg_purchase_amount,
    SUM(f.quantity) AS total_quantity
FROM FACT_SALES f
JOIN DIM_CUSTOMER c ON f.customer_key = c.customer_key
JOIN DIM_CITY city ON f.city_key = city.city_key
GROUP BY c.gender, c.age, city.city_category
ORDER BY total_purchase_amount DESC""")

query("q3", "Product category sales by occupation", "customers", ["Dice"],
      "What does each occupation group spend in each product category?", """
SELECT
    c.occupation, p.product_category,
    COUNT(DISTINCT f.order_id) AS order_count,
    SUM(f.quantity) AS total_quantity,
    SUM(f.total_amount) AS total_sales,
    AVG(f.total_amount) AS avg_sale_amount
FROM FACT_SALES f
JOIN DIM_CUSTOMER c ON f.customer_key = c.customer_key
JOIN DIM_PRODUCT p ON f.product_key = p.product_key
GROUP BY c.occupation, p.product_category
ORDER BY c.occupation, total_sales DESC""")

query("q4", "Purchases by gender and age, quarter by quarter", "sales", ["Drill-down", "Slice"],
      "How did purchases by gender and age group move across the quarters of 2020?", """
SELECT
    t.year, t.quarter, c.gender, c.age,
    SUM(f.total_amount) AS total_purchases,
    COUNT(DISTINCT f.order_id) AS order_count,
    AVG(f.total_amount) AS avg_purchase
FROM FACT_SALES f
JOIN DIM_CUSTOMER c ON f.customer_key = c.customer_key
JOIN DIM_TIME t ON f.time_key = t.time_key
WHERE t.year = 2020
GROUP BY t.year, t.quarter, c.gender, c.age
ORDER BY t.year, t.quarter, c.gender, c.age""")

query("q5", "Top occupations in each product category", "customers", ["Window function", "Ranking"],
      "Which 5 occupations drive the most sales within each product category?", """
WITH ranked_occupations AS (
    SELECT
        p.product_category, c.occupation,
        SUM(f.total_amount) AS total_sales,
        ROW_NUMBER() OVER (PARTITION BY p.product_category ORDER BY SUM(f.total_amount) DESC) AS occupation_rank
    FROM FACT_SALES f
    JOIN DIM_PRODUCT p ON f.product_key = p.product_key
    JOIN DIM_CUSTOMER c ON f.customer_key = c.customer_key
    GROUP BY p.product_category, c.occupation
)
SELECT product_category, occupation, total_sales, occupation_rank
FROM ranked_occupations
WHERE occupation_rank <= 5
ORDER BY product_category, total_sales DESC""")

query("q6", "City categories by marital status, last 6 months", "customers", ["Dice", "Drill-down"],
      "How did each city category perform by marital status over the last 6 months of 2020?", """
SELECT
    t.year, t.month, t.month_name, city.city_category,
    CASE WHEN c.marital_status = 0 THEN 'Single' ELSE 'Married' END AS marital_status,
    SUM(f.total_amount) AS total_purchase_amount,
    COUNT(DISTINCT f.customer_key) AS customer_count,
    COUNT(DISTINCT f.order_id) AS order_count
FROM FACT_SALES f
JOIN DIM_CITY city ON f.city_key = city.city_key
JOIN DIM_CUSTOMER c ON f.customer_key = c.customer_key
JOIN DIM_TIME t ON f.time_key = t.time_key
WHERE t.date_value >= '2020-06-30'
GROUP BY t.year, t.month, t.month_name, city.city_category, c.marital_status
ORDER BY t.year DESC, t.month DESC, city.city_category, c.marital_status""",
      note="MySQL's DATE_SUB('2020-12-31', INTERVAL 6 MONTH) is written as the date it evaluates to, "
           "'2020-06-30', so the window matches exactly (SQLite's date modifier would give 2020-07-01).")

query("q7", "Average purchase by years in city and gender", "customers", ["Roll-up"],
      "Does how long someone has lived in their city change what they spend?", """
SELECT
    c.stay_in_current_city_years, c.gender,
    COUNT(DISTINCT f.customer_key) AS customer_count,
    COUNT(DISTINCT f.order_id) AS order_count,
    AVG(f.total_amount) AS avg_purchase_amount,
    SUM(f.total_amount) AS total_purchase_amount,
    SUM(f.quantity) AS total_quantity
FROM FACT_SALES f
JOIN DIM_CUSTOMER c ON f.customer_key = c.customer_key
GROUP BY c.stay_in_current_city_years, c.gender
ORDER BY c.stay_in_current_city_years, c.gender""")

query("q8", "Top city categories for each product category", "customers", ["Window function", "Ranking"],
      "Which city categories bring in the most revenue for each product category?", """
WITH ranked_cities AS (
    SELECT
        p.product_category, city.city_category,
        SUM(f.total_amount) AS total_revenue,
        ROW_NUMBER() OVER (PARTITION BY p.product_category ORDER BY SUM(f.total_amount) DESC) AS city_rank
    FROM FACT_SALES f
    JOIN DIM_PRODUCT p ON f.product_key = p.product_key
    JOIN DIM_CITY city ON f.city_key = city.city_key
    GROUP BY p.product_category, city.city_category
)
SELECT product_category, city_category, total_revenue, city_rank
FROM ranked_cities
WHERE city_rank <= 5
ORDER BY product_category, total_revenue DESC""")

query("q9", "Month-over-month growth by product category", "sales", ["Self-join", "Trend"],
      "How fast did each product category grow month over month in 2020?", """
WITH monthly_sales AS (
    SELECT t.year, t.month, p.product_category, SUM(f.total_amount) AS monthly_revenue
    FROM FACT_SALES f
    JOIN DIM_PRODUCT p ON f.product_key = p.product_key
    JOIN DIM_TIME t ON f.time_key = t.time_key
    WHERE t.year = 2020
    GROUP BY t.year, t.month, p.product_category
)
SELECT
    ms1.year, ms1.month, ms1.product_category,
    ms1.monthly_revenue AS current_month_revenue,
    COALESCE(ms2.monthly_revenue, 0) AS previous_month_revenue,
    CASE WHEN COALESCE(ms2.monthly_revenue, 0) > 0
         THEN ((ms1.monthly_revenue - ms2.monthly_revenue) / ms2.monthly_revenue) * 100
         ELSE NULL END AS growth_percentage
FROM monthly_sales ms1
LEFT JOIN monthly_sales ms2
    ON ms1.product_category = ms2.product_category AND ms1.year = ms2.year AND ms1.month = ms2.month + 1
ORDER BY ms1.product_category, ms1.month""")

query("q10", "Weekend vs weekday sales by age group", "sales", ["Slice", "Dice"],
      "Do different age groups shop more on weekends or weekdays (2020)?", """
SELECT
    c.age,
    CASE WHEN t.is_weekend = 1 THEN 'Weekend' ELSE 'Weekday' END AS day_type,
    SUM(f.total_amount) AS total_sales,
    COUNT(DISTINCT f.order_id) AS order_count,
    AVG(f.total_amount) AS avg_sale_amount,
    COUNT(DISTINCT f.customer_key) AS customer_count
FROM FACT_SALES f
JOIN DIM_CUSTOMER c ON f.customer_key = c.customer_key
JOIN DIM_TIME t ON f.time_key = t.time_key
WHERE t.year = 2020
GROUP BY c.age, t.is_weekend
ORDER BY c.age, t.is_weekend""")

query("q11", "Top products on weekdays vs weekends, with units", "sales", ["Window function", "Drill-down"],
      "The same monthly top-5 ranking as Q1, adding the units sold for each product.",
      TOP_PRODUCTS_2020.format(qty="\n        SUM(f.quantity) AS total_quantity,", month="month, ",
                               qty_out=" total_quantity,").replace("revenue_rank", "product_rank"))

query("q12", "Quarterly store revenue growth, 2017", "stores", ["Self-join", "Trend"],
      "How fast did each store's revenue grow quarter over quarter in 2017?", """
WITH quarterly_store_sales AS (
    SELECT s.store_id, s.store_name, t.year, t.quarter, SUM(f.total_amount) AS quarterly_revenue
    FROM FACT_SALES f
    JOIN DIM_STORE s ON f.store_key = s.store_key
    JOIN DIM_TIME t ON f.time_key = t.time_key
    WHERE t.year = 2017
    GROUP BY s.store_id, s.store_name, t.year, t.quarter
)
SELECT
    qss1.store_id, qss1.store_name,
    qss1.quarter AS current_quarter,
    qss1.quarterly_revenue AS current_quarter_revenue,
    COALESCE(qss2.quarterly_revenue, 0) AS previous_quarter_revenue,
    CASE WHEN COALESCE(qss2.quarterly_revenue, 0) > 0
         THEN ((qss1.quarterly_revenue - qss2.quarterly_revenue) / qss2.quarterly_revenue) * 100
         ELSE NULL END AS growth_rate_percentage
FROM quarterly_store_sales qss1
LEFT JOIN quarterly_store_sales qss2 ON qss1.store_id = qss2.store_id AND qss1.quarter = qss2.quarter + 1
ORDER BY qss1.store_id, qss1.quarter""")

query("q13", "Supplier contribution by store and product", "stores", ["Drill-down"],
      "For each store, how much does each supplier contribute, product by product?", """
SELECT
    s.store_id, s.store_name, sup.supplier_id, sup.supplier_name, p.product_id, p.product_category,
    COUNT(DISTINCT f.order_id) AS order_count,
    SUM(f.quantity) AS total_quantity,
    SUM(f.total_amount) AS total_sales,
    AVG(f.total_amount) AS avg_sale_amount
FROM FACT_SALES f
JOIN DIM_STORE s ON f.store_key = s.store_key
JOIN DIM_SUPPLIER sup ON f.supplier_key = sup.supplier_key
JOIN DIM_PRODUCT p ON f.product_key = p.product_key
GROUP BY s.store_id, s.store_name, sup.supplier_id, sup.supplier_name, p.product_id, p.product_category
ORDER BY s.store_id, sup.supplier_id, total_sales DESC""")

query("q14", "Seasonal product sales", "products", ["Drill-down"],
      "How does each product sell across Spring, Summer, Fall and Winter?", """
SELECT
    p.product_id, p.product_category, t.season, t.year,
    COUNT(DISTINCT f.order_id) AS order_count,
    SUM(f.quantity) AS total_quantity,
    SUM(f.total_amount) AS total_sales,
    AVG(f.total_amount) AS avg_sale_amount
FROM FACT_SALES f
JOIN DIM_PRODUCT p ON f.product_key = p.product_key
JOIN DIM_TIME t ON f.time_key = t.time_key
GROUP BY p.product_id, p.product_category, t.season, t.year
ORDER BY p.product_category, t.year,
    CASE t.season WHEN 'Spring' THEN 1 WHEN 'Summer' THEN 2 WHEN 'Fall' THEN 3 WHEN 'Winter' THEN 4 END,
    total_sales DESC""")

query("q15", "Monthly revenue volatility by store and supplier", "stores", ["Self-join", "Trend"],
      "How much does revenue swing month to month for each store and supplier pair?", """
WITH monthly_store_supplier_sales AS (
    SELECT s.store_id, s.store_name, sup.supplier_id, sup.supplier_name, t.year, t.month,
           SUM(f.total_amount) AS monthly_revenue
    FROM FACT_SALES f
    JOIN DIM_STORE s ON f.store_key = s.store_key
    JOIN DIM_SUPPLIER sup ON f.supplier_key = sup.supplier_key
    JOIN DIM_TIME t ON f.time_key = t.time_key
    GROUP BY s.store_id, s.store_name, sup.supplier_id, sup.supplier_name, t.year, t.month
)
SELECT
    m1.store_id, m1.store_name, m1.supplier_id, m1.supplier_name, m1.year, m1.month,
    m1.monthly_revenue AS current_month_revenue,
    COALESCE(m2.monthly_revenue, 0) AS previous_month_revenue,
    CASE WHEN COALESCE(m2.monthly_revenue, 0) > 0
         THEN ABS(((m1.monthly_revenue - m2.monthly_revenue) / m2.monthly_revenue) * 100)
         ELSE NULL END AS volatility_percentage
FROM monthly_store_supplier_sales m1
LEFT JOIN monthly_store_supplier_sales m2
    ON m1.store_id = m2.store_id AND m1.supplier_id = m2.supplier_id
    AND m1.year = m2.year AND m1.month = m2.month + 1
ORDER BY m1.store_id, m1.supplier_id, m1.year, m1.month""",
      note="Table aliases shortened from msss1/msss2 to m1/m2 for readability; logic unchanged.")

query("q16", "Products bought together", "products", ["Self-join", "Ranking"],
      "Which 5 product pairs are most often bought in the same order?", """
WITH product_pairs AS (
    SELECT f1.order_id,
           p1.product_id AS product1_id, p1.product_category AS product1_category,
           p2.product_id AS product2_id, p2.product_category AS product2_category
    FROM FACT_SALES f1
    JOIN FACT_SALES f2 ON f1.order_id = f2.order_id AND f1.product_key < f2.product_key
    JOIN DIM_PRODUCT p1 ON f1.product_key = p1.product_key
    JOIN DIM_PRODUCT p2 ON f2.product_key = p2.product_key
),
co_purchase_counts AS (
    SELECT product1_id, product1_category, product2_id, product2_category,
           COUNT(DISTINCT order_id) AS co_purchase_count
    FROM product_pairs
    GROUP BY product1_id, product1_category, product2_id, product2_category
),
ranked_pairs AS (
    SELECT *, ROW_NUMBER() OVER (ORDER BY co_purchase_count DESC) AS affinity_rank
    FROM co_purchase_counts
)
SELECT product1_id, product1_category, product2_id, product2_category, co_purchase_count, affinity_rank
FROM ranked_pairs
WHERE affinity_rank <= 5
ORDER BY co_purchase_count DESC""",
      note="Unused product key columns dropped from the first CTE; the result is the same.")

ROLLUP_LEVELS = [
    ("s.store_name", "sup.supplier_name", "p.product_category", "t.year"),
    ("s.store_name", "sup.supplier_name", "p.product_category", None),
    ("s.store_name", "sup.supplier_name", None, None),
    ("s.store_name", None, None, None),
    (None, None, None, None),
]


def _rollup_sql():
    parts = []
    for store, sup, cat, year in ROLLUP_LEVELS:
        group = ", ".join(c for c in (store, sup, cat, year) if c)
        parts.append(f"""SELECT
    {store or 'NULL'} AS store_name, {sup or 'NULL'} AS supplier_name,
    {cat or 'NULL'} AS product_category, {year or 'NULL'} AS year,
    COUNT(DISTINCT f.order_id) AS order_count, SUM(f.quantity) AS total_quantity,
    SUM(f.total_amount) AS total_revenue
FROM FACT_SALES f
JOIN DIM_STORE s ON f.store_key = s.store_key
JOIN DIM_SUPPLIER sup ON f.supplier_key = sup.supplier_key
JOIN DIM_PRODUCT p ON f.product_key = p.product_key
JOIN DIM_TIME t ON f.time_key = t.time_key{chr(10) + 'GROUP BY ' + group if group else ''}""")
    union = "\nUNION ALL\n".join(parts)
    return f"""WITH rollup AS (
{union}
)
SELECT
    COALESCE(store_name, 'ALL STORES') AS store_name,
    COALESCE(supplier_name, 'ALL SUPPLIERS') AS supplier_name,
    COALESCE(product_category, 'ALL PRODUCTS') AS product_category,
    year, order_count, total_quantity, total_revenue
FROM rollup
ORDER BY store_name IS NULL, store_name, supplier_name IS NULL, supplier_name,
         product_category IS NULL, product_category, year IS NULL, year"""


query("q17", "Yearly revenue by store, supplier and product (ROLLUP)", "stores", ["Roll-up"],
      "What is yearly revenue at every level, from product up to each store and the grand total?",
      _rollup_sql(),
      note="SQLite has no GROUP BY ... WITH ROLLUP, so each subtotal level is a UNION ALL branch. "
           "The rows and the 'ALL ...' labels match MySQL's ROLLUP output.")

query("q18", "First half vs second half of 2020, per product", "products", ["Drill-down", "Slice"],
      "How did each product's revenue and volume compare between H1 and H2 of 2020?", """
SELECT
    p.product_id, p.product_category, t.year,
    CASE WHEN t.month <= 6 THEN 'H1 (Jan-Jun)' ELSE 'H2 (Jul-Dec)' END AS half_year,
    COUNT(DISTINCT f.order_id) AS order_count,
    SUM(f.quantity) AS total_quantity,
    SUM(f.total_amount) AS total_revenue,
    AVG(f.total_amount) AS avg_revenue
FROM FACT_SALES f
JOIN DIM_PRODUCT p ON f.product_key = p.product_key
JOIN DIM_TIME t ON f.time_key = t.time_key
WHERE t.year = 2020
GROUP BY p.product_id, p.product_category, t.year,
    CASE WHEN t.month <= 6 THEN 'H1 (Jan-Jun)' ELSE 'H2 (Jul-Dec)' END
ORDER BY p.product_category, p.product_id, half_year""")

query("q19", "Revenue spikes and outlier days", "products", ["Outlier detection"],
      "On which days did a product sell more than twice (or under half) its daily average?", """
WITH daily_product_sales AS (
    SELECT p.product_id, p.product_category, t.date_value,
           SUM(f.total_amount) AS daily_revenue, SUM(f.quantity) AS daily_quantity
    FROM FACT_SALES f
    JOIN DIM_PRODUCT p ON f.product_key = p.product_key
    JOIN DIM_TIME t ON f.time_key = t.time_key
    GROUP BY p.product_id, p.product_category, t.date_value
),
product_avg_sales AS (
    SELECT product_id, product_category,
           AVG(daily_revenue) AS avg_daily_revenue,
           SQRT(AVG(daily_revenue * daily_revenue) - AVG(daily_revenue) * AVG(daily_revenue)) AS stddev_daily_revenue
    FROM daily_product_sales
    GROUP BY product_id, product_category
)
SELECT
    dps.product_id, dps.product_category, dps.date_value, dps.daily_revenue,
    pas.avg_daily_revenue, pas.stddev_daily_revenue,
    CASE WHEN dps.daily_revenue > (pas.avg_daily_revenue * 2) THEN 'OUTLIER - High Spike'
         WHEN dps.daily_revenue < (pas.avg_daily_revenue * 0.5) THEN 'OUTLIER - Low Spike'
         ELSE 'Normal' END AS outlier_flag,
    ((dps.daily_revenue - pas.avg_daily_revenue) / pas.avg_daily_revenue) * 100 AS deviation_percentage
FROM daily_product_sales dps
JOIN product_avg_sales pas ON dps.product_id = pas.product_id
WHERE dps.daily_revenue > (pas.avg_daily_revenue * 2) OR dps.daily_revenue < (pas.avg_daily_revenue * 0.5)
ORDER BY dps.product_category, deviation_percentage DESC""",
      note="SQLite has no STDDEV(); it is computed as the population standard deviation "
           "sqrt(avg(x²) − avg(x)²), which is what MySQL's STDDEV returns.")

query("q20", "STORE_QUARTERLY_SALES view", "stores", ["View", "Roll-up"],
      "A reusable view of quarterly sales per store, then queried for every store and quarter.", """
SELECT * FROM STORE_QUARTERLY_SALES
ORDER BY store_name, year, quarter""",
      setup="""
CREATE VIEW STORE_QUARTERLY_SALES AS
SELECT
    s.store_id, s.store_name, t.year, t.quarter,
    COUNT(DISTINCT f.order_id) AS order_count,
    COUNT(DISTINCT f.customer_key) AS customer_count,
    SUM(f.quantity) AS total_quantity,
    SUM(f.total_amount) AS total_revenue,
    AVG(f.total_amount) AS avg_order_value
FROM FACT_SALES f
JOIN DIM_STORE s ON f.store_key = s.store_key
JOIN DIM_TIME t ON f.time_key = t.time_key
GROUP BY s.store_id, s.store_name, t.year, t.quarter
ORDER BY s.store_name, t.year, t.quarter""",
      note="CREATE OR REPLACE VIEW becomes CREATE VIEW (SQLite has no OR REPLACE for views).")

BY_ID = {q["id"]: q for q in Q}


def run(db):
    """Run every query; returns {id: {"columns": [...], "rows": [...], "ms": float}}."""
    import math
    import time
    db.create_function("SQRT", 1, lambda x: math.sqrt(x) if x is not None and x >= 0 else None)
    out = {}
    for q in Q:
        if q["setup"]:
            db.execute("DROP VIEW IF EXISTS STORE_QUARTERLY_SALES")
            db.execute(q["setup"])
        start = time.perf_counter()
        cur = db.execute(q["sql"])
        rows = cur.fetchall()
        out[q["id"]] = {"columns": [c[0] for c in cur.description], "rows": rows,
                        "ms": round((time.perf_counter() - start) * 1000, 1)}
    return out
