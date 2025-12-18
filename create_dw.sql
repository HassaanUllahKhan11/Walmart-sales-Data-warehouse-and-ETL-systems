-- =====================================================
-- Data Warehouse 
-- =====================================================
-- Hassaan Ullah Khan
-- i21 1695
-- =====================================================

-- Drop existing schema if exists
DROP DATABASE IF EXISTS walmart_dw;
CREATE DATABASE walmart_dw;
USE walmart_dw;

-- =====================================================
-- DIMENSION TABLES
-- =====================================================

-- DIM_CUSTOMER: Customer dimension table
CREATE TABLE DIM_CUSTOMER (
    customer_key INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL UNIQUE,
    gender VARCHAR(10) NOT NULL,
    age VARCHAR(20) NOT NULL,
    occupation INT NOT NULL,
    marital_status INT NOT NULL,
    stay_in_current_city_years INT NOT NULL,
    effective_date DATE NOT NULL,
    expiry_date DATE,
    is_current BOOLEAN DEFAULT TRUE,
    INDEX idx_customer_id (customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- DIM_PRODUCT: Product dimension table
CREATE TABLE DIM_PRODUCT (
    product_key INT AUTO_INCREMENT PRIMARY KEY,
    product_id VARCHAR(50) NOT NULL UNIQUE,
    product_category VARCHAR(100) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    effective_date DATE NOT NULL,
    expiry_date DATE,
    is_current BOOLEAN DEFAULT TRUE,
    INDEX idx_product_id (product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- DIM_TIME: Time dimension table
CREATE TABLE DIM_TIME (
    time_key INT AUTO_INCREMENT PRIMARY KEY,
    date_value DATE NOT NULL UNIQUE,
    day INT NOT NULL,
    month INT NOT NULL,
    quarter INT NOT NULL,
    year INT NOT NULL,
    week_number INT NOT NULL,
    day_of_week INT NOT NULL,
    day_name VARCHAR(20) NOT NULL,
    month_name VARCHAR(20) NOT NULL,
    is_weekend BOOLEAN NOT NULL,
    season VARCHAR(20) NOT NULL,
    is_holiday BOOLEAN DEFAULT FALSE,
    INDEX idx_date (date_value),
    INDEX idx_year_month (year, month),
    INDEX idx_year_quarter (year, quarter)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- DIM_CITY: City dimension table
CREATE TABLE DIM_CITY (
    city_key INT AUTO_INCREMENT PRIMARY KEY,
    city_category VARCHAR(10) NOT NULL UNIQUE,
    city_name VARCHAR(100),
    region VARCHAR(50),
    INDEX idx_city_category (city_category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- DIM_STORE: Store dimension table
CREATE TABLE DIM_STORE (
    store_key INT AUTO_INCREMENT PRIMARY KEY,
    store_id INT NOT NULL UNIQUE,
    store_name VARCHAR(100) NOT NULL,
    effective_date DATE NOT NULL,
    expiry_date DATE,
    is_current BOOLEAN DEFAULT TRUE,
    INDEX idx_store_id (store_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- DIM_SUPPLIER: Supplier dimension table
CREATE TABLE DIM_SUPPLIER (
    supplier_key INT AUTO_INCREMENT PRIMARY KEY,
    supplier_id INT NOT NULL UNIQUE,
    supplier_name VARCHAR(100) NOT NULL,
    effective_date DATE NOT NULL,
    expiry_date DATE,
    is_current BOOLEAN DEFAULT TRUE,
    INDEX idx_supplier_id (supplier_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- FACT TABLE
-- =====================================================

-- FACT_SALES: Sales fact table
CREATE TABLE FACT_SALES (
    sales_key INT AUTO_INCREMENT PRIMARY KEY,
    customer_key INT NOT NULL,
    product_key INT NOT NULL,
    time_key INT NOT NULL,
    city_key INT NOT NULL,
    store_key INT NOT NULL,
    supplier_key INT NOT NULL,
    order_id INT NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    total_amount DECIMAL(12, 2) NOT NULL,
    created_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_key) REFERENCES DIM_CUSTOMER(customer_key),
    FOREIGN KEY (product_key) REFERENCES DIM_PRODUCT(product_key),
    FOREIGN KEY (time_key) REFERENCES DIM_TIME(time_key),
    FOREIGN KEY (city_key) REFERENCES DIM_CITY(city_key),
    FOREIGN KEY (store_key) REFERENCES DIM_STORE(store_key),
    FOREIGN KEY (supplier_key) REFERENCES DIM_SUPPLIER(supplier_key),
    INDEX idx_customer (customer_key),
    INDEX idx_product (product_key),
    INDEX idx_time (time_key),
    INDEX idx_city (city_key),
    INDEX idx_store (store_key),
    INDEX idx_supplier (supplier_key),
    INDEX idx_order_id (order_id),
    INDEX idx_time_product (time_key, product_key),
    INDEX idx_customer_time (customer_key, time_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================
-- END OF SCHEMA CREATION
-- =====================================================

