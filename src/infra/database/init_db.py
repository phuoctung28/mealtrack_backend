"""
Database initialization script.

This script creates all tables in the database based on the defined models.
"""

import logging
import os
import sys

from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import models and database config
from src.infra.database.config import engine, Base

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
    """Create database tables."""
    logger.info("Creating database tables...")
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    logger.info("Database tables created successfully!")

if __name__ == "__main__":
    load_dotenv()
    init_db() 