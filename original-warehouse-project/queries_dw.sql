-- =====================================================
-- Data Warehouse project  -  Queries
-- =====================================================
-- Hassaan Ullah Khan
-- 21i 1695
-- =====================================================

USE walmart_dw;

-- =====================================================
-- Q1. Top Revenue-Generating Products on Weekdays and Weekends with Monthly Drill-Down
-- =====================================================
-- Identifies the top 5 products by revenue, split by weekdays and weekends, 
-- with monthly breakdowns for a year.
-- =====================================================

WITH ranked_products AS (
    SELECT 
        t.month_name,
        t.year,
        t.month,
        CASE WHEN t.is_weekend = 1 THEN 'Weekend' ELSE 'Weekday' END AS day_type,
        p.product_id,
        p.product_category,
        SUM(f.total_amount) AS total_revenue,
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
SELECT 
    month_name,
    year,
    day_type,
    product_id,
    product_category,
    total_revenue,
    revenue_rank
FROM ranked_products
WHERE revenue_rank <= 5
ORDER BY year, month, day_type, total_revenue DESC;

-- =====================================================
-- Q2. Customer Demographics by Purchase Amount with City Category Breakdown
-- =====================================================
-- Analyzes total purchase amounts by gender and age, detailed by city category.
-- =====================================================

SELECT 
    c.gender,
    c.age,
    city.city_category,
    COUNT(DISTINCT f.customer_key) AS customer_count,
    SUM(f.total_amount) AS total_purchase_amount,
    AVG(f.total_amount) AS avg_purchase_amount,
    SUM(f.quantity) AS total_quantity
FROM FACT_SALES f
JOIN DIM_CUSTOMER c ON f.customer_key = c.customer_key
JOIN DIM_CITY city ON f.city_key = city.city_key
GROUP BY c.gender, c.age, city.city_category
ORDER BY total_purchase_amount DESC;

-- =====================================================
-- Q3. Product Category Sales by Occupation
-- =====================================================
-- Examines total sales for each product category based on customer occupation.
-- =====================================================

SELECT 
    c.occupation,
    p.product_category,
    COUNT(DISTINCT f.order_id) AS order_count,
    SUM(f.quantity) AS total_quantity,
    SUM(f.total_amount) AS total_sales,
    AVG(f.total_amount) AS avg_sale_amount
FROM FACT_SALES f
JOIN DIM_CUSTOMER c ON f.customer_key = c.customer_key
JOIN DIM_PRODUCT p ON f.product_key = p.product_key
GROUP BY c.occupation, p.product_category
ORDER BY c.occupation, total_sales DESC;

-- =====================================================
-- Q4. Total Purchases by Gender and Age Group with Quarterly Trend
-- =====================================================
-- Tracks purchase amounts by gender and age across quarterly periods for the current year.
-- =====================================================

SELECT 
    t.year,
    t.quarter,
    c.gender,
    c.age,
    SUM(f.total_amount) AS total_purchases,
    COUNT(DISTINCT f.order_id) AS order_count,
    AVG(f.total_amount) AS avg_purchase
FROM FACT_SALES f
JOIN DIM_CUSTOMER c ON f.customer_key = c.customer_key
JOIN DIM_TIME t ON f.time_key = t.time_key
WHERE t.year = 2020
GROUP BY t.year, t.quarter, c.gender, c.age
ORDER BY t.year, t.quarter, c.gender, c.age;

-- =====================================================
-- Q5. Top Occupations by Product Category Sales
-- =====================================================
-- Highlights the top 5 occupations driving sales within each product category.
-- =====================================================

WITH ranked_occupations AS (
    SELECT 
        p.product_category,
        c.occupation,
        SUM(f.total_amount) AS total_sales,
        ROW_NUMBER() OVER (
            PARTITION BY p.product_category 
            ORDER BY SUM(f.total_amount) DESC
        ) AS occupation_rank
    FROM FACT_SALES f
    JOIN DIM_PRODUCT p ON f.product_key = p.product_key
    JOIN DIM_CUSTOMER c ON f.customer_key = c.customer_key
    GROUP BY p.product_category, c.occupation
)
SELECT 
    product_category,
    occupation,
    total_sales,
    occupation_rank
FROM ranked_occupations
WHERE occupation_rank <= 5
ORDER BY product_category, total_sales DESC;

-- =====================================================
-- Q6. City Category Performance by Marital Status with Monthly Breakdown
-- =====================================================
-- Assesses purchase amounts by city category and marital status over the past 6 months.
-- =====================================================

SELECT 
    t.year,
    t.month,
    t.month_name,
    city.city_category,
    CASE WHEN c.marital_status = 0 THEN 'Single' ELSE 'Married' END AS marital_status,
    SUM(f.total_amount) AS total_purchase_amount,
    COUNT(DISTINCT f.customer_key) AS customer_count,
    COUNT(DISTINCT f.order_id) AS order_count
FROM FACT_SALES f
JOIN DIM_CITY city ON f.city_key = city.city_key
JOIN DIM_CUSTOMER c ON f.customer_key = c.customer_key
JOIN DIM_TIME t ON f.time_key = t.time_key
WHERE t.date_value >= DATE_SUB('2020-12-31', INTERVAL 6 MONTH)
GROUP BY t.year, t.month, t.month_name, city.city_category, c.marital_status
ORDER BY t.year DESC, t.month DESC, city.city_category, c.marital_status;

-- =====================================================
-- Q7. Average Purchase Amount by Stay Duration and Gender
-- =====================================================
-- Calculates the average purchase amount based on years stayed in the city and gender.
-- =====================================================

SELECT 
    c.stay_in_current_city_years,
    c.gender,
    COUNT(DISTINCT f.customer_key) AS customer_count,
    COUNT(DISTINCT f.order_id) AS order_count,
    AVG(f.total_amount) AS avg_purchase_amount,
    SUM(f.total_amount) AS total_purchase_amount,
    SUM(f.quantity) AS total_quantity
FROM FACT_SALES f
JOIN DIM_CUSTOMER c ON f.customer_key = c.customer_key
GROUP BY c.stay_in_current_city_years, c.gender
ORDER BY c.stay_in_current_city_years, c.gender;

-- =====================================================
-- Q8. Top 5 Revenue-Generating Cities by Product Category
-- =====================================================
-- Ranks the top 5 city categories by revenue, grouped by product category.
-- =====================================================

WITH ranked_cities AS (
    SELECT 
        p.product_category,
        city.city_category,
        SUM(f.total_amount) AS total_revenue,
        ROW_NUMBER() OVER (
            PARTITION BY p.product_category 
            ORDER BY SUM(f.total_amount) DESC
        ) AS city_rank
    FROM FACT_SALES f
    JOIN DIM_PRODUCT p ON f.product_key = p.product_key
    JOIN DIM_CITY city ON f.city_key = city.city_key
    GROUP BY p.product_category, city.city_category
)
SELECT 
    product_category,
    city_category,
    total_revenue,
    city_rank
FROM ranked_cities
WHERE city_rank <= 5
ORDER BY product_category, total_revenue DESC;

-- =====================================================
-- Q9. Monthly Sales Growth by Product Category
-- =====================================================
-- Measures month-over-month sales growth percentage for each product category in the current year.
-- =====================================================

WITH monthly_sales AS (
    SELECT 
        t.year,
        t.month,
        p.product_category,
        SUM(f.total_amount) AS monthly_revenue
    FROM FACT_SALES f
    JOIN DIM_PRODUCT p ON f.product_key = p.product_key
    JOIN DIM_TIME t ON f.time_key = t.time_key
    WHERE t.year = 2020
    GROUP BY t.year, t.month, p.product_category
)
SELECT 
    ms1.year,
    ms1.month,
    ms1.product_category,
    ms1.monthly_revenue AS current_month_revenue,
    COALESCE(ms2.monthly_revenue, 0) AS previous_month_revenue,
    CASE 
        WHEN COALESCE(ms2.monthly_revenue, 0) > 0 
        THEN ((ms1.monthly_revenue - ms2.monthly_revenue) / ms2.monthly_revenue) * 100
        ELSE NULL
    END AS growth_percentage
FROM monthly_sales ms1
LEFT JOIN monthly_sales ms2 
    ON ms1.product_category = ms2.product_category 
    AND ms1.year = ms2.year 
    AND ms1.month = ms2.month + 1
ORDER BY ms1.product_category, ms1.month;

-- =====================================================
-- Q10. Weekend vs. Weekday Sales by Age Group
-- =====================================================
-- Compares total sales by age group for weekends versus weekdays in the current year.
-- =====================================================

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
ORDER BY c.age, t.is_weekend;

-- =====================================================
-- Q11. Top Revenue-Generating Products on Weekdays and Weekends with Monthly Drill-Down
-- =====================================================
-- Find the top 5 products that generated the highest revenue, separated by weekday and weekend sales,
-- with results grouped by month for a specified year.
-- =====================================================

WITH ranked_products_q11 AS (
    SELECT 
        t.year,
        t.month,
        t.month_name,
        CASE WHEN t.is_weekend = 1 THEN 'Weekend' ELSE 'Weekday' END AS day_type,
        p.product_id,
        p.product_category,
        SUM(f.total_amount) AS total_revenue,
        SUM(f.quantity) AS total_quantity,
        ROW_NUMBER() OVER (
            PARTITION BY t.year, t.month, t.is_weekend 
            ORDER BY SUM(f.total_amount) DESC
        ) AS product_rank
    FROM FACT_SALES f
    JOIN DIM_PRODUCT p ON f.product_key = p.product_key
    JOIN DIM_TIME t ON f.time_key = t.time_key
    WHERE t.year = 2020
    GROUP BY t.year, t.month, t.month_name, t.is_weekend, p.product_id, p.product_category
)
SELECT 
    year,
    month,
    month_name,
    day_type,
    product_id,
    product_category,
    total_revenue,
    total_quantity,
    product_rank
FROM ranked_products_q11
WHERE product_rank <= 5
ORDER BY year, month, day_type, total_revenue DESC;

-- =====================================================
-- Q12. Trend Analysis of Store Revenue Growth Rate Quarterly for 2017
-- =====================================================
-- Calculate the revenue growth rate for each store on a quarterly basis for 2017.
-- =====================================================

WITH quarterly_store_sales AS (
    SELECT 
        s.store_id,
        s.store_name,
        t.year,
        t.quarter,
        SUM(f.total_amount) AS quarterly_revenue
    FROM FACT_SALES f
    JOIN DIM_STORE s ON f.store_key = s.store_key
    JOIN DIM_TIME t ON f.time_key = t.time_key
    WHERE t.year = 2017
    GROUP BY s.store_id, s.store_name, t.year, t.quarter
)
SELECT 
    qss1.store_id,
    qss1.store_name,
    qss1.quarter AS current_quarter,
    qss1.quarterly_revenue AS current_quarter_revenue,
    COALESCE(qss2.quarterly_revenue, 0) AS previous_quarter_revenue,
    CASE 
        WHEN COALESCE(qss2.quarterly_revenue, 0) > 0 
        THEN ((qss1.quarterly_revenue - qss2.quarterly_revenue) / qss2.quarterly_revenue) * 100
        ELSE NULL
    END AS growth_rate_percentage
FROM quarterly_store_sales qss1
LEFT JOIN quarterly_store_sales qss2 
    ON qss1.store_id = qss2.store_id 
    AND qss1.quarter = qss2.quarter + 1
ORDER BY qss1.store_id, qss1.quarter;

-- =====================================================
-- Q13. Detailed Supplier Sales Contribution by Store and Product Name
-- =====================================================
-- For each store, show the total sales contribution of each supplier broken down by product name.
-- The output should group results by store, then supplier, and then product name under each supplier.
-- =====================================================

SELECT 
    s.store_id,
    s.store_name,
    sup.supplier_id,
    sup.supplier_name,
    p.product_id,
    p.product_category,
    COUNT(DISTINCT f.order_id) AS order_count,
    SUM(f.quantity) AS total_quantity,
    SUM(f.total_amount) AS total_sales,
    AVG(f.total_amount) AS avg_sale_amount
FROM FACT_SALES f
JOIN DIM_STORE s ON f.store_key = s.store_key
JOIN DIM_SUPPLIER sup ON f.supplier_key = sup.supplier_key
JOIN DIM_PRODUCT p ON f.product_key = p.product_key
GROUP BY s.store_id, s.store_name, sup.supplier_id, sup.supplier_name, p.product_id, p.product_category
ORDER BY s.store_id, sup.supplier_id, total_sales DESC;

-- =====================================================
-- Q14. Seasonal Analysis of Product Sales Using Dynamic Drill-Down
-- =====================================================
-- Present total sales for each product, drilled down by seasonal periods (Spring, Summer, Fall, Winter).
-- This can help understand product performance across seasonal periods.
-- =====================================================

SELECT 
    p.product_id,
    p.product_category,
    t.season,
    t.year,
    COUNT(DISTINCT f.order_id) AS order_count,
    SUM(f.quantity) AS total_quantity,
    SUM(f.total_amount) AS total_sales,
    AVG(f.total_amount) AS avg_sale_amount
FROM FACT_SALES f
JOIN DIM_PRODUCT p ON f.product_key = p.product_key
JOIN DIM_TIME t ON f.time_key = t.time_key
GROUP BY p.product_id, p.product_category, t.season, t.year
ORDER BY p.product_category, t.year, 
    CASE t.season 
        WHEN 'Spring' THEN 1 
        WHEN 'Summer' THEN 2 
        WHEN 'Fall' THEN 3 
        WHEN 'Winter' THEN 4 
    END,
    total_sales DESC;

-- =====================================================
-- Q15. Store-Wise and Supplier-Wise Monthly Revenue Volatility
-- =====================================================
-- Calculate the month-to-month revenue volatility for each store and supplier pair.
-- Volatility can be defined as the percentage change in revenue from one month to the next.
-- =====================================================

WITH monthly_store_supplier_sales AS (
    SELECT 
        s.store_id,
        s.store_name,
        sup.supplier_id,
        sup.supplier_name,
        t.year,
        t.month,
        SUM(f.total_amount) AS monthly_revenue
    FROM FACT_SALES f
    JOIN DIM_STORE s ON f.store_key = s.store_key
    JOIN DIM_SUPPLIER sup ON f.supplier_key = sup.supplier_key
    JOIN DIM_TIME t ON f.time_key = t.time_key
    GROUP BY s.store_id, s.store_name, sup.supplier_id, sup.supplier_name, t.year, t.month
)
SELECT 
    msss1.store_id,
    msss1.store_name,
    msss1.supplier_id,
    msss1.supplier_name,
    msss1.year,
    msss1.month,
    msss1.monthly_revenue AS current_month_revenue,
    COALESCE(msss2.monthly_revenue, 0) AS previous_month_revenue,
    CASE 
        WHEN COALESCE(msss2.monthly_revenue, 0) > 0 
        THEN ABS(((msss1.monthly_revenue - msss2.monthly_revenue) / msss2.monthly_revenue) * 100)
        ELSE NULL
    END AS volatility_percentage
FROM monthly_store_supplier_sales msss1
LEFT JOIN monthly_store_supplier_sales msss2 
    ON msss1.store_id = msss2.store_id 
    AND msss1.supplier_id = msss2.supplier_id
    AND msss1.year = msss2.year 
    AND msss1.month = msss2.month + 1
ORDER BY msss1.store_id, msss1.supplier_id, msss1.year, msss1.month;

-- =====================================================
-- Q16. Top 5 Products Purchased Together Across Multiple Orders (Product Affinity Analysis)
-- =====================================================
-- Identify the top 5 products frequently bought together within a set of orders
-- (i.e., multiple products purchased in the same transaction).
-- =====================================================

WITH product_pairs AS (
    SELECT 
        f1.order_id,
        f1.product_key AS product1_key,
        p1.product_id AS product1_id,
        p1.product_category AS product1_category,
        f2.product_key AS product2_key,
        p2.product_id AS product2_id,
        p2.product_category AS product2_category
    FROM FACT_SALES f1
    JOIN FACT_SALES f2 ON f1.order_id = f2.order_id AND f1.product_key < f2.product_key
    JOIN DIM_PRODUCT p1 ON f1.product_key = p1.product_key
    JOIN DIM_PRODUCT p2 ON f2.product_key = p2.product_key
),
co_purchase_counts AS (
    SELECT 
        product1_id,
        product1_category,
        product2_id,
        product2_category,
        COUNT(DISTINCT order_id) AS co_purchase_count
    FROM product_pairs
    GROUP BY product1_id, product1_category, product2_id, product2_category
),
ranked_pairs AS (
    SELECT 
        product1_id,
        product1_category,
        product2_id,
        product2_category,
        co_purchase_count,
        ROW_NUMBER() OVER (ORDER BY co_purchase_count DESC) AS affinity_rank
    FROM co_purchase_counts
)
SELECT 
    product1_id,
    product1_category,
    product2_id,
    product2_category,
    co_purchase_count,
    affinity_rank
FROM ranked_pairs
WHERE affinity_rank <= 5
ORDER BY co_purchase_count DESC;

-- =====================================================
-- Q17. Yearly Revenue Trends by Store, Supplier, and Product with ROLLUP
-- =====================================================
-- Use the ROLLUP operation to aggregate yearly revenue data by store, supplier, and product,
-- enabling a comprehensive overview from individual product-level details up to total revenue per store.
-- =====================================================

SELECT 
    COALESCE(s.store_name, 'ALL STORES') AS store_name,
    COALESCE(sup.supplier_name, 'ALL SUPPLIERS') AS supplier_name,
    COALESCE(p.product_category, 'ALL PRODUCTS') AS product_category,
    t.year,
    COUNT(DISTINCT f.order_id) AS order_count,
    SUM(f.quantity) AS total_quantity,
    SUM(f.total_amount) AS total_revenue
FROM FACT_SALES f
JOIN DIM_STORE s ON f.store_key = s.store_key
JOIN DIM_SUPPLIER sup ON f.supplier_key = sup.supplier_key
JOIN DIM_PRODUCT p ON f.product_key = p.product_key
JOIN DIM_TIME t ON f.time_key = t.time_key
GROUP BY s.store_name, sup.supplier_name, p.product_category, t.year WITH ROLLUP
ORDER BY s.store_name, sup.supplier_name, p.product_category, t.year;

-- =====================================================
-- Q18. Revenue and Volume-Based Sales Analysis for Each Product for H1 and H2
-- =====================================================
-- For each product, calculate the total revenue and quantity sold in the first and second halves of the year,
-- along with yearly totals.
-- =====================================================

SELECT 
    p.product_id,
    p.product_category,
    t.year,
    CASE 
        WHEN t.month <= 6 THEN 'H1 (Jan-Jun)'
        ELSE 'H2 (Jul-Dec)'
    END AS half_year,
    COUNT(DISTINCT f.order_id) AS order_count,
    SUM(f.quantity) AS total_quantity,
    SUM(f.total_amount) AS total_revenue,
    AVG(f.total_amount) AS avg_revenue
FROM FACT_SALES f
JOIN DIM_PRODUCT p ON f.product_key = p.product_key
JOIN DIM_TIME t ON f.time_key = t.time_key
WHERE t.year = 2020
GROUP BY p.product_id, p.product_category, t.year,
    CASE 
        WHEN t.month <= 6 THEN 'H1 (Jan-Jun)'
        ELSE 'H2 (Jul-Dec)'
    END
ORDER BY p.product_category, p.product_id, half_year;

-- =====================================================
-- Q19. Identify High Revenue Spikes in Product Sales and Highlight Outliers
-- =====================================================
-- Calculate daily average sales for each product and flag days where the sales exceed 
-- twice the daily average by product as potential outliers or spikes.
-- =====================================================

WITH daily_product_sales AS (
    SELECT 
        p.product_id,
        p.product_category,
        t.date_value,
        SUM(f.total_amount) AS daily_revenue,
        SUM(f.quantity) AS daily_quantity
    FROM FACT_SALES f
    JOIN DIM_PRODUCT p ON f.product_key = p.product_key
    JOIN DIM_TIME t ON f.time_key = t.time_key
    GROUP BY p.product_id, p.product_category, t.date_value
),
product_avg_sales AS (
    SELECT 
        product_id,
        product_category,
        AVG(daily_revenue) AS avg_daily_revenue,
        STDDEV(daily_revenue) AS stddev_daily_revenue
    FROM daily_product_sales
    GROUP BY product_id, product_category
)
SELECT 
    dps.product_id,
    dps.product_category,
    dps.date_value,
    dps.daily_revenue,
    pas.avg_daily_revenue,
    pas.stddev_daily_revenue,
    CASE 
        WHEN dps.daily_revenue > (pas.avg_daily_revenue * 2) THEN 'OUTLIER - High Spike'
        WHEN dps.daily_revenue < (pas.avg_daily_revenue * 0.5) THEN 'OUTLIER - Low Spike'
        ELSE 'Normal'
    END AS outlier_flag,
    ((dps.daily_revenue - pas.avg_daily_revenue) / pas.avg_daily_revenue) * 100 AS deviation_percentage
FROM daily_product_sales dps
JOIN product_avg_sales pas ON dps.product_id = pas.product_id
WHERE dps.daily_revenue > (pas.avg_daily_revenue * 2) OR dps.daily_revenue < (pas.avg_daily_revenue * 0.5)
ORDER BY dps.product_category, deviation_percentage DESC;

-- =====================================================
-- Q20. Create a View STORE_QUARTERLY_SALES for Optimized Sales Analysis
-- =====================================================
-- Create a view named STORE_QUARTERLY_SALES that aggregates total quarterly sales by store,
-- ordered by store name. This view allows quick retrieval of store-specific trends across quarters.
-- =====================================================

CREATE OR REPLACE VIEW STORE_QUARTERLY_SALES AS
SELECT 
    s.store_id,
    s.store_name,
    t.year,
    t.quarter,
    COUNT(DISTINCT f.order_id) AS order_count,
    COUNT(DISTINCT f.customer_key) AS customer_count,
    SUM(f.quantity) AS total_quantity,
    SUM(f.total_amount) AS total_revenue,
    AVG(f.total_amount) AS avg_order_value
FROM FACT_SALES f
JOIN DIM_STORE s ON f.store_key = s.store_key
JOIN DIM_TIME t ON f.time_key = t.time_key
GROUP BY s.store_id, s.store_name, t.year, t.quarter
ORDER BY s.store_name, t.year, t.quarter;

-- Query the view
SELECT * FROM STORE_QUARTERLY_SALES
ORDER BY store_name, year, quarter;

-- =====================================================
-- END OF OLAP QUERIES
-- =====================================================

