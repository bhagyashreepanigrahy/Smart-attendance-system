"""
🎓 Eduvision - MySQL Database Configuration
Professional Attendance Management System
"""

import mysql.connector
from mysql.connector import Error
import json
import os
from datetime import datetime, date
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MySQLConfig:
    """MySQL Database Configuration and Connection Manager"""
    
    def __init__(self):
        # MySQL Connection Configuration
        self.config = {
            'host': 'localhost',
            'port': 3306,
            'database': 'eduvision',
            'user': 'root',  # Change this to your MySQL username
            'password': 'uddhab123',  # Add your MySQL password here
            'charset': 'utf8mb4',
            'collation': 'utf8mb4_unicode_ci',
            'autocommit': True,
            'raise_on_warnings': True
        }
        
        self.connection = None
        self.cursor = None
    
    def connect(self):
        """Establish connection to MySQL database"""
        try:
            self.connection = mysql.connector.connect(**self.config)
            self.cursor = self.connection.cursor(dictionary=True)
            logger.info("✅ MySQL database connected successfully!")
            return True
        except Error as e:
            logger.error(f"❌ MySQL connection failed: {e}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        try:
            if self.cursor:
                self.cursor.close()
            if self.connection and self.connection.is_connected():
                self.connection.close()
            logger.info("🔌 MySQL connection closed")
        except Error as e:
            logger.error(f"Error closing connection: {e}")
    
    def execute_query(self, query, params=None):
        """Execute a query and return results"""
        try:
            if not self.connection or not self.connection.is_connected():
                self.connect()
            
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            
            if query.strip().upper().startswith(('SELECT', 'SHOW', 'DESCRIBE')):
                return self.cursor.fetchall()
            else:
                self.connection.commit()
                return True
                
        except Error as e:
            logger.error(f"Query execution failed: {e}")
            logger.error(f"Query: {query}")
            return False
    
    def create_database_if_not_exists(self):
        """Create the eduvision database if it doesn't exist"""
        try:
            # Connect without specifying database
            temp_config = self.config.copy()
            del temp_config['database']
            
            temp_connection = mysql.connector.connect(**temp_config)
            temp_cursor = temp_connection.cursor()
            
            # Create database
            temp_cursor.execute("CREATE DATABASE IF NOT EXISTS eduvision CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            temp_cursor.execute("USE eduvision")
            
            temp_cursor.close()
            temp_connection.close()
            
            logger.info("✅ Database 'eduvision' created/verified successfully!")
            return True
            
        except Error as e:
            logger.error(f"❌ Database creation failed: {e}")
            return False

# Global database instance
db = MySQLConfig()

def get_db_connection():
    """Get database connection instance"""
    if not db.connection or not db.connection.is_connected():
        db.connect()
    return db

def close_db_connection():
    """Close database connection"""
    db.disconnect()

# Custom JSON encoder for datetime objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)