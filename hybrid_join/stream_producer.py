"""
Stream Producer Thread
======================
Continuously reads transactional data from CSV and pushes it into the stream buffer
This runs in a separate thread independent of the join operation
"""

import csv
import threading
import time
from queue import Queue as ThreadQueue


class StreamProducer:
    """Producer thread that continuously reads from transactional_data.csv"""
    
    def __init__(self, csv_file_path, stream_buffer, delay=0.001):
        """
        Initialize stream producer
        
        Args:
            csv_file_path: Path to transactional_data.csv
            stream_buffer: Thread-safe queue to push stream tuples
            delay: Delay between reading rows (simulates real-time stream)
        """
        self.csv_file_path = csv_file_path
        self.stream_buffer = stream_buffer
        self.delay = delay
        self.running = False
        self.thread = None
        self.rows_read = 0
    
    def start(self):
        """Start the producer thread"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._produce, daemon=True)
        self.thread.start()
        print("[Stream Producer] Started reading from CSV...")
    
    def stop(self):
        """Stop the producer thread"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print(f"[Stream Producer] Stopped. Total rows read: {self.rows_read}")
    
    def _produce(self):
        """Main producer loop - reads CSV and pushes to stream buffer"""
        try:
            with open(self.csv_file_path, 'r', encoding='utf-8') as file:
                csv_reader = csv.DictReader(file)
                
                # Skip header if needed
                for row in csv_reader:
                    if not self.running:
                        break
                    
                    # Parse row data
                    stream_tuple = {
                        'orderID': int(row['orderID']),
                        'Customer_ID': int(row['Customer_ID']),
                        'Product_ID': row['Product_ID'],
                        'quantity': int(row['quantity']),
                        'date': row['date']
                    }
                    
                    # Push to stream buffer
                    self.stream_buffer.put(stream_tuple)
                    self.rows_read += 1
                    
                    # Small delay to simulate real-time stream
                    if self.delay > 0:
                        time.sleep(self.delay)
                    
                    # Print progress every 1000 rows
                    if self.rows_read % 1000 == 0:
                        print(f"[Stream Producer] Read {self.rows_read} rows...")
        
        except FileNotFoundError:
            print(f"[Stream Producer] ERROR: File not found: {self.csv_file_path}")
        except Exception as e:
            print(f"[Stream Producer] ERROR: {str(e)}")
        finally:
            self.running = False
            print(f"[Stream Producer] Finished. Total rows: {self.rows_read}")

