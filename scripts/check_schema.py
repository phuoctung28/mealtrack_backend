#!/usr/bin/env python3
"""Check database schema"""

import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'mealtrack.db')

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = cursor.fetchall()
    
    print("📊 Current Database Tables:")
    print("-" * 40)
    for table in tables:
        if not table[0].startswith('sqlite_'):
            print(f"  • {table[0]}")
    
    # Check if user tables exist
    user_tables = ['users', 'user_profiles', 'user_preferences', 'user_goals', 'tdee_calculations']
    print("\n🔍 Checking for User Tables:")
    print("-" * 40)
    for table_name in user_tables:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';")
        exists = cursor.fetchone() is not None
        status = "✅" if exists else "❌"
        print(f"  {status} {table_name}")
    
    # Check alembic version
    print("\n📌 Current Migration Version:")
    print("-" * 40)
    cursor.execute("SELECT version_num FROM alembic_version;")
    version = cursor.fetchone()
    if version:
        print(f"  Current version: {version[0]}")
    
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")