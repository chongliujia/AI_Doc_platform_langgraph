"""
Shared state for the API components.
This module holds shared variables to avoid circular imports between routes.py and langgraph_impl.py.
"""

import os
import json
import threading

# File for persistence
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)
REQUESTS_FILE = os.path.join(DATA_DIR, "requests.json")

# Lock for thread-safe file operations
file_lock = threading.Lock()

# Dictionary to track generation progress for different requests
generation_progress = {}

# Load saved requests if file exists
try:
    with file_lock:
        if os.path.exists(REQUESTS_FILE):
            with open(REQUESTS_FILE, 'r') as f:
                document_requests = json.load(f)
        else:
            document_requests = {}
except Exception as e:
    print(f"Error loading requests data: {e}")
    document_requests = {}

# Function to save document_requests to file
def save_requests():
    try:
        with file_lock:
            with open(REQUESTS_FILE, 'w') as f:
                json.dump(document_requests, f)
    except Exception as e:
        print(f"Error saving requests data: {e}")

# Update document_requests dictionary with persistence
class PersistentDict(dict):
    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        save_requests()
    
    def update(self, *args, **kwargs):
        super().update(*args, **kwargs)
        save_requests()

# Replace the standard dict with our persistent version
if not isinstance(document_requests, PersistentDict):
    document_requests = PersistentDict(document_requests) 