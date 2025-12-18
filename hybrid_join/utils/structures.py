"""
Data Structures for HYBRIDJOIN Algorithm
=========================================
This module implements:
1. Hash Table (Multi-map with 10,000 slots)
2. Queue (Doubly Linked List for FIFO with random deletion)
3. Queue Node (for doubly linked list)
"""


class QueueNode:
    """Node for doubly linked list queue"""
    
    def __init__(self, key, data=None):
        self.key = key  # Join attribute value (e.g., Customer_ID or Product_ID)
        self.data = data  # Reference to hash table entry
        self.prev = None
        self.next = None


class Queue:
    """
    Doubly Linked List Queue for FIFO order with efficient random deletion
    Tracks the order of arrival for fairness in processing
    """
    
    def __init__(self):
        self.head = None  # Oldest node (front)
        self.tail = None  # Newest node (rear)
        self.size = 0
    
    def enqueue(self, key, data=None):
        """Add a new node to the rear of the queue"""
        new_node = QueueNode(key, data)
        
        if self.tail is None:
            # First node
            self.head = new_node
            self.tail = new_node
        else:
            # Add to rear
            new_node.prev = self.tail
            self.tail.next = new_node
            self.tail = new_node
        
        self.size += 1
        return new_node
    
    def dequeue(self):
        """Remove and return the oldest node (front)"""
        if self.head is None:
            return None
        
        node = self.head
        
        if self.head == self.tail:
            # Only one node
            self.head = None
            self.tail = None
        else:
            # Remove from front
            self.head = self.head.next
            self.head.prev = None
        
        self.size -= 1
        return node
    
    def remove_node(self, node):
        """Remove a specific node from anywhere in the queue (O(1) operation)"""
        if node is None:
            return
        
        if node.prev is not None:
            node.prev.next = node.next
        else:
            # Node is head
            self.head = node.next
        
        if node.next is not None:
            node.next.prev = node.prev
        else:
            # Node is tail
            self.tail = node.prev
        
        self.size -= 1
    
    def peek(self):
        """Get the oldest key without removing it"""
        if self.head is None:
            return None
        return self.head.key
    
    def is_empty(self):
        """Check if queue is empty"""
        return self.size == 0
    
    def get_size(self):
        """Get current queue size"""
        return self.size


class HashTable:
    """
    Multi-map Hash Table with 10,000 slots
    Allows multiple entries per key (collision handling via chaining)
    Each entry stores stream tuple data and a pointer to queue node
    """
    
    def __init__(self, num_slots=10000):
        self.num_slots = num_slots
        self.slots = [[] for _ in range(num_slots)]  # List of lists for chaining
        self.size = 0
    
    def _hash(self, key):
        """Hash function to map key to slot index"""
        if isinstance(key, str):
            # String key (e.g., Product_ID)
            hash_value = hash(key)
        else:
            # Integer key (e.g., Customer_ID)
            hash_value = key
        
        return abs(hash_value) % self.num_slots
    
    def insert(self, key, value, queue_node=None):
        """
        Insert a key-value pair into the hash table
        value: stream tuple data (dictionary)
        queue_node: reference to corresponding queue node
        """
        slot_index = self._hash(key)
        entry = {
            'key': key,
            'value': value,
            'queue_node': queue_node
        }
        self.slots[slot_index].append(entry)
        self.size += 1
        return entry
    
    def find(self, key):
        """Find all entries with the given key (returns list of entries)"""
        slot_index = self._hash(key)
        matches = []
        
        for entry in self.slots[slot_index]:
            if entry['key'] == key:
                matches.append(entry)
        
        return matches
    
    def remove(self, entry):
        """Remove a specific entry from the hash table"""
        if entry is None:
            return False
        
        key = entry['key']
        slot_index = self._hash(key)
        
        try:
            self.slots[slot_index].remove(entry)
            self.size -= 1
            return True
        except ValueError:
            return False
    
    def get_free_slots(self):
        """Calculate number of free slots (approximation based on load factor)"""
        # Return available capacity
        return max(0, self.num_slots - self.size)
    
    def is_full(self):
        """Check if hash table is full (all slots occupied)"""
        return self.size >= self.num_slots
    
    def get_size(self):
        """Get current number of entries"""
        return self.size
    
    def clear(self):
        """Clear all entries from hash table"""
        self.slots = [[] for _ in range(self.num_slots)]
        self.size = 0

