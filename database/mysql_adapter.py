"""
🎓 Eduvision - MySQL Database Adapter
Replaces JSON files with MySQL database operations
"""

import mysql.connector
from mysql.connector import Error
import json
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)

class EduvisionMySQLAdapter:
    """MySQL Database Adapter for Eduvision"""
    
    def __init__(self):
        # Get password from environment or use default
        import os
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
            if self.connection and self.connection.is_connected():
                return True
                
            self.connection = mysql.connector.connect(**self.config)
            self.cursor = self.connection.cursor(dictionary=True)
            return True
        except Error as e:
            logger.error(f"MySQL connection failed: {e}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        try:
            if self.cursor:
                self.cursor.close()
            if self.connection and self.connection.is_connected():
                self.connection.close()
        except Error as e:
            logger.error(f"Error closing connection: {e}")
    
    def execute_query(self, query, params=None):
        """Execute query and return results"""
        try:
            if not self.connect():
                return None
            
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            
            if query.strip().upper().startswith(('SELECT', 'SHOW')):
                return self.cursor.fetchall()
            else:
                self.connection.commit()
                return True
                
        except Error as e:
            logger.error(f"Query execution failed: {e}")
            return None
    
    # User Management
    def authenticate_user(self, username, password):
        """Authenticate user login"""
        query = "SELECT * FROM users WHERE username = %s AND password = %s"
        result = self.execute_query(query, (username, password))
        return result[0] if result else None
    
    def get_user_sections(self, username):
        """Get sections for a user"""
        query = "SELECT sections FROM users WHERE username = %s"
        result = self.execute_query(query, (username,))
        if result:
            sections_json = result[0]['sections']
            return json.loads(sections_json) if sections_json else []
        return []
    
    # Student Management
    def get_section_students(self, section_id):
        """Get all students in a section"""
        query = """
            SELECT roll_number, name, email, mobile 
            FROM students 
            WHERE section_id = %s 
            ORDER BY roll_number
        """
        result = self.execute_query(query, (section_id,))
        return result if result else []
    
    def get_student_details(self, roll_number):
        """Get student details with SGPA and CGPA"""
        query = """
            SELECT *, 
                   sgpa_sem1, sgpa_sem2, sgpa_sem3, sgpa_sem4,
                   sgpa_sem5, sgpa_sem6, sgpa_sem7, sgpa_sem8,
                   sgpa_data, cgpa
            FROM students 
            WHERE roll_number = %s
        """
        result = self.execute_query(query, (roll_number,))
        return result[0] if result else None
    
    def get_all_students(self):
        """Get all students"""
        query = "SELECT * FROM students ORDER BY section_id, roll_number"
        return self.execute_query(query) or []
    
    # Section Management
    def get_sections(self):
        """Get all sections"""
        query = "SELECT * FROM sections ORDER BY section_name"
        result = self.execute_query(query)
        
        if result:
            sections = {}
            for section in result:
                sections[section['section_id']] = {
                    'name': section['section_name'],
                    'department': section['department'],
                    'year': section['year'],
                    'total_students': section['total_students']
                }
            return sections
        return {}
    
    # Attendance Management
    def save_attendance(self, section_id, attendance_data, subject='General', marked_by='system'):
        """Save attendance data to database"""
        try:
            attendance_date = datetime.now().date()
            records = []
            
            for roll_number, status in attendance_data.items():
                # Skip if it's online attendance marker
                if roll_number.startswith('online_'):
                    continue
                    
                attendance_status = 'present' if status == 1 else 'absent'
                records.append((
                    roll_number, section_id, subject, attendance_date,
                    attendance_status, marked_by, 'offline'
                ))
            
            if records:
                query = """
                    INSERT INTO attendance 
                    (student_roll, section_id, subject, attendance_date, status, marked_by, attendance_type)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE 
                    status = VALUES(status), marked_at = CURRENT_TIMESTAMP
                """
                
                if not self.connect():
                    return False
                    
                self.cursor.executemany(query, records)
                self.connection.commit()
                return True
            
            return False
            
        except Error as e:
            logger.error(f"Failed to save attendance: {e}")
            return False
    
    def get_attendance_by_date(self, section_id, attendance_date):
        """Get attendance for a specific date"""
        query = """
            SELECT student_roll, status 
            FROM attendance 
            WHERE section_id = %s AND attendance_date = %s
        """
        result = self.execute_query(query, (section_id, attendance_date))
        
        if result:
            attendance = {}
            for record in result:
                attendance[record['student_roll']] = 1 if record['status'] == 'present' else 0
            return attendance
        return {}
    
    def get_student_attendance_history(self, roll_number):
        """Get attendance history for a student"""
        query = """
            SELECT attendance_date, subject, status, attendance_type
            FROM attendance 
            WHERE student_roll = %s 
            ORDER BY attendance_date DESC
            LIMIT 50
        """
        return self.execute_query(query, (roll_number,)) or []
    
    # Online Session Management
    def create_online_session(self, session_data):
        """Create new online session"""
        try:
            query = """
                INSERT INTO online_sessions 
                (session_id, faculty_username, section_id, subject, class_type, 
                 duration_minutes, jitsi_link, session_data)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            result = self.execute_query(query, (
                session_data['session_id'],
                session_data['faculty_username'],
                session_data['section_id'],
                session_data['subject'],
                session_data['class_type'],
                session_data['duration_minutes'],
                session_data['jitsi_link'],
                json.dumps(session_data)
            ))
            
            return result is not None
            
        except Error as e:
            logger.error(f"Failed to create online session: {e}")
            return False
    
    def get_active_online_sessions(self, faculty_username=None):
        """Get active online sessions"""
        if faculty_username:
            query = """
                SELECT * FROM online_sessions 
                WHERE status = 'active' AND faculty_username = %s
                ORDER BY start_time DESC
            """
            result = self.execute_query(query, (faculty_username,))
        else:
            query = """
                SELECT * FROM online_sessions 
                WHERE status = 'active'
                ORDER BY start_time DESC
            """
            result = self.execute_query(query)
        
        return result if result else []
    
    def update_online_session(self, session_id, updates):
        """Update online session"""
        try:
            set_clause = ', '.join([f"{key} = %s" for key in updates.keys()])
            query = f"UPDATE online_sessions SET {set_clause} WHERE session_id = %s"
            
            params = list(updates.values()) + [session_id]
            return self.execute_query(query, params)
            
        except Error as e:
            logger.error(f"Failed to update online session: {e}")
            return False
    
    def save_online_response(self, session_id, student_roll, response_data):
        """Save online attendance response"""
        try:
            query = """
                INSERT INTO online_responses 
                (session_id, student_roll, response, response_method, participant_name, 
                 popup_question, popup_options)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            result = self.execute_query(query, (
                session_id,
                student_roll,
                response_data.get('response', ''),
                response_data.get('method', 'jitsi_popup'),
                response_data.get('participant_name', ''),
                response_data.get('question', ''),
                json.dumps(response_data.get('options', []))
            ))
            
            return result is not None
            
        except Error as e:
            logger.error(f"Failed to save online response: {e}")
            return False
    
    def get_session_responses(self, session_id):
        """Get all responses for a session"""
        query = """
            SELECT * FROM online_responses 
            WHERE session_id = %s 
            ORDER BY response_time DESC
        """
        return self.execute_query(query, (session_id,)) or []
    
    # Timetable Management
    def get_timetable(self, section_id=None):
        """Get timetable data"""
        if section_id:
            query = """
                SELECT * FROM timetable 
                WHERE section_id = %s 
                ORDER BY day_of_week, start_time
            """
            result = self.execute_query(query, (section_id,))
        else:
            query = "SELECT * FROM timetable ORDER BY section_id, day_of_week, start_time"
            result = self.execute_query(query)
        
        if result:
            timetable = {}
            for record in result:
                section = record['section_id']
                day = record['day_of_week']
                
                if section not in timetable:
                    timetable[section] = {}
                if day not in timetable[section]:
                    timetable[section][day] = []
                
                timetable[section][day].append({
                    'start_time': str(record['start_time']),
                    'end_time': str(record['end_time']),
                    'subject': record['subject'],
                    'faculty': record['faculty_name'],
                    'room': record['room_number'],
                    'type': record['class_type']
                })
            
            return timetable
        return {}
    
    # Statistics and Reports
    def get_attendance_statistics(self, section_id, start_date=None, end_date=None):
        """Get attendance statistics"""
        base_query = """
            SELECT 
                student_roll,
                COUNT(*) as total_classes,
                SUM(CASE WHEN status = 'present' THEN 1 ELSE 0 END) as present_count,
                SUM(CASE WHEN status = 'absent' THEN 1 ELSE 0 END) as absent_count,
                ROUND((SUM(CASE WHEN status = 'present' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)), 2) as percentage
            FROM attendance 
            WHERE section_id = %s
        """
        
        params = [section_id]
        
        if start_date and end_date:
            base_query += " AND attendance_date BETWEEN %s AND %s"
            params.extend([start_date, end_date])
        
        base_query += " GROUP BY student_roll ORDER BY student_roll"
        
        return self.execute_query(base_query, params) or []
    
    def get_top_performers(self, section_id=None, limit=10):
        """Get top performing students based on CGPA"""
        base_query = """
            SELECT roll_number, name, section_id, cgpa,
                   sgpa_sem1, sgpa_sem2, sgpa_sem3, sgpa_sem4,
                   sgpa_sem5, sgpa_sem6, sgpa_sem7, sgpa_sem8
            FROM students 
            WHERE cgpa IS NOT NULL
        """
        
        params = []
        if section_id:
            base_query += " AND section_id = %s"
            params.append(section_id)
        
        base_query += " ORDER BY cgpa DESC LIMIT %s"
        params.append(limit)
        
        return self.execute_query(base_query, params) or []
    
    def get_student_academic_summary(self, roll_number):
        """Get comprehensive academic summary for a student"""
        query = """
            SELECT s.*, 
                   COALESCE(att.total_classes, 0) as total_classes,
                   COALESCE(att.present_count, 0) as present_count,
                   COALESCE(att.attendance_percentage, 0) as attendance_percentage
            FROM students s
            LEFT JOIN (
                SELECT student_roll,
                       COUNT(*) as total_classes,
                       SUM(CASE WHEN status = 'present' THEN 1 ELSE 0 END) as present_count,
                       ROUND((SUM(CASE WHEN status = 'present' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)), 2) as attendance_percentage
                FROM attendance 
                GROUP BY student_roll
            ) att ON s.roll_number = att.student_roll
            WHERE s.roll_number = %s
        """
        result = self.execute_query(query, (roll_number,))
        return result[0] if result else None

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()

# Global database adapter instance
mysql_db = EduvisionMySQLAdapter()

def get_mysql_adapter():
    """Get MySQL adapter instance"""
    return mysql_db