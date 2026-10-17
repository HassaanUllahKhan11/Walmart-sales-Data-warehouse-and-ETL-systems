"""
Data Loader Module
==================
Handles loading master data from CSV files and database operations
"""

import csv
import mysql.connector
from mysql.connector import Error
from datetime import datetime


class DataLoader:
    """Handles ETL operations for dimension and fact tables"""
    
    def __init__(self, host, user, password, database):
        """
        Initialize database connection
        
        Args:
            host: MySQL host
            user: MySQL username
            password: MySQL password
            database: Database name
        """
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.connection = None
        self.cursor = None
    
    def connect(self):
        """Establish database connection"""
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database
            )
            self.cursor = self.connection.cursor()
            print("[Data Loader] Connected to MySQL database")
            return True
        except Error as e:
            print(f"[Data Loader] ERROR connecting to database: {e}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("[Data Loader] Disconnected from database")
    
    def load_customer_master_data(self, csv_file_path):
        """Load customer master data into DIM_CUSTOMER"""
        print("[Data Loader] Loading customer master data...")
        
        try:
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                csv_reader = csv.DictReader(file)
                count = 0
                
                for row in csv_reader:
                    try:
                        query = """
                        INSERT INTO DIM_CUSTOMER 
                        (customer_id, gender, age, occupation, marital_status, 
                         stay_in_current_city_years, effective_date, is_current)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                        gender = VALUES(gender),
                        age = VALUES(age),
                        occupation = VALUES(occupation),
                        marital_status = VALUES(marital_status),
                        stay_in_current_city_years = VALUES(stay_in_current_city_years)
                        """
                        
                        values = (
                            int(row['Customer_ID']),
                            row['Gender'],
                            row['Age'],
                            int(row['Occupation']),
                            int(row['Marital_Status']),
                            int(row['Stay_In_Current_City_Years']),
                            datetime.now().date(),
                            1
                        )
                        
                        self.cursor.execute(query, values)
                        count += 1
                        
                    except Exception as e:
                        print(f"[Data Loader] Error inserting customer {row.get('Customer_ID', 'unknown')}: {e}")
                        continue
                
                self.connection.commit()
                print(f"[Data Loader] Loaded {count} customers into DIM_CUSTOMER")
                return count
        
        except Exception as e:
            print(f"[Data Loader] ERROR loading customer data: {e}")
            return 0
    
    def load_product_master_data(self, csv_file_path):
        """Load product master data into DIM_PRODUCT, DIM_STORE, DIM_SUPPLIER"""
        print("[Data Loader] Loading product master data...")
        
        stores = {}  # store_id -> store_name
        suppliers = {}  # supplier_id -> supplier_name
        products_loaded = 0
        
        try:
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                csv_reader = csv.DictReader(file)
                
                for row in csv_reader:
                    try:
                        # Extract store info
                        store_id = int(row['storeID'])
                        store_name = row['storeName']
                        if store_id not in stores:
                            stores[store_id] = store_name
                        
                        # Extract supplier info
                        supplier_id = int(row['supplierID'])
                        supplier_name = row['supplierName']
                        if supplier_id not in suppliers:
                            suppliers[supplier_id] = supplier_name
                        
                        # Insert product
                        query = """
                        INSERT INTO DIM_PRODUCT 
                        (product_id, product_category, price, effective_date, is_current)
                        VALUES (%s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                        product_category = VALUES(product_category),
                        price = VALUES(price)
                        """
                        
                        # Clean price (remove $ if present)
                        price_str = row['price$'].replace('$', '').strip()
                        price = float(price_str)
                        
                        values = (
                            row['Product_ID'],
                            row['Product_Category'],
                            price,
                            datetime.now().date(),
                            1
                        )
                        
                        self.cursor.execute(query, values)
                        products_loaded += 1
                        
                    except Exception as e:
                        print(f"[Data Loader] Error inserting product {row.get('Product_ID', 'unknown')}: {e}")
                        continue
                
                self.connection.commit()
                print(f"[Data Loader] Loaded {products_loaded} products into DIM_PRODUCT")
        
        except Exception as e:
            print(f"[Data Loader] ERROR loading product data: {e}")
        
        # Load stores
        print("[Data Loader] Loading stores...")
        store_count = 0
        for store_id, store_name in stores.items():
            try:
                query = """
                INSERT INTO DIM_STORE (store_id, store_name, effective_date, is_current)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE store_name = VALUES(store_name)
                """
                self.cursor.execute(query, (store_id, store_name, datetime.now().date(), 1))
                store_count += 1
            except Exception as e:
                print(f"[Data Loader] Error inserting store {store_id}: {e}")
        
        self.connection.commit()
        print(f"[Data Loader] Loaded {store_count} stores into DIM_STORE")
        
        # Load suppliers
        print("[Data Loader] Loading suppliers...")
        supplier_count = 0
        for supplier_id, supplier_name in suppliers.items():
            try:
                query = """
                INSERT INTO DIM_SUPPLIER (supplier_id, supplier_name, effective_date, is_current)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE supplier_name = VALUES(supplier_name)
                """
                self.cursor.execute(query, (supplier_id, supplier_name, datetime.now().date(), 1))
                supplier_count += 1
            except Exception as e:
                print(f"[Data Loader] Error inserting supplier {supplier_id}: {e}")
        
        self.connection.commit()
        print(f"[Data Loader] Loaded {supplier_count} suppliers into DIM_SUPPLIER")
        
        return products_loaded
    
    def load_time_dimension(self, start_date='2015-01-01', end_date='2025-12-31'):
        """Populate DIM_TIME with date range"""
        print("[Data Loader] Loading time dimension...")
        
        from datetime import timedelta
        
        current_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
        count = 0
        
        seasons = {
            (12, 1, 2): 'Winter',
            (3, 4, 5): 'Spring',
            (6, 7, 8): 'Summer',
            (9, 10, 11): 'Fall'
        }
        
        while current_date <= end:
            day = current_date.day
            month = current_date.month
            year = current_date.year
            
            # Calculate quarter
            quarter = (month - 1) // 3 + 1
            
            # Calculate week number (ISO week)
            week_number = current_date.isocalendar()[1]
            
            # Day of week (0=Monday, 6=Sunday)
            day_of_week = current_date.weekday()
            day_name = current_date.strftime('%A')
            month_name = current_date.strftime('%B')
            
            # Check if weekend
            is_weekend = day_of_week >= 5  # Saturday or Sunday
            
            # Determine season
            season = 'Unknown'
            for months, season_name in seasons.items():
                if month in months:
                    season = season_name
                    break
            
            try:
                query = """
                INSERT INTO DIM_TIME 
                (date_value, day, month, quarter, year, week_number, day_of_week, 
                 day_name, month_name, is_weekend, season)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE date_value = date_value
                """
                
                values = (
                    current_date, day, month, quarter, year, week_number,
                    day_of_week, day_name, month_name, is_weekend, season
                )
                
                self.cursor.execute(query, values)
                count += 1
                
            except Exception as e:
                print(f"[Data Loader] Error inserting date {current_date}: {e}")
            
            current_date += timedelta(days=1)
        
        self.connection.commit()
        print(f"[Data Loader] Loaded {count} dates into DIM_TIME")
        return count
    
    def load_city_dimension(self):
        """Load city categories into DIM_CITY"""
        print("[Data Loader] Loading city dimension...")
        
        city_categories = ['A', 'B', 'C']
        count = 0
        
        for city_cat in city_categories:
            try:
                query = """
                INSERT INTO DIM_CITY (city_category, city_name)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE city_category = city_category
                """
                self.cursor.execute(query, (city_cat, f"City Category {city_cat}"))
                count += 1
            except Exception as e:
                print(f"[Data Loader] Error inserting city {city_cat}: {e}")
        
        self.connection.commit()
        print(f"[Data Loader] Loaded {count} cities into DIM_CITY")
        return count
    
    def get_customer_key(self, customer_id):
        """Get customer_key for given customer_id"""
        query = "SELECT customer_key FROM DIM_CUSTOMER WHERE customer_id = %s AND is_current = 1"
        self.cursor.execute(query, (customer_id,))
        result = self.cursor.fetchone()
        return result[0] if result else None
    
    def get_product_key(self, product_id):
        """Get product_key for given product_id"""
        query = "SELECT product_key FROM DIM_PRODUCT WHERE product_id = %s AND is_current = 1"
        self.cursor.execute(query, (product_id,))
        result = self.cursor.fetchone()
        return result[0] if result else None
    
    def get_time_key(self, date_str):
        """Get time_key for given date string"""
        query = "SELECT time_key FROM DIM_TIME WHERE date_value = %s"
        self.cursor.execute(query, (date_str,))
        result = self.cursor.fetchone()
        return result[0] if result else None
    
    def get_city_key(self, city_category):
        """Get city_key for given city_category"""
        query = "SELECT city_key FROM DIM_CITY WHERE city_category = %s"
        self.cursor.execute(query, (city_category,))
        result = self.cursor.fetchone()
        return result[0] if result else None
    
    def get_store_key(self, store_id):
        """Get store_key for given store_id"""
        query = "SELECT store_key FROM DIM_STORE WHERE store_id = %s AND is_current = 1"
        self.cursor.execute(query, (store_id,))
        result = self.cursor.fetchone()
        return result[0] if result else None
    
    def get_supplier_key(self, supplier_id):
        """Get supplier_key for given supplier_id"""
        query = "SELECT supplier_key FROM DIM_SUPPLIER WHERE supplier_id = %s AND is_current = 1"
        self.cursor.execute(query, (supplier_id,))
        result = self.cursor.fetchone()
        return result[0] if result else None
    
    def get_product_info(self, product_id):
        """Get product info including store and supplier for given product_id"""
        query = """
        SELECT p.product_key, p.price, pm.storeID, pm.supplierID
        FROM DIM_PRODUCT p
        JOIN (SELECT DISTINCT Product_ID, storeID, supplierID 
              FROM product_master_data) pm ON p.product_id = pm.Product_ID
        WHERE p.product_id = %s AND p.is_current = 1
        LIMIT 1
        """
        # Note: This requires product_master_data to be accessible
        # Alternative: Store this mapping during product load
        return None
    
    def insert_fact_sales(self, fact_record):
        """
        Insert a record into FACT_SALES
        
        Args:
            fact_record: Dictionary with keys: customer_key, product_key, time_key,
                        city_key, store_key, supplier_key, order_id, quantity,
                        unit_price, total_amount
        """
        query = """
        INSERT INTO FACT_SALES 
        (customer_key, product_key, time_key, city_key, store_key, supplier_key,
         order_id, quantity, unit_price, total_amount)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        values = (
            fact_record['customer_key'],
            fact_record['product_key'],
            fact_record['time_key'],
            fact_record['city_key'],
            fact_record['store_key'],
            fact_record['supplier_key'],
            fact_record['order_id'],
            fact_record['quantity'],
            fact_record['unit_price'],
            fact_record['total_amount']
        )
        
        try:
            self.cursor.execute(query, values)
            return True
        except Exception as e:
            print(f"[Data Loader] Error inserting fact record: {e}")
            return False
    
    def commit(self):
        """Commit current transaction"""
        if self.connection:
            self.connection.commit()
    
    def load_master_data_mapping(self, product_csv_path):
        """Load product to store/supplier mapping into memory"""
        mapping = {}
        try:
            with open(product_csv_path, 'r', encoding='utf-8') as file:
                csv_reader = csv.DictReader(file)
                for row in csv_reader:
                    product_id = row['Product_ID']
                    mapping[product_id] = {
                        'store_id': int(row['storeID']),
                        'supplier_id': int(row['supplierID'])
                    }
        except Exception as e:
            print(f"[Data Loader] Error loading product mapping: {e}")
        return mapping

