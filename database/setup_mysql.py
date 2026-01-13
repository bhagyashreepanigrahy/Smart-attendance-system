"""
🎓 Eduvision - MySQL Database Setup & Migration Script
Converts JSON data to MySQL tables
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

class EduvisionDatabaseSetup:
    """Setup and migrate Eduvision database from JSON to MySQL"""
    
    def __init__(self):
        # MySQL Connection Configuration
        # Try to get password from environment or use empty string
        import os
        mysql_password = os.environ.get('MYSQL_PASSWORD', '')
        
        self.config = {
            'host': 'localhost',
            'port': 3306,
            'database': 'eduvision',
            'user': 'root',
            'password': mysql_password,
            'charset': 'utf8mb4',
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
            logger.info("✅ Connected to MySQL database 'eduvision'")
            return True
        except Error as e:
            logger.error(f"❌ MySQL connection failed: {e}")
            return False
    
    def create_tables(self):
        """Create all required tables for Eduvision"""
        
        tables = {
            # Users table - Faculty and Students
            'users': '''
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    user_type ENUM('faculty', 'student') NOT NULL,
                    faculty_name VARCHAR(100),
                    sections JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_username (username),
                    INDEX idx_user_type (user_type)
                )
            ''',
            
            # Sections table - Class sections
            'sections': '''
                CREATE TABLE IF NOT EXISTS sections (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    section_id VARCHAR(20) UNIQUE NOT NULL,
                    section_name VARCHAR(100) NOT NULL,
                    department VARCHAR(50) NOT NULL,
                    year VARCHAR(10) NOT NULL,
                    total_students INT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_section_id (section_id),
                    INDEX idx_department (department)
                )
            ''',
            
            # Students table - Student details with SGPA data
            'students': '''
                CREATE TABLE IF NOT EXISTS students (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    roll_number VARCHAR(20) UNIQUE NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(100),
                    mobile VARCHAR(15),
                    section_id VARCHAR(20) NOT NULL,
                    department VARCHAR(50) NOT NULL,
                    year VARCHAR(10) NOT NULL,
                    photo_path VARCHAR(255),
                    sgpa_sem1 DECIMAL(4,2) DEFAULT NULL,
                    sgpa_sem2 DECIMAL(4,2) DEFAULT NULL,
                    sgpa_sem3 DECIMAL(4,2) DEFAULT NULL,
                    sgpa_sem4 DECIMAL(4,2) DEFAULT NULL,
                    sgpa_sem5 DECIMAL(4,2) DEFAULT NULL,
                    sgpa_sem6 DECIMAL(4,2) DEFAULT NULL,
                    sgpa_sem7 DECIMAL(4,2) DEFAULT NULL,
                    sgpa_sem8 DECIMAL(4,2) DEFAULT NULL,
                    sgpa_data JSON COMMENT 'Complete SGPA data in JSON format for flexibility',
                    cgpa DECIMAL(4,2) GENERATED ALWAYS AS (
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
                    ) STORED,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_roll_number (roll_number),
                    INDEX idx_section_id (section_id),
                    INDEX idx_department (department),
                    INDEX idx_cgpa (cgpa),
                    FOREIGN KEY (section_id) REFERENCES sections(section_id) ON DELETE CASCADE
                )
            '''
            
            # Attendance table - Daily attendance records
            'attendance': '''
                CREATE TABLE IF NOT EXISTS attendance (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    student_roll VARCHAR(20) NOT NULL,
                    section_id VARCHAR(20) NOT NULL,
                    subject VARCHAR(100) NOT NULL,
                    attendance_date DATE NOT NULL,
                    status ENUM('present', 'absent') NOT NULL,
                    marked_by VARCHAR(50) NOT NULL,
                    attendance_type ENUM('offline', 'online') NOT NULL DEFAULT 'offline',
                    session_id VARCHAR(100),
                    response_time TIMESTAMP NULL,
                    marked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_student_date (student_roll, attendance_date),
                    INDEX idx_section_date (section_id, attendance_date),
                    INDEX idx_session_id (session_id),
                    INDEX idx_attendance_type (attendance_type),
                    UNIQUE KEY unique_attendance (student_roll, section_id, subject, attendance_date),
                    FOREIGN KEY (student_roll) REFERENCES students(roll_number) ON DELETE CASCADE,
                    FOREIGN KEY (section_id) REFERENCES sections(section_id) ON DELETE CASCADE
                )
            ''',
            
            # Online sessions table - Virtual class sessions
            'online_sessions': '''
                CREATE TABLE IF NOT EXISTS online_sessions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    session_id VARCHAR(100) UNIQUE NOT NULL,
                    faculty_username VARCHAR(50) NOT NULL,
                    section_id VARCHAR(20) NOT NULL,
                    subject VARCHAR(100) NOT NULL,
                    class_type ENUM('lecture', 'tutorial', 'practical', 'seminar') DEFAULT 'lecture',
                    duration_minutes INT NOT NULL,
                    jitsi_link VARCHAR(500) NOT NULL,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_time TIMESTAMP NULL,
                    status ENUM('active', 'completed', 'cancelled') DEFAULT 'active',
                    total_students INT DEFAULT 0,
                    present_students INT DEFAULT 0,
                    session_data JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_session_id (session_id),
                    INDEX idx_faculty (faculty_username),
                    INDEX idx_section_id (section_id),
                    INDEX idx_status (status),
                    INDEX idx_start_time (start_time),
                    FOREIGN KEY (section_id) REFERENCES sections(section_id) ON DELETE CASCADE
                )
            ''',
            
            # Online attendance responses - Popup responses
            'online_responses': '''
                CREATE TABLE IF NOT EXISTS online_responses (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    session_id VARCHAR(100) NOT NULL,
                    student_roll VARCHAR(20) NOT NULL,
                    response VARCHAR(50) NOT NULL,
                    response_method VARCHAR(50) DEFAULT 'jitsi_popup',
                    participant_name VARCHAR(100),
                    response_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    popup_question TEXT,
                    popup_options JSON,
                    INDEX idx_session_id (session_id),
                    INDEX idx_student_roll (student_roll),
                    INDEX idx_response_time (response_time),
                    FOREIGN KEY (session_id) REFERENCES online_sessions(session_id) ON DELETE CASCADE,
                    FOREIGN KEY (student_roll) REFERENCES students(roll_number) ON DELETE CASCADE
                )
            ''',
            
            # Timetable table - Class schedules
            'timetable': '''
                CREATE TABLE IF NOT EXISTS timetable (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    section_id VARCHAR(20) NOT NULL,
                    day_of_week ENUM('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday') NOT NULL,
                    start_time TIME NOT NULL,
                    end_time TIME NOT NULL,
                    subject VARCHAR(100) NOT NULL,
                    faculty_name VARCHAR(100) NOT NULL,
                    room_number VARCHAR(20),
                    class_type VARCHAR(20) DEFAULT 'lecture',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_section_day (section_id, day_of_week),
                    INDEX idx_start_time (start_time),
                    FOREIGN KEY (section_id) REFERENCES sections(section_id) ON DELETE CASCADE
                )
            '''
        }
        
        try:
            for table_name, create_sql in tables.items():
                logger.info(f"Creating table: {table_name}")
                self.cursor.execute(create_sql)
                logger.info(f"✅ Table '{table_name}' created successfully")
            
            logger.info("🎉 All tables created successfully!")
            return True
            
        except Error as e:
            logger.error(f"❌ Table creation failed: {e}")
            return False
    
    def migrate_json_data(self):
        """Migrate data from JSON files to MySQL tables"""
        
        try:
            # 1. Migrate Users data
            logger.info("📋 Migrating users data...")
            if os.path.exists('users.json'):
                with open('users.json', 'r') as f:
                    users_data = json.load(f)
                
                for username, user_info in users_data.items():
                    query = """
                        INSERT IGNORE INTO users (username, password, user_type, faculty_name, sections) 
                        VALUES (%s, %s, %s, %s, %s)
                    """
                    sections_json = json.dumps(user_info.get('sections', []))
                    self.cursor.execute(query, (
                        username,
                        user_info.get('password', ''),
                        user_info.get('type', 'faculty'),
                        user_info.get('faculty_name', username),
                        sections_json
                    ))
                logger.info("✅ Users data migrated")
            
            # 2. Create sections from existing data
            logger.info("📋 Creating sections...")
            sections_data = {
                'CSE_DS': {'name': 'CSE DS', 'department': 'CSE', 'year': '2023'},
                'CSEAIML_A': {'name': 'CSE AIML-A', 'department': 'CSE', 'year': '2023'},
                'CSEAIML_B': {'name': 'CSE AIML-B', 'department': 'CSE', 'year': '2023'},
                'CSEAIML_C': {'name': 'CSE AIML-C', 'department': 'CSE', 'year': '2023'}
            }
            
            for section_id, section_info in sections_data.items():
                query = """
                    INSERT IGNORE INTO sections (section_id, section_name, department, year) 
                    VALUES (%s, %s, %s, %s)
                """
                self.cursor.execute(query, (
                    section_id,
                    section_info['name'],
                    section_info['department'],
                    section_info['year']
                ))
            logger.info("✅ Sections created")
            
            # 3. Migrate Students data
            logger.info("📋 Migrating students data...")
            if os.path.exists('details.json'):
                with open('details.json', 'r') as f:
                    students_data = json.load(f)
                
                for student in students_data:
                    # Determine section based on roll number
                    roll = student.get('rollNo', '')
                    section_id = 'CSE_DS'  # Default
                    
                    if 'CSEAIML' in roll or 'AIML' in roll:
                        # Extract number part to determine section
                        import re
                        numbers = re.findall(r'\d+', roll)
                        if numbers:
                            num = int(numbers[-1])  # Get last number
                            if num <= 64:
                                section_id = 'CSEAIML_A'
                            elif num <= 128:
                                section_id = 'CSEAIML_B'
                            else:
                                section_id = 'CSEAIML_C'
                    elif 'CSEDS' in roll or 'DS' in roll:
                        section_id = 'CSE_DS'
                    elif 'CSE' in roll and 'AIML' not in roll and 'DS' not in roll:
                        # Regular CSE students
                        section_id = 'CSE_DS'
                    
                    # Extract SGPA data
                    sgpas = student.get('sgpas', {})
                    sgpa_values = {}
                    
                    # Convert SGPA data to individual semester values
                    for sem, sgpa in sgpas.items():
                        if sem.isdigit() and int(sem) <= 8:
                            try:
                                sgpa_values[f'sgpa_sem{sem}'] = float(sgpa) if sgpa else None
                            except (ValueError, TypeError):
                                sgpa_values[f'sgpa_sem{sem}'] = None
                    
                    query = """
                        INSERT IGNORE INTO students (
                            roll_number, name, email, mobile, section_id, department, year,
                            sgpa_sem1, sgpa_sem2, sgpa_sem3, sgpa_sem4, 
                            sgpa_sem5, sgpa_sem6, sgpa_sem7, sgpa_sem8, sgpa_data
                        ) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    self.cursor.execute(query, (
                        student.get('rollNo', ''),
                        student.get('name', ''),
                        student.get('email', ''),
                        student.get('mobile', ''),
                        section_id,
                        'CSE',
                        '2023',
                        sgpa_values.get('sgpa_sem1'),
                        sgpa_values.get('sgpa_sem2'),
                        sgpa_values.get('sgpa_sem3'),
                        sgpa_values.get('sgpa_sem4'),
                        sgpa_values.get('sgpa_sem5'),
                        sgpa_values.get('sgpa_sem6'),
                        sgpa_values.get('sgpa_sem7'),
                        sgpa_values.get('sgpa_sem8'),
                        json.dumps(sgpas) if sgpas else None
                    ))
                logger.info("✅ Students data migrated")
            
            # 4. Migrate Attendance data
            logger.info("📋 Migrating attendance data...")
            if os.path.exists('attendance.json'):
                with open('attendance.json', 'r') as f:
                    attendance_data = json.load(f)
                
                # First, get list of existing students to avoid foreign key errors
                existing_students_query = "SELECT roll_number FROM students"
                self.cursor.execute(existing_students_query)
                existing_students = set(row['roll_number'] for row in self.cursor.fetchall())
                
                attendance_records = []
                for section_id, dates in attendance_data.items():
                    for date_str, students in dates.items():
                        for student_roll, status in students.items():
                            # Skip online attendance entries (they'll be handled separately)
                            if student_roll.startswith('online_'):
                                continue
                            
                            # Only add attendance for students that exist in the database
                            if student_roll in existing_students:
                                attendance_records.append((
                                    student_roll,
                                    section_id,
                                    'General',  # Default subject
                                    date_str,
                                    'present' if status == 1 else 'absent',
                                    'system',  # Default marked by
                                    'offline'
                                ))
                
                if attendance_records:
                    query = """
                        INSERT IGNORE INTO attendance 
                        (student_roll, section_id, subject, attendance_date, status, marked_by, attendance_type) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """
                    self.cursor.executemany(query, attendance_records)
                    logger.info(f"✅ {len(attendance_records)} attendance records migrated")
                else:
                    logger.info("⚠️ No valid attendance records found to migrate")
            
            # 5. Migrate Online Sessions data
            logger.info("📋 Migrating online sessions data...")
            if os.path.exists('online_sessions.json'):
                with open('online_sessions.json', 'r') as f:
                    sessions_data = json.load(f)
                
                for session_id, session_info in sessions_data.items():
                    query = """
                        INSERT IGNORE INTO online_sessions 
                        (session_id, faculty_username, section_id, subject, class_type, duration_minutes, 
                         jitsi_link, start_time, status, session_data) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    self.cursor.execute(query, (
                        session_id,
                        session_info.get('faculty_username', ''),
                        session_info.get('section_id', ''),
                        session_info.get('subject', ''),
                        session_info.get('class_type', 'lecture'),
                        session_info.get('duration_minutes', 90),
                        session_info.get('jitsi_link', ''),
                        session_info.get('start_time', datetime.now()),
                        session_info.get('status', 'active'),
                        json.dumps(session_info)
                    ))
                logger.info("✅ Online sessions data migrated")
            
            # 6. Migrate Timetable data
            logger.info("📋 Migrating timetable data...")
            if os.path.exists('timetable.json'):
                with open('timetable.json', 'r') as f:
                    timetable_data = json.load(f)
                
                for section_id, schedule in timetable_data.items():
                    for day, slots in schedule.items():
                        for slot in slots:
                            query = """
                                INSERT IGNORE INTO timetable 
                                (section_id, day_of_week, start_time, end_time, subject, faculty_name, room_number) 
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """
                            self.cursor.execute(query, (
                                section_id,
                                day,
                                slot.get('start_time', '09:00'),
                                slot.get('end_time', '10:00'),
                                slot.get('subject', ''),
                                slot.get('faculty', ''),
                                slot.get('room', '')
                            ))
                logger.info("✅ Timetable data migrated")
            
            logger.info("🎉 All data migration completed successfully!")
            return True
            
        except Error as e:
            logger.error(f"❌ Data migration failed: {e}")
            return False
        except FileNotFoundError as e:
            logger.warning(f"⚠️ File not found: {e} - Skipping...")
            return True
        except Exception as e:
            logger.error(f"❌ Unexpected error during migration: {e}")
            return False
    
    def run_setup(self, skip_table_creation=False):
        """Run complete database setup and migration"""
        logger.info("🚀 Starting Eduvision MySQL Database Setup...")
        
        if not self.connect():
            return False
        
        # Create tables (skip if requested)
        if not skip_table_creation:
            if not self.create_tables():
                # If table creation fails, try to continue with migration
                logger.warning("⚠️ Table creation failed, attempting to continue with migration...")
        else:
            logger.info("⏭️ Skipping table creation as requested")
        
        # Migrate data
        if not self.migrate_json_data():
            return False
        
        # Update student counts in sections
        self.update_section_counts()
        
        logger.info("✅ Eduvision MySQL Database Setup Complete!")
        logger.info("🎯 You can now use MySQL Workbench to view and manage your data")
        
        self.disconnect()
        return True
    
    def update_section_counts(self):
        """Update student counts in sections table"""
        try:
            query = """
                UPDATE sections s 
                SET total_students = (
                    SELECT COUNT(*) FROM students st WHERE st.section_id = s.section_id
                )
            """
            self.cursor.execute(query)
            logger.info("✅ Section student counts updated")
        except Error as e:
            logger.error(f"❌ Failed to update section counts: {e}")
    
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
    # Run the setup
    setup = EduvisionDatabaseSetup()
    setup.run_setup()