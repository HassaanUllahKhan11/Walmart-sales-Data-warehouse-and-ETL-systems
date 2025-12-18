"""
Main Entry Point for HYBRIDJOIN Data Warehouse ETL
==================================================
This script orchestrates the entire ETL process:
1. Loads dimension tables from master data
2. Starts stream producer thread
3. Executes HYBRIDJOIN algorithm
4. Loads fact table with joined data
"""

import sys
import os
import threading
from queue import Queue as ThreadQueue

# Add current directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from data_loader import DataLoader
from stream_producer import StreamProducer
from hybrid_join import HybridJoin


def get_database_credentials():
    """Prompt user for database credentials"""
    print("=" * 60)
    print("Walmart Data Warehouse - HYBRIDJOIN ETL System")
    print("=" * 60)
    print("\nPlease enter MySQL database credentials:\n")
    
    host = input("Host [localhost]: ").strip() or "localhost"
    user = input("Username: ").strip()
    password = input("Password: ").strip()
    database = input("Database [walmart_dw]: ").strip() or "walmart_dw"
    
    return host, user, password, database


def main():
    """Main execution function"""
    
    # Get database credentials
    host, user, password, database = get_database_credentials()
    
    # File paths (adjust if needed)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, 'data')
    
    customer_master_path = os.path.join(data_dir, 'customer_master_data.csv')
    product_master_path = os.path.join(data_dir, 'product_master_data.csv')
    transactional_data_path = os.path.join(data_dir, 'transactional_data.csv')
    
    # Verify files exist
    for file_path in [customer_master_path, product_master_path, transactional_data_path]:
        if not os.path.exists(file_path):
            print(f"ERROR: File not found: {file_path}")
            return
    
    # Initialize data loader
    print("\n[Main] Initializing data loader...")
    data_loader = DataLoader(host, user, password, database)
    
    if not data_loader.connect():
        print("ERROR: Failed to connect to database. Exiting.")
        return
    
    try:
        # Step 1: Load dimension tables
        print("\n" + "=" * 60)
        print("STEP 1: Loading Dimension Tables")
        print("=" * 60)
        
        # Load time dimension
        data_loader.load_time_dimension('2015-01-01', '2025-12-31')
        
        # Load city dimension
        data_loader.load_city_dimension()
        
        # Load customer master data
        data_loader.load_customer_master_data(customer_master_path)
        
        # Load product master data (includes stores and suppliers)
        data_loader.load_product_master_data(product_master_path)
        
        print("\n[Main] Dimension tables loaded successfully!")
        
        # Step 2: Initialize stream buffer and producer
        print("\n" + "=" * 60)
        print("STEP 2: Initializing Stream Producer")
        print("=" * 60)
        
        stream_buffer = ThreadQueue(maxsize=10000)  # Thread-safe queue
        stream_producer = StreamProducer(
            csv_file_path=transactional_data_path,
            stream_buffer=stream_buffer,
            delay=0.0001  # Small delay to simulate real-time stream
        )
        
        # Step 3: Initialize HYBRIDJOIN
        print("\n" + "=" * 60)
        print("STEP 3: Initializing HYBRIDJOIN Algorithm")
        print("=" * 60)
        
        hybrid_join = HybridJoin(
            data_loader=data_loader,
            customer_master_path=customer_master_path,
            product_master_path=product_master_path,
            stream_buffer=stream_buffer,
            vP=500,  # Disk partition size
            hS=10000  # Hash table size
        )
        
        # Step 4: Start stream producer thread
        print("\n" + "=" * 60)
        print("STEP 4: Starting ETL Process")
        print("=" * 60)
        
        stream_producer.start()
        
        # Give producer a moment to start reading
        import time
        time.sleep(1)
        
        # Step 5: Execute HYBRIDJOIN algorithm (runs in main thread)
        print("\n[Main] Starting HYBRIDJOIN algorithm...")
        print("[Main] Processing stream data and joining with master data...\n")
        
        # Run HYBRIDJOIN in a separate thread so we can monitor progress
        join_thread = threading.Thread(target=hybrid_join.execute, daemon=False)
        join_thread.start()
        
        # Monitor progress
        last_joined = 0
        while join_thread.is_alive() or not stream_buffer.empty():
            time.sleep(5)  # Check every 5 seconds
            
            current_joined = hybrid_join.joined_count
            if current_joined > last_joined:
                print(f"[Main] Progress: {current_joined} records joined, "
                      f"{hybrid_join.total_processed} total processed, "
                      f"Queue size: {stream_buffer.qsize()}")
                last_joined = current_joined
        
        # Wait for join thread to complete
        join_thread.join(timeout=30)
        
        # Stop stream producer
        stream_producer.stop()
        
        # Final statistics
        print("\n" + "=" * 60)
        print("ETL PROCESS COMPLETED")
        print("=" * 60)
        print(f"Total stream tuples processed: {hybrid_join.total_processed}")
        print(f"Successfully joined and loaded: {hybrid_join.joined_count}")
        print(f"Stream producer rows read: {stream_producer.rows_read}")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n[Main] Process interrupted by user")
        stream_producer.stop()
        hybrid_join.stop()
    
    except Exception as e:
        print(f"\n[Main] ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Close database connection
        data_loader.disconnect()
        print("\n[Main] Database connection closed. Exiting.")


if __name__ == "__main__":
    main()

