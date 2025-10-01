#!/usr/bin/env python3
"""
Database creation and migration script.
This script creates the database tables using SQLAlchemy directly.
"""

from app.database import create_tables, drop_tables, engine
from app.models import Base
import os


def main():
    print("Creating database tables...")
    
    # Get the database URL
    db_url = os.getenv("DATABASE_URL", "postgresql+psycopg://autograde_user:autograde_pass@localhost:5432/autograde")
    print(f"Database URL: {db_url}")
    
    try:
        # Create all tables
        create_tables()
        print("✅ Database tables created successfully!")
        
        # Print table names
        print("\nCreated tables:")
        for table_name in Base.metadata.tables.keys():
            print(f"  - {table_name}")
            
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False
        
    return True


if __name__ == "__main__":
    main()