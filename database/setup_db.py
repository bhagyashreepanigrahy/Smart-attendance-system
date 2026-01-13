#!/usr/bin/env python3
"""
🎓 Eduvision Database Setup Script
This script handles MySQL database creation and setup with password prompts
"""

import mysql.connector
from mysql.connector import Error
import getpass
import os
import sys

def create_eduvision_database():
    """Create the eduvision database if it doesn't exist"""
    print("🚀 Setting up Eduvision MySQL Database...")
    
    # Try to connect to MySQL first
    password = ""
    connection = None
    
    # Try with provided password first
    password = os.environ.get('MYSQL_PASSWORD', 'uddhab123')  # Use provided password
    
    if not password:
        # First try without password
        try:
            print("Attempting to connect to MySQL without password...")
            connection = mysql.connector.connect(
                host='localhost',
                user='root',
                password='',
                charset='utf8mb4'
            )
            print("✅ Connected to MySQL successfully (no password required)")
        except Error as e:
            if "Access denied" in str(e):
                print("❌ Access denied. MySQL root password required.")
                password = getpass.getpass("Please enter MySQL root password: ")
            else:
                print(f"❌ MySQL connection error: {e}")
                return False, password
    else:
        print(f"Using provided MySQL password...")
    
    # Try to connect with password
    if password:
        try:
            connection = mysql.connector.connect(
                host='localhost',
                user='root',
                password=password,
                charset='utf8mb4'
            )
            print("✅ Connected to MySQL successfully with password")
        except Error as e:
            print(f"❌ Failed to connect to MySQL: {e}")
            return False, password
    
    try:
        cursor = connection.cursor()
        
        # Create database if it doesn't exist
        cursor.execute("CREATE DATABASE IF NOT EXISTS eduvision")
        print("✅ Database 'eduvision' created successfully")
        
        # Grant privileges (optional, for security)
        cursor.execute("USE eduvision")
        print("✅ Switched to 'eduvision' database")
        
        cursor.close()
        connection.close()
        
        return True, password
    
    except Error as e:
        print(f"❌ Error creating database: {e}")
        if connection:
            connection.close()
        return False, password

def main():
    """Main setup function"""
    print("="*60)
    print("🎓 EDUVISION ATTENDANCE SYSTEM - DATABASE SETUP")
    print("="*60)
    
    # Step 1: Create database
    success, mysql_password = create_eduvision_database()
    if not success:
        print("❌ Database creation failed. Please check your MySQL installation and try again.")
        sys.exit(1)
    
    # Step 2: Set environment variable for password
    if mysql_password:
        os.environ['MYSQL_PASSWORD'] = mysql_password
        print(f"✅ MySQL password set in environment variable")
    
    # Step 3: Run the main setup script
    print("\n🔄 Running database table creation and data migration...")
    try:
        from setup_mysql import EduvisionDatabaseSetup
        setup = EduvisionDatabaseSetup()
        # Skip table creation since they already exist
        if setup.run_setup(skip_table_creation=True):
            print("\n🎉 SUCCESS! Eduvision database setup completed successfully!")
            print("\n📋 What's been set up:")
            print("   ✅ MySQL database 'eduvision' created")
            print("   ✅ All required tables created")
            print("   ✅ Sample data migrated from JSON files")
            print("   ✅ Indexes and foreign keys configured")
            print("\n🔧 Next steps:")
            print("   1. Start the Flask application: python app.py")
            print("   2. Access the system at http://localhost:5000")
            print("   3. Use MySQL Workbench to manage the database")
            return True
        else:
            print("❌ Database setup failed during table creation or migration.")
            return False
    except Exception as e:
        print(f"❌ Error during setup: {e}")
        return False

if __name__ == "__main__":
    main()