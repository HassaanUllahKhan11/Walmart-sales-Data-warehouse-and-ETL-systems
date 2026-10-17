"""
HYBRIDJOIN Algorithm Implementation
===================================
Implements the stream-based join algorithm for near-real-time data warehousing
Joins fast-arriving stream data (S) with large disk-based master data (R)
"""

import threading
import csv
import time
from queue import Queue as ThreadQueue
from utils.structures import HashTable, Queue
from data_loader import DataLoader


class HybridJoin:
    """
    HYBRIDJOIN Algorithm Implementation
    
    Components:
    - Stream Buffer: Thread-safe queue for incoming stream tuples
    - Hash Table: Multi-map with 10,000 slots
    - Queue: Doubly linked list for FIFO order
    - Disk Buffer: Partition size vP = 500 tuples
    - Stream Input (w): Available slots in hash table
    """
    
    def __init__(self, data_loader, customer_master_path, product_master_path, 
                 stream_buffer, vP=500, hS=10000):
        """
        Initialize HYBRIDJOIN
        
        Args:
            data_loader: DataLoader instance for database operations
            customer_master_path: Path to customer_master_data.csv
            product_master_path: Path to product_master_data.csv
            stream_buffer: Thread-safe queue for stream tuples
            vP: Disk partition size (default 500)
            hS: Hash table size (default 10,000)
        """
        self.data_loader = data_loader
        self.customer_master_path = customer_master_path
        self.product_master_path = product_master_path
        self.stream_buffer = stream_buffer
        
        # Algorithm parameters
        self.vP = vP  # Disk partition size
        self.hS = hS  # Hash table size
        
        # Data structures
        self.hash_table = HashTable(num_slots=hS)
        self.queue = Queue()
        self.disk_buffer = []  # Current partition from master data
        
        # Stream input (w): available slots in hash table
        self.w = hS  # Initially all slots are free
        
        # Master data mappings (loaded into memory)
        self.customer_master = {}  # customer_id -> customer_data
        self.product_master = {}  # product_id -> product_data
        
        # Statistics
        self.joined_count = 0
        self.total_processed = 0
        self.running = False
        
        # Load master data into memory
        self._load_master_data()
    
    def _load_master_data(self):
        """Load master data from CSV files into memory"""
        print("[HybridJoin] Loading customer master data into memory...")
        
        # Load customer master data
        try:
            with open(self.customer_master_path, 'r', encoding='utf-8') as file:
                csv_reader = csv.DictReader(file)
                for row in csv_reader:
                    customer_id = int(row['Customer_ID'])
                    self.customer_master[customer_id] = {
                        'customer_id': customer_id,
                        'gender': row['Gender'],
                        'age': row['Age'],
                        'occupation': int(row['Occupation']),
                        'city_category': row['City_Category'],
                        'stay_years': int(row['Stay_In_Current_City_Years']),
                        'marital_status': int(row['Marital_Status'])
                    }
            print(f"[HybridJoin] Loaded {len(self.customer_master)} customers")
        except Exception as e:
            print(f"[HybridJoin] ERROR loading customer master data: {e}")
        
        # Load product master data
        print("[HybridJoin] Loading product master data into memory...")
        try:
            with open(self.product_master_path, 'r', encoding='utf-8') as file:
                csv_reader = csv.DictReader(file)
                for row in csv_reader:
                    product_id = row['Product_ID']
                    price_str = row['price$'].replace('$', '').strip()
                    self.product_master[product_id] = {
                        'product_id': product_id,
                        'product_category': row['Product_Category'],
                        'price': float(price_str),
                        'store_id': int(row['storeID']),
                        'supplier_id': int(row['supplierID']),
                        'store_name': row['storeName'],
                        'supplier_name': row['supplierName']
                    }
            print(f"[HybridJoin] Loaded {len(self.product_master)} products")
        except Exception as e:
            print(f"[HybridJoin] ERROR loading product master data: {e}")
    
    def _load_disk_partition(self, join_key, join_type='customer'):
        """
        Load a partition of size vP from master data into disk buffer
        
        Args:
            join_key: The key to use for loading partition (e.g., Customer_ID or Product_ID)
            join_type: 'customer' or 'product'
        """
        self.disk_buffer = []
        
        if join_type == 'customer':
            # For customer join, we load customers around the join_key
            # Since master data is indexed/sorted, we can load a range
            sorted_customers = sorted(self.customer_master.keys())
            
            try:
                # Find position of join_key
                if join_key in sorted_customers:
                    idx = sorted_customers.index(join_key)
                    # Load vP customers starting from this position
                    start_idx = max(0, idx - self.vP // 2)
                    end_idx = min(len(sorted_customers), start_idx + self.vP)
                    
                    for i in range(start_idx, end_idx):
                        customer_id = sorted_customers[i]
                        self.disk_buffer.append(self.customer_master[customer_id])
            except Exception as e:
                print(f"[HybridJoin] Error loading customer partition: {e}")
        
        elif join_type == 'product':
            # For product join, load products around the join_key
            sorted_products = sorted(self.product_master.keys())
            
            try:
                if join_key in sorted_products:
                    idx = sorted_products.index(join_key)
                    start_idx = max(0, idx - self.vP // 2)
                    end_idx = min(len(sorted_products), start_idx + self.vP)
                    
                    for i in range(start_idx, end_idx):
                        product_id = sorted_products[i]
                        self.disk_buffer.append(self.product_master[product_id])
            except Exception as e:
                print(f"[HybridJoin] Error loading product partition: {e}")
        
        return len(self.disk_buffer)
    
    def _join_with_master(self, stream_tuple, master_tuple, master_type):
        """
        Join stream tuple with master tuple and insert into FACT_SALES
        
        Args:
            stream_tuple: Tuple from stream (transactional data)
            master_tuple: Tuple from master data
            master_type: 'customer' or 'product'
        """
        try:
            # Get dimension keys from database
            customer_id = stream_tuple['Customer_ID']
            product_id = stream_tuple['Product_ID']
            date_str = stream_tuple['date']
            
            # Get customer key
            customer_key = self.data_loader.get_customer_key(customer_id)
            if customer_key is None:
                return False
            
            # Get product key
            product_key = self.data_loader.get_product_key(product_id)
            if product_key is None:
                return False
            
            # Get time key
            time_key = self.data_loader.get_time_key(date_str)
            if time_key is None:
                return False
            
            # Get city key (from customer master data)
            customer_data = self.customer_master.get(customer_id)
            if customer_data is None:
                return False
            
            city_category = customer_data['city_category']
            city_key = self.data_loader.get_city_key(city_category)
            if city_key is None:
                return False
            
            # Get store and supplier keys (from product master data)
            product_data = self.product_master.get(product_id)
            if product_data is None:
                return False
            
            store_id = product_data['store_id']
            supplier_id = product_data['supplier_id']
            
            store_key = self.data_loader.get_store_key(store_id)
            if store_key is None:
                return False
            
            supplier_key = self.data_loader.get_supplier_key(supplier_id)
            if supplier_key is None:
                return False
            
            # Calculate total amount
            quantity = stream_tuple['quantity']
            unit_price = product_data['price']
            total_amount = quantity * unit_price
            
            # Create fact record
            fact_record = {
                'customer_key': customer_key,
                'product_key': product_key,
                'time_key': time_key,
                'city_key': city_key,
                'store_key': store_key,
                'supplier_key': supplier_key,
                'order_id': stream_tuple['orderID'],
                'quantity': quantity,
                'unit_price': unit_price,
                'total_amount': total_amount
            }
            
            # Insert into FACT_SALES
            if self.data_loader.insert_fact_sales(fact_record):
                self.joined_count += 1
                # Commit every 100 records for performance
                if self.joined_count % 100 == 0:
                    self.data_loader.commit()
                return True
            
            return False
        
        except Exception as e:
            print(f"[HybridJoin] Error in join operation: {e}")
            return False
    
    def execute(self):
        """
        Main HYBRIDJOIN algorithm execution
        
        Algorithm Steps:
        1. Initialize data structures (done in __init__)
        2. Check stream buffer for new tuples, load up to w tuples into hash table
        3. Take oldest queue key → load disk partition vP of Master Data
        4. Join stream tuples with master tuples
        5. On match: generate joined record, insert into FACT_SALES, remove from hash table and queue
        6. Increase w by freed slots
        7. Continue until stream is exhausted
        """
        print("[HybridJoin] Starting HYBRIDJOIN algorithm...")
        self.running = True
        
        # Outer loop: continue while stream has data or hash table has entries
        while self.running:
            # Step 2: Load up to w tuples from stream buffer into hash table
            loaded_count = 0
            temp_buffer = []
            
            # Collect up to w tuples from stream buffer
            while loaded_count < self.w and not self.stream_buffer.empty():
                try:
                    stream_tuple = self.stream_buffer.get(timeout=0.1)
                    temp_buffer.append(stream_tuple)
                    loaded_count += 1
                except:
                    break
            
            # Insert collected tuples into hash table and queue
            for stream_tuple in temp_buffer:
                # Use Customer_ID as join key (can be changed to Product_ID)
                join_key = stream_tuple['Customer_ID']
                
                # Insert into hash table
                queue_node = self.queue.enqueue(join_key)
                hash_entry = self.hash_table.insert(join_key, stream_tuple, queue_node)
                queue_node.data = hash_entry  # Link queue node to hash entry
                
                self.total_processed += 1
            
            # Update w (available slots)
            self.w = self.hash_table.get_free_slots()
            
            # Step 3: Process queue - take oldest key and load disk partition
            if not self.queue.is_empty():
                oldest_key = self.queue.peek()
                
                # Load disk partition for customer join
                partition_size = self._load_disk_partition(oldest_key, join_type='customer')
                
                if partition_size > 0:
                    # Step 4: Inner loop - probe hash table with disk partition tuples
                    matched_entries = []
                    
                    for master_tuple in self.disk_buffer:
                        master_key = master_tuple['customer_id']
                        
                        # Find matching stream tuples in hash table
                        hash_entries = self.hash_table.find(master_key)
                        
                        for hash_entry in hash_entries:
                            stream_tuple = hash_entry['value']
                            
                            # Step 5: Join and insert into FACT_SALES
                            if self._join_with_master(stream_tuple, master_tuple, 'customer'):
                                # Mark for removal
                                matched_entries.append(hash_entry)
                    
                    # Step 6: Remove matched entries from hash table and queue
                    freed_slots = 0
                    for hash_entry in matched_entries:
                        # Remove from hash table
                        if self.hash_table.remove(hash_entry):
                            freed_slots += 1
                        
                        # Remove from queue
                        queue_node = hash_entry.get('queue_node')
                        if queue_node:
                            self.queue.remove_node(queue_node)
                    
                    # Increase w by freed slots
                    self.w += freed_slots
                    
                    # If queue is empty but stream buffer has more data, continue
                    if self.queue.is_empty() and not self.stream_buffer.empty():
                        continue
                    
                    # If queue still has entries, continue with next oldest key
                    if not self.queue.is_empty():
                        continue
            
            # Check if we should continue
            if self.queue.is_empty() and self.stream_buffer.empty():
                # Wait a bit to see if more data arrives
                time.sleep(0.5)
                if self.stream_buffer.empty() and self.queue.is_empty():
                    print("[HybridJoin] Stream exhausted and queue empty. Stopping...")
                    break
        
        # Final commit
        self.data_loader.commit()
        print(f"[HybridJoin] Algorithm completed.")
        print(f"[HybridJoin] Total processed: {self.total_processed}")
        print(f"[HybridJoin] Successfully joined: {self.joined_count}")
        self.running = False
    
    def stop(self):
        """Stop the HYBRIDJOIN algorithm"""
        self.running = False

