#!/usr/bin/env python3
"""Test database path to ensure scripts use the correct database."""

import os
import sys

# Get the database path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
db_path = os.path.join(parent_dir, 'mealtrack.db')

print("📍 Database Path Test")
print("=" * 60)
print(f"Script directory: {script_dir}")
print(f"Parent directory: {parent_dir}")
print(f"Database path: {db_path}")
print(f"Database exists: {os.path.exists(db_path)}")

if os.path.exists(db_path):
    size = os.path.getsize(db_path)
    print(f"Database size: {size:,} bytes")
else:
    print("❌ Database not found at expected location!")
    print("\nLooking for mealtrack.db in parent directory...")
    
    # List files in parent directory
    files = [f for f in os.listdir(parent_dir) if f.endswith('.db')]
    if files:
        print(f"Found database files: {files}")
    else:
        print("No .db files found in parent directory")