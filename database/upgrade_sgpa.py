#!/usr/bin/env python3
"""
🎓 Eduvision Database SGPA Upgrade Script
Adds SGPA columns to existing students table and migrates data
"""

import mysql.connector
from mysql.connector import Error
import json
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SGPAUpgrade:
    """Upgrade existing database with SGPA functionality"""
    
    def __init__(self):
        # MySQL Connection Configuration
        mysql_password = os.environ.get('MYSQL_PASSWORD', 'uddhab123')
        
        self.config = {
            'host': 'localhost',
            'port': 3306,
            'database': 'eduvision',
            'user': 'root',
            'password': mysql_password,
            'charset': 'utf8mb4',
            'autocommit': True,
            'raise_on_warnings': False
        }
        
        self.connection = None
        self.cursor = None
    
    def connect(self):
        """Establish database connection"""
        try:
            self.connection = mysql.connector.connect(**self.config)
            self.cursor = self.connection.cursor(dictionary=True)
            logger.info("✅ Connected to MySQL database 'eduvision'")
            return True
        except Error as e:
            logger.error(f"❌ MySQL connection failed: {e}")
            return False
    
    def check_columns_exist(self):
        """Check if SGPA columns already exist"""
        try:
            query = """
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = 'eduvision' 
                AND TABLE_NAME = 'students' 
                AND COLUMN_NAME LIKE 'sgpa_%'
            """
            self.cursor.execute(query)
            existing_columns = [row['COLUMN_NAME'] for row in self.cursor.fetchall()]
            return existing_columns
        except Error as e:
            logger.error(f"Error checking columns: {e}")
            return []
    
    def add_sgpa_columns(self):
        """Add SGPA columns to students table"""
        try:
            logger.info("📋 Adding SGPA columns to students table...")
            
            # Check if columns already exist
            existing_columns = self.check_columns_exist()
            if existing_columns:
                logger.info(f"⏭️ SGPA columns already exist: {existing_columns}")
                return True
            
            # Add SGPA columns
            alter_queries = [
                "ALTER TABLE students ADD COLUMN sgpa_sem1 DECIMAL(4,2) DEFAULT NULL",
                "ALTER TABLE students ADD COLUMN sgpa_sem2 DECIMAL(4,2) DEFAULT NULL",
                "ALTER TABLE students ADD COLUMN sgpa_sem3 DECIMAL(4,2) DEFAULT NULL",
                "ALTER TABLE students ADD COLUMN sgpa_sem4 DECIMAL(4,2) DEFAULT NULL",
                "ALTER TABLE students ADD COLUMN sgpa_sem5 DECIMAL(4,2) DEFAULT NULL",
                "ALTER TABLE students ADD COLUMN sgpa_sem6 DECIMAL(4,2) DEFAULT NULL",
                "ALTER TABLE students ADD COLUMN sgpa_sem7 DECIMAL(4,2) DEFAULT NULL",
                "ALTER TABLE students ADD COLUMN sgpa_sem8 DECIMAL(4,2) DEFAULT NULL",
                "ALTER TABLE students ADD COLUMN sgpa_data JSON COMMENT 'Complete SGPA data in JSON format'",
                """ALTER TABLE students ADD COLUMN cgpa DECIMAL(4,2) GENERATED ALWAYS AS (
                    CASE 
                        WHEN sgpa_sem8 IS NOT NULL THEN (COALESCE(sgpa_sem1,0) + COALESCE(sgpa_sem2,0) + COALESCE(sgpa_sem3,0) + COALESCE(sgpa_sem4,0) + COALESCE(sgpa_sem5,0) + COALESCE(sgpa_sem6,0) + COALESCE(sgpa_sem7,0) + COALESCE(sgpa_sem8,0)) / 8
                        WHEN sgpa_sem7 IS NOT NULL THEN (COALESCE(sgpa_sem1,0) + COALESCE(sgpa_sem2,0) + COALESCE(sgpa_sem3,0) + COALESCE(sgpa_sem4,0) + COALESCE(sgpa_sem5,0) + COALESCE(sgpa_sem6,0) + COALESCE(sgpa_sem7,0)) / 7
                        WHEN sgpa_sem6 IS NOT NULL THEN (COALESCE(sgpa_sem1,0) + COALESCE(sgpa_sem2,0) + COALESCE(sgpa_sem3,0) + COALESCE(sgpa_sem4,0) + COALESCE(sgpa_sem5,0) + COALESCE(sgpa_sem6,0)) / 6
                        WHEN sgpa_sem5 IS NOT NULL THEN (COALESCE(sgpa_sem1,0) + COALESCE(sgpa_sem2,0) + COALESCE(sgpa_sem3,0) + COALESCE(sgpa_sem4,0) + COALESCE(sgpa_sem5,0)) / 5
                        WHEN sgpa_sem4 IS NOT NULL THEN (COALESCE(sgpa_sem1,0) + COALESCE(sgpa_sem2,0) + COALESCE(sgpa_sem3,0) + COALESCE(sgpa_sem4,0)) / 4
                        WHEN sgpa_sem3 IS NOT NULL THEN (COALESCE(sgpa_sem1,0) + COALESCE(sgpa_sem2,0) + COALESCE(sgpa_sem3,0)) / 3
                        WHEN sgpa_sem2 IS NOT NULL THEN (COALESCE(sgpa_sem1,0) + COALESCE(sgpa_sem2,0)) / 2
                        WHEN sgpa_sem1 IS NOT NULL THEN sgpa_sem1
                        ELSE NULL
                    END
                ) STORED""",
                "ALTER TABLE students ADD INDEX idx_cgpa (cgpa)"
            ]
            
            for query in alter_queries:
                try:
                    self.cursor.execute(query)
                    logger.info("✅ Added column/index")
                except Error as e:
                    if "Duplicate column name" in str(e) or "Duplicate key name" in str(e):
                        logger.info("⏭️ Column/index already exists, skipping")
                    else:
                        logger.error(f"❌ Error executing query: {e}")
                        return False
            
            logger.info("🎉 SGPA columns added successfully!")
            return True
            
        except Error as e:
            logger.error(f"❌ Failed to add SGPA columns: {e}")
            return False
    
    def migrate_sgpa_data(self):
        """Migrate SGPA data from JSON file to database columns"""
        try:
            logger.info("📋 Migrating SGPA data...")
            
            if not os.path.exists('details.json'):
                logger.warning("⚠️ details.json not found, skipping SGPA migration")
                return True
            
            with open('details.json', 'r') as f:
                students_data = json.load(f)
            
            updated_count = 0
            for student in students_data:
                roll_no = student.get('rollNo', '')
                sgpas = student.get('sgpas', {})
                
                if not roll_no or not sgpas:
                    continue
                
                # Prepare SGPA values for individual columns
                sgpa_values = {}
                for sem, sgpa in sgpas.items():
                    if sem.isdigit() and int(sem) <= 8:
                        try:
                            sgpa_values[f'sgpa_sem{sem}'] = float(sgpa) if sgpa else None
                        except (ValueError, TypeError):
                            sgpa_values[f'sgpa_sem{sem}'] = None
                
                # Update query
                update_query = """
                    UPDATE students SET 
                        sgpa_sem1 = %s, sgpa_sem2 = %s, sgpa_sem3 = %s, sgpa_sem4 = %s,
                        sgpa_sem5 = %s, sgpa_sem6 = %s, sgpa_sem7 = %s, sgpa_sem8 = %s,
                        sgpa_data = %s
                    WHERE roll_number = %s
                """
                
                self.cursor.execute(update_query, (
                    sgpa_values.get('sgpa_sem1'),
                    sgpa_values.get('sgpa_sem2'),
                    sgpa_values.get('sgpa_sem3'),
                    sgpa_values.get('sgpa_sem4'),
                    sgpa_values.get('sgpa_sem5'),
                    sgpa_values.get('sgpa_sem6'),
                    sgpa_values.get('sgpa_sem7'),
                    sgpa_values.get('sgpa_sem8'),
                    json.dumps(sgpas),
                    roll_no
                ))
                
                if self.cursor.rowcount > 0:
                    updated_count += 1
            
            logger.info(f"✅ Updated SGPA data for {updated_count} students")
            return True
            
        except Error as e:
            logger.error(f"❌ SGPA data migration failed: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            return False
    
    def run_upgrade(self):
        """Run complete SGPA upgrade"""
        logger.info("🚀 Starting SGPA Database Upgrade...")
        
        if not self.connect():
            return False
        
        # Add SGPA columns
        if not self.add_sgpa_columns():
            return False
        
        # Migrate SGPA data
        if not self.migrate_sgpa_data():
            return False
        
        logger.info("🎉 SGPA Database Upgrade Complete!")
        logger.info("📊 Students now have SGPA and auto-calculated CGPA!")
        
        self.disconnect()
        return True
    
    def disconnect(self):
        """Close database connection"""
        try:
            if self.cursor:
                self.cursor.close()
            if self.connection and self.connection.is_connected():
                self.connection.close()
            logger.info("🔌 Database connection closed")
        except Error as e:
            logger.error(f"Error closing connection: {e}")

if __name__ == "__main__":
    upgrade = SGPAUpgrade()
    success = upgrade.run_upgrade()
    if success:
        print("\n🎉 SUCCESS! SGPA upgrade completed successfully!")
        print("\n📋 What's been upgraded:")
        print("   ✅ Added SGPA columns (sem1-sem8) to students table")
        print("   ✅ Added JSON sgpa_data column for flexibility")
        print("   ✅ Added auto-calculated CGPA column")
        print("   ✅ Migrated existing SGPA data from JSON")
        print("   ✅ Added database indexes for performance")
    else:
        print("❌ SGPA upgrade failed. Please check the logs.")