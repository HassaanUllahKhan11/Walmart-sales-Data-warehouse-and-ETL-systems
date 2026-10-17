================================================================================
Data Warehouse  Project
================================================================================
Hassaan Ullah Khan
21i 1695

================================================================================
PROJECT STRUCTURE
================================================================================

i211695_HassaanUllahKhan_DSC_Project/
│
├── create_dw.sql              
├── hybrid_join/               
│   ├── main.py               
│   ├── stream_producer.py    
│   ├── hybrid_join.py        
│   ├── data_loader.py        
│   └── utils/
│       └── structures.py     
│
├── queries_dw.sql            
├── report/
│   └── i211695_HassaanUllahKhan_DS-C_report.pdf   
├── README.txt                
└── data/                     
    ├── customer_master_data.csv
    ├── product_master_data.csv
    └── transactional_data.csv

================================================================================
PREREQUISITES
================================================================================

1. Python 3.7 or higher
2. MySQL Server 5.7 or higher (or MySQL 8.0)
3. MySQL Connector/Python library
4. python-docx library (for report generation)

================================================================================
STEP 1: SETUP MYSQL DATABASE
================================================================================

1. Install MySQL Server if not already installed
   - Download from: https://dev.mysql.com/downloads/mysql/
   - Follow installation instructions for your operating system

2. Start MySQL service
   - Windows: MySQL service should start automatically
   - Linux/Mac: sudo systemctl start mysql (or mysql.service)

3. Create a MySQL user (optional, can use root)
   - Login to MySQL: mysql -u root -p
   - Create user: CREATE USER 'dw_user'@'localhost' IDENTIFIED BY 'your_password';
   - Grant privileges: GRANT ALL PRIVILEGES ON *.* TO 'dw_user'@'localhost';
   - Flush privileges: FLUSH PRIVILEGES;

================================================================================
STEP 2: CREATE DATA WAREHOUSE SCHEMA
================================================================================

1. Open MySQL command line or MySQL Workbench

2. Run the create_dw.sql script:
   
   Method 1 (Command Line):
   ------------------------
   mysql -u root -p < create_dw.sql
   
   OR
   
   mysql -u dw_user -p < create_dw.sql
   
   Method 2 (MySQL Workbench):
   ---------------------------
   - Open MySQL Workbench
   - File -> Open SQL Script -> Select create_dw.sql
   - Click Execute (lightning bolt icon)
   
   Method 3 (Interactive):
   -----------------------
   mysql -u root -p
   source create_dw.sql;

3. Verify schema creation:
   mysql -u root -p
   USE walmart_dw;
   SHOW TABLES;
   
   You should see:
   - DIM_CUSTOMER
   - DIM_PRODUCT
   - DIM_TIME
   - DIM_CITY
   - DIM_STORE
   - DIM_SUPPLIER
   - FACT_SALES

================================================================================
STEP 3: SETUP PYTHON ENVIRONMENT
================================================================================

1. Create a virtual environment (recommended):
   
   Windows:
   --------
   python -m venv venv
   venv\Scripts\activate
   
   Linux/Mac:
   ----------
   python3 -m venv venv
   source venv/bin/activate

2. Install required Python packages:
   
   pip install mysql-connector-python python-docx
   
   OR
   
   pip install -r requirements.txt
   
   (If requirements.txt exists)

3. Verify installation:
   python -c "import mysql.connector; import docx; 

================================================================================
STEP 4: VERIFY DATA FILES
================================================================================

Ensure the following CSV files are present in the 'data' folder:

1. data/customer_master_data.csv
2. data/product_master_data.csv
3. data/transactional_data.csv


================================================================================
STEP 5: RUN HYBRIDJOIN ETL PROCESS
================================================================================

1. Navigate to the project directory:
   cd Walmart_DW_Project

2. Run the main script:
   python hybrid_join/main.py
   
   OR
   
   cd hybrid_join
   python main.py

3. When prompted, enter your MySQL credentials:
   - Host: [Enter host, default: localhost]
   - Username: [Enter MySQL username]
   - Password: [Enter MySQL password]
   - Database: [Enter database name, default: walmart_dw]

4. The process will:
   a. Connect to MySQL database
   b. Load dimension tables (DIM_TIME, DIM_CITY, DIM_CUSTOMER, DIM_PRODUCT, 
      DIM_STORE, DIM_SUPPLIER)
   c. Start stream producer thread (reads transactional_data.csv)
   d. Execute HYBRIDJOIN algorithm
   e. Load fact table (FACT_SALES) with joined data

5. Monitor progress:
   - The script will display progress messages
   - You'll see statistics like:
     * Rows read by stream producer
     * Records processed by HYBRIDJOIN
     * Successfully joined records

6. Wait for completion:
   - Processing time depends on data size
   - For 550,000+ transactions, expect 10-30 minutes
   - The script will display final statistics when complete

================================================================================
STEP 6: VERIFY DATA LOADING
================================================================================

1. Connect to MySQL:
   mysql -u root -p
   USE walmart_dw;

2. Check dimension table counts:
   SELECT 'DIM_CUSTOMER' AS table_name, COUNT(*) AS count FROM DIM_CUSTOMER
   UNION ALL
   SELECT 'DIM_PRODUCT', COUNT(*) FROM DIM_PRODUCT
   UNION ALL
   SELECT 'DIM_TIME', COUNT(*) FROM DIM_TIME
   UNION ALL
   SELECT 'DIM_CITY', COUNT(*) FROM DIM_CITY
   UNION ALL
   SELECT 'DIM_STORE', COUNT(*) FROM DIM_STORE
   UNION ALL
   SELECT 'DIM_SUPPLIER', COUNT(*) FROM DIM_SUPPLIER;

3. Check fact table count:
   SELECT COUNT(*) AS total_sales_records FROM FACT_SALES;

4. Sample query to verify joins:
   SELECT 
       COUNT(*) AS record_count,
       SUM(total_amount) AS total_revenue
   FROM FACT_SALES f
   JOIN DIM_CUSTOMER c ON f.customer_key = c.customer_key
   JOIN DIM_PRODUCT p ON f.product_key = p.product_key
   JOIN DIM_TIME t ON f.time_key = t.time_key;

================================================================================
STEP 7: RUN OLAP QUERIES
================================================================================

1. Open MySQL command line or MySQL Workbench

2. Run queries_dw.sql:
   
   Method 1 (Command Line):
   ------------------------
   mysql -u root -p walmart_dw < queries_dw.sql > query_results.txt
   
   Method 2 (MySQL Workbench):
   ---------------------------
   - Open MySQL Workbench
   - File -> Open SQL Script -> Select queries_dw.sql
   - Click Execute
   - Results will appear in result panels

3. Run individual queries:
   - Open queries_dw.sql in a text editor
   - Copy a specific query (Q1, Q2, etc.)
   - Paste and execute in MySQL

4. The script contains 20 queries:
   - Q1, Q11: Top products by weekday/weekend with monthly drill-down
   - Q2: Customer demographics by purchase amount
   - Q3: Product category sales by occupation
   - Q4: Purchases by gender/age with quarterly trend
   - Q5: Top occupations by product category
   - Q6: City category by marital status (monthly)
   - Q7: Average purchase by stay duration and gender
   - Q8: Top 5 cities by product category
   - Q9: Monthly sales growth by category
   - Q10: Weekend vs weekday by age group
   - Q12: Store revenue growth quarterly (2017)
   - Q13: Supplier sales by store and product
   - Q14: Seasonal analysis with drill-down
   - Q15: Store-supplier revenue volatility
   - Q16: Product affinity analysis
   - Q17: Yearly trends with ROLLUP
   - Q18: H1 vs H2 analysis
   - Q19: Outlier detection
   - Q20: STORE_QUARTERLY_SALES view

================================================================================
STEP 8: GENERATE PROJECT REPORT
================================================================================

1. Ensure python-docx is installed:
   pip install python-docx

2. Run the report generator:
   python generate_report.py

3. The report will be created at:
   report/project_report.docx

4. Open the report in Microsoft Word or compatible software

Note: If python-docx is not available, you can manually create the report
using the structure described in the generate_report.py script.

================================================================================
EXPECTED OUTPUT
================================================================================

After successful execution, you should have:

1. Database Schema:
   - 6 dimension tables populated
   - 1 fact table (FACT_SALES) with joined transactional data
   - All foreign key relationships established

2. ETL Process Output:
   [Stream Producer] Started reading from CSV...
   [Stream Producer] Read 1000 rows...
   [HybridJoin] Starting HYBRIDJOIN algorithm...
   [Main] Progress: 1000 records joined, 5000 total processed...
   [Main] ETL PROCESS COMPLETED
   Total stream tuples processed: 550000
   Successfully joined and loaded: 545000
   Stream producer rows read: 550000

3. Query Results:
   - 20 OLAP queries executed successfully
   - Various analytical insights generated
   - Materialized view created (STORE_QUARTERLY_SALES)

================================================================================
TROUBLESHOOTING
================================================================================

Problem: "ModuleNotFoundError: No module named 'mysql.connector'"
Solution: Install mysql-connector-python
          pip install mysql-connector-python

Problem: "Access denied for user"
Solution: Check MySQL credentials
          Verify user has proper privileges
          Try: GRANT ALL PRIVILEGES ON walmart_dw.* TO 'user'@'localhost';

Problem: "Table doesn't exist"
Solution: Run create_dw.sql first to create schema
          Verify you're using the correct database: USE walmart_dw;

Problem: "File not found: data/transactional_data.csv"
Solution: Verify data files are in the 'data' folder
          Check file paths in main.py
          Ensure CSV files are not corrupted

Problem: "Hash table full" or "Stream buffer full"
Solution: This is expected behavior for high-velocity streams
          The algorithm will process data as slots become available
          Consider increasing hash table size (hS) in hybrid_join.py

Problem: "Out of memory"
Solution: Process data in smaller batches
          Increase system RAM if possible
          Close other applications

Problem: "Connection timeout"
Solution: Increase MySQL connection timeout
          Check MySQL server is running
          Verify network connectivity

Problem: "Foreign key constraint fails"
Solution: Ensure dimension tables are loaded before fact table
          Check for missing dimension records
          Verify data integrity in CSV files

Problem: "Query takes too long"
Solution: Add indexes on frequently queried columns
          Use EXPLAIN to analyze query plans
          Consider materialized views for complex queries

Problem: "Report generation fails"
Solution: Install python-docx: pip install python-docx
          Check write permissions in report/ directory
          Verify Python version (3.7+)

================================================================================
CONTACT AND SUPPORT
================================================================================

For issues or questions:
- Review this README thoroughly
- Check error messages for specific guidance
- Verify all prerequisites are met
- Ensure data files are in correct format

================================================================================
NOTES
================================================================================

1. The HYBRIDJOIN algorithm processes data in near-real-time, simulating
   a continuous stream from transactional_data.csv

2. Dimension tables are loaded first to ensure referential integrity

3. The algorithm uses Customer_ID as the primary join key, but can be
   modified to use Product_ID

4. All timestamps and dates are handled according to MySQL date formats

5. The project is designed to handle large datasets efficiently using
   batch processing and optimized data structures

================================================================================
END OF README
================================================================================

