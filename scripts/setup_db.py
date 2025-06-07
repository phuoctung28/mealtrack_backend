#!/usr/bin/env python3
"""
Database setup script.

This script initializes the MySQL database for the application.
"""

import logging
import os
import sys

import mysql.connector
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def setup_database():
    """Create MySQL database and user for the application."""
    load_dotenv()
    
    # Get database configuration from environment
    mysql_root_password = os.getenv("MYSQL_ROOT_PASSWORD", "")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "3306")
    db_name = os.getenv("DB_NAME", "mealtrack")
    db_user = os.getenv("DB_USER", "mealtrack_user")
    db_password = os.getenv("DB_PASSWORD", "mealtrack_password")
    
    try:
        # Connect to MySQL as root
        conn = mysql.connector.connect(
            host=db_host,
            port=db_port,
            user="root",
            password=mysql_root_password
        )
        cursor = conn.cursor()
        
        # Create database if it doesn't exist
        logger.info(f"Creating database '{db_name}' if it doesn't exist...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        
        # Create user if it doesn't exist (MySQL 8.0+ syntax)
        logger.info(f"Creating user '{db_user}' if it doesn't exist...")
        try:
            cursor.execute(f"CREATE USER IF NOT EXISTS '{db_user}'@'%' IDENTIFIED BY '{db_password}'")
        except mysql.connector.Error:
            # For MySQL 5.7 or earlier
            cursor.execute(f"SELECT user FROM mysql.user WHERE user = '{db_user}'")
            if not cursor.fetchone():
                cursor.execute(f"CREATE USER '{db_user}'@'%' IDENTIFIED BY '{db_password}'")
        
        # Grant privileges
        logger.info(f"Granting privileges to '{db_user}'...")
        cursor.execute(f"GRANT ALL PRIVILEGES ON {db_name}.* TO '{db_user}'@'%'")
        cursor.execute("FLUSH PRIVILEGES")
        
        logger.info("Database setup completed successfully!")
        
    except mysql.connector.Error as err:
        logger.error(f"Error: {err}")
        sys.exit(1)
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    setup_database() 