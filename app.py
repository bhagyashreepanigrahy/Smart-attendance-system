from flask import Flask, render_template, Response, request, jsonify, send_file, session, redirect, url_for
from flask_cors import CORS, cross_origin
import cv2
import face_recognition
import pickle
import numpy as np
import pandas as pd
import json
import re
from datetime import datetime, timedelta
from io import BytesIO
import time
import threading
from queue import Queue
import os
from functools import wraps
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

# Import MySQL adapter
try:
    from database.mysql_adapter import mysql_db
    USE_MYSQL = True
    logging.info("✅ MySQL adapter imported successfully")
except ImportError as e:
    USE_MYSQL = False
    logging.warning(f"⚠️ MySQL adapter not available: {e}. Falling back to JSON files.")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define application root directory
APP_ROOT = os.path.dirname(os.path.abspath(__file__))

# Function to test email configuration
def test_email_configuration(recipient_email=None):
    """Test the email configuration by sending a test email"""
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Test Email - Attendance System'
        msg['From'] = EMAIL_CONFIG['sender_email']
        
        # Use provided recipient email or default to sender (for testing)
        if not recipient_email:
            # Default to sender email for testing if no recipient specified
            recipient_email = EMAIL_CONFIG['sender_email']
            
        msg['To'] = recipient_email
        
        # Create email content
        text_content = "This is a test email from the Attendance System."
        html_content = """<html>
        <body>
            <h2>Email Configuration Test</h2>
            <p>This is a test email from the Attendance System.</p>
            <p>If you received this email, your email configuration is working correctly.</p>
        </body>
        </html>
        """
        
        # Attach parts
        part1 = MIMEText(text_content, 'plain')
        part2 = MIMEText(html_content, 'html')
        msg.attach(part1)
        msg.attach(part2)
        
        # Send email with improved error handling
        with smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
            server.starttls()
            server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
            server.sendmail(EMAIL_CONFIG['sender_email'], recipient_email, msg.as_string())
        
        logger.info("Test email sent successfully!")
        return True, "Test email sent successfully!"
        
    except smtplib.SMTPAuthenticationError as auth_error:
        error_msg = f"SMTP Authentication failed: {str(auth_error)}. Please check email credentials."
        logger.error(error_msg)
        return False, error_msg
        
    except Exception as e:
        error_msg = f"Failed to send test email: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

# Email configuration
EMAIL_CONFIG = {
    'sender_email': 'uddhabdas2020@gmail.com',
    'sender_password': 'xbmw txjk lbdu ebni',  # Gmail App Password
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587
}

# Define login_required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'authenticated' not in session or not session['authenticated']:
            # Return JSON 401 for API/JSON requests instead of redirecting HTML
            accepts = (request.headers.get('Accept') or '').lower()
            xrw = (request.headers.get('X-Requested-With') or '').lower()
            if request.path.startswith('/api/') or 'application/json' in accepts or xrw == 'xmlhttprequest':
                return jsonify({'error': 'Not authenticated'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

app = Flask(__name__)
app.secret_key = 'attendance-system-secret-key-2024'

# Enable CORS for all routes with credentials support
CORS(app, origins=['http://localhost:5000', 'https://meet.jit.si', 'http://meet.jit.si', 'file://', 'null'], 
     methods=['GET', 'POST', 'OPTIONS'], 
     allow_headers=['*'], 
     supports_credentials=True)
# Configure session to work across multiple tabs
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=5)  # Session lasts for 5 hours
app.config['SESSION_USE_SIGNER'] = True  # Add this for extra security

# File paths
ENCODINGS_FILE = os.path.join(APP_ROOT, "database", "encodings.pkl")
USERS_FILE = os.path.join(APP_ROOT, "database", "users.json")
DETAILS_FILE = os.path.join(APP_ROOT, "database", "details.json")
ATTENDANCE_FILE = os.path.join(APP_ROOT, "database", "attendance.json")

# Section configurations
SECTIONS = {
    "CSE_DS": {"prefix": "23CSEDS", "start": 1, "end": 60, "name": "CSE-DS"},
    "CSEAIML_A": {"prefix": "23CSEAIML", "start": 1, "end": 64, "name": "CSE AIML-A"},
    "CSEAIML_B": {"prefix": "23CSEAIML", "start": 65, "end": 128, "name": "CSE AIML-B"},
    "CSEAIML_C": {"prefix": "23CSEAIML", "start": 129, "end": 204, "name": "CSE AIML-C"}
}

# Timetable configuration - Days and subjects for each section
TIMETABLE = {
    "CSE_DS": {
        "Monday": ["Data Structures", "Python Programming", "Database Systems", "Statistics"],
        "Tuesday": ["Machine Learning", "Data Visualization", "Python Programming", "Mathematics"],
        "Wednesday": ["Database Systems", "Statistics", "Data Structures", "Communication Skills"],
        "Thursday": ["Data Visualization", "Machine Learning", "Mathematics", "Python Programming"],
        "Friday": ["Statistics", "Data Structures", "Database Systems", "Machine Learning"],
        "Saturday": ["Mathematics", "Communication Skills", "Data Visualization", "Python Programming"]
    },
    "CSEAIML_A": {
        "Monday": ["Artificial Intelligence", "Deep Learning", "Python Programming", "Mathematics"],
        "Tuesday": ["Machine Learning", "Neural Networks", "Data Structures", "Communication Skills"],
        "Wednesday": ["Deep Learning", "Mathematics", "Artificial Intelligence", "Python Programming"],
        "Thursday": ["Neural Networks", "Machine Learning", "Data Structures", "Deep Learning"],
        "Friday": ["Mathematics", "Artificial Intelligence", "Machine Learning", "Neural Networks"],
        "Saturday": ["Python Programming", "Communication Skills", "Data Structures", "Artificial Intelligence"]
    },
    "CSEAIML_B": {
        "Monday": ["Machine Learning", "Neural Networks", "Python Programming", "Mathematics"],
        "Tuesday": ["Artificial Intelligence", "Deep Learning", "Data Structures", "Communication Skills"],
        "Wednesday": ["Neural Networks", "Mathematics", "Machine Learning", "Python Programming"],
        "Thursday": ["Deep Learning", "Artificial Intelligence", "Data Structures", "Neural Networks"],
        "Friday": ["Mathematics", "Machine Learning", "Artificial Intelligence", "Deep Learning"],
        "Saturday": ["Python Programming", "Communication Skills", "Data Structures", "Machine Learning"]
    },
    "CSEAIML_C": {
        "Monday": ["Deep Learning", "Artificial Intelligence", "Python Programming", "Mathematics"],
        "Tuesday": ["Neural Networks", "Machine Learning", "Data Structures", "Communication Skills"],
        "Wednesday": ["Artificial Intelligence", "Mathematics", "Deep Learning", "Python Programming"],
        "Thursday": ["Machine Learning", "Neural Networks", "Data Structures", "Artificial Intelligence"],
        "Friday": ["Mathematics", "Deep Learning", "Neural Networks", "Machine Learning"],
        "Saturday": ["Python Programming", "Communication Skills", "Data Structures", "Deep Learning"]
    }
}

# Global variables for camera processing
camera_processor = None
present_students = set()
attendance_started = False

# Add route for enhanced dashboard
@app.route('/enhanced_dashboard')
@login_required
def enhanced_dashboard():
    """Enhanced attendance dashboard with MySQL integration"""
    return render_template('enhanced_dashboard.html')

# Import for SGPA graph
try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    logger.warning("Plotly not available. SGPA graphs will be disabled.")

# Declare global variable first to avoid scope issues
global online_attendance

# Import online attendance module with AGGRESSIVE forced reload
try:
    # STEP 1: Clear module from sys.modules completely
    import sys
    modules_to_reload = ['online_attendance', 'jitsi_config']
    for module_name in modules_to_reload:
        if module_name in sys.modules:
            del sys.modules[module_name]
            logger.info(f"🗑️ Removed {module_name} from sys.modules")
    
    # STEP 2: Force fresh import
    logger.info("🔄 Starting FRESH import of online_attendance module...")
    from online_attendance import OnlineAttendanceManager
    
    # Initialize online attendance manager
    online_attendance = OnlineAttendanceManager(APP_ROOT)
    logger.info("Online attendance system initialized successfully")
    logger.info(f"✅ Global online_attendance variable type: {type(online_attendance)}")
    
    # Debug: Check if create_online_session method exists with ENHANCED validation
    logger.info(f"🔍 OnlineAttendanceManager object type: {type(online_attendance)}")
    logger.info(f"🔍 Available methods: {[m for m in dir(online_attendance) if not m.startswith('_')]}")
    
    if hasattr(online_attendance, 'create_online_session'):
        logger.info("🎉 ✅ create_online_session method IS AVAILABLE!")
        # Test method signature
        import inspect
        sig = inspect.signature(online_attendance.create_online_session)
        logger.info(f"📝 Method signature: {sig}")
        
        # Quick test to ensure it works
        try:
            test_result = online_attendance.create_online_session(
                'test_faculty', 'CSE_DS', 'Test Subject', 'lecture', 90, 'https://meet.jit.si/test'
            )
            logger.info(f"🎉 ✅ METHOD TEST SUCCESSFUL! Session ID: {test_result[0]}")
            logger.info("🚀 ONLINE ATTENDANCE IS FULLY FUNCTIONAL!")
        except Exception as test_error:
            logger.error(f"💥 ❌ Method test failed: {test_error}")
    else:
        logger.error("💥 ❌ create_online_session method STILL NOT AVAILABLE!")
        logger.error("🔧 This means the module reload didn't work properly.")
        
except ImportError as e:
    logger.error(f"Failed to import online attendance module: {e}")
    online_attendance = None
except Exception as e:
    logger.error(f"Failed to initialize online attendance: {e}")
    online_attendance = None

def send_absence_emails_to_students(absent_students, section, date_str):
    """Send absence notification emails to students who missed class"""
    try:
        # Get current day and subject information
        current_date = datetime.strptime(date_str, '%Y-%m-%d')
        day_name = current_date.strftime('%A')
        
        # Get subjects for this day from timetable
        subjects = TIMETABLE.get(section, {}).get(day_name, ['Class'])
        current_subject = subjects[0] if subjects else 'Class'  # Get first subject or default
        section_name = SECTIONS[section]['name']
        
        # Get student details
        student_details = load_student_details()
        student_map = {student['rollNo']: student for student in student_details}
        
        emails_sent = 0
        for student_roll in absent_students:
            student_info = student_map.get(student_roll, {
                'rollNo': student_roll,
                'name': f'Student {student_roll}',
                'mobile': 'N/A',
                'sgpas': {}
            })
            
            # Calculate student's attendance percentage
            attendance_percentage = calculate_attendance_percentage(student_roll)
            daily_attendance = get_student_daily_attendance(student_roll)
            
            total_classes = sum(day["total_classes"] for day in daily_attendance)
            classes_attended = sum(day["classes_attended"] for day in daily_attendance)
            missed_classes = total_classes - classes_attended + 1  # +1 for today's absence
            
            # Calculate classes needed to reach 80%
            classes_to_80 = 0
            if attendance_percentage < 80 and total_classes > 0:
                classes_to_80 = max(0, int((0.8 * (total_classes + 1) - classes_attended) / 0.2) + 1)
            
            # Get academic performance data
            sgpas = student_info.get('sgpas', {})
            latest_sgpa = 'N/A'
            if sgpas:
                # Get the latest semester SGPA
                latest_semester = max([int(sem) for sem in sgpas.keys() if sem.isdigit()], default=0)
                if latest_semester > 0:
                    latest_sgpa = sgpas.get(str(latest_semester), 'N/A')
            
            # Calculate CGPA
            cgpa = calculate_cgpa(sgpas)
            
            # Send email
            success = send_attendance_email(
                student_roll, 
                student_info['name'], 
                attendance_percentage, 
                classes_attended, 
                total_classes + 1,  # Include today's class
                classes_to_80,
                missed_classes,
                current_subject,
                section_name,
                latest_sgpa,
                cgpa
            )
            
            if success:
                emails_sent += 1
        
        logger.info(f"Sent absence emails to {emails_sent} out of {len(absent_students)} absent students")
        return emails_sent
        
    except Exception as e:
        logger.error(f"Error sending absence emails: {str(e)}")
        return 0

def calculate_cgpa(sgpas):
    """Calculate CGPA from available SGPA data"""
    if not sgpas:
        return 'N/A'
    
    total_sgpa = 0
    count = 0
    
    for semester, sgpa in sgpas.items():
        try:
            sgpa_value = float(sgpa)
            total_sgpa += sgpa_value
            count += 1
        except (ValueError, TypeError):
            # Skip invalid SGPA values
            continue
    
    if count == 0:
        return 'N/A'
    
    return round(total_sgpa / count, 2)

def get_cgpa_feedback_html(cgpa):
    """Generate HTML feedback based on CGPA value"""
    try:
        if cgpa == 'N/A' or not cgpa:
            return ''
            
        cgpa_value = float(cgpa) if isinstance(cgpa, str) else cgpa
        
        if cgpa_value >= 9.0:
            color = "#28a745"  # Green
            message = "Outstanding Performance! You're among the top performers in your class."
            advice = "Keep up the excellent work and consider exploring research opportunities or advanced coursework."
        elif cgpa_value >= 8.0:
            color = "#17a2b8"  # Blue
            message = "Excellent Performance! You're doing very well academically."
            advice = "Continue your strong academic efforts and consider mentoring other students."
        elif cgpa_value >= 7.0:
            color = "#ffc107"  # Yellow
            message = "Good Performance. You're on the right track."
            advice = "Focus on improving in challenging areas and maintain consistent study habits."
        else:
            color = "#dc3545"  # Red
            message = "Needs Improvement. Your academic performance requires attention."
            advice = "Consider seeking additional academic support, tutoring, or study groups to boost your performance."
        
        # Create a light background color based on the main color
        bg_color = f"rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.1)"
        
        html = f"""
        <div style="margin-top: 15px; padding: 10px; border-left: 4px solid {color}; background-color: {bg_color};">
            <h4 style="color: {color}; margin-top: 0;">Academic Performance Feedback</h4>
            <p><strong>{message}</strong></p>
            <p>{advice}</p>
        </div>
        """
        return html
    except Exception as e:
        logger.error(f"Error generating CGPA feedback: {str(e)}")
        return ''

def send_attendance_email(student_roll, student_name, attendance_percentage, classes_attended, total_classes, classes_to_80, missed_classes, subject_name=None, section_name=None, sgpa=None, cgpa=None, faculty_name="Dr. Faculty Member"):
    """Send attendance email to student with enhanced messaging including academic performance and SGPA graph"""
    try:
        # Generate student email in format: rollno.studentname@giet.edu
        # Clean student name: remove ALL spaces, dots, and special characters
        if student_name:
            # Remove all non-alphabetic characters and combine into single word
            import re
            clean_name = re.sub(r'[^a-zA-Z]', '', student_name.strip())
            email_name = clean_name.lower()
        else:
            email_name = 'student'
        
        # Format student email according to GIET University format
        student_email = f"{student_roll.lower()}.{email_name}@giet.edu"
        
        # Create email content with enhanced messaging
        if subject_name:
            subject = f"Attendance and Academic Performance Reminder - {subject_name} - {student_roll}"
            absence_message = f"<p><strong>⚠️ You have missed the {subject_name} class today.</strong></p>"
        else:
            subject = f"Attendance and Academic Performance Reminder - {student_roll}"
            absence_message = "<p><strong>⚠️ You have been marked absent for today's classes.</strong></p>"
            
        # If subject name is not provided, try to determine it from the context
        subject_display = subject_name if subject_name else "your courses"
        
        # Get current date and day
        current_date = datetime.now()
        day_name = current_date.strftime('%A')
        
        # Use provided faculty name or default
        teacher_name = faculty_name
        
        # Institution name
        institution_name = "GIET University"
        
        # Generate SGPA graph
        sgpa_graph_html = ''
        # Initialize variables
        sgpa_table_rows = ""
        student_sgpas = {}
        
        try:
            # Use the provided sgpa and cgpa parameters instead of fetching again
            # This avoids the 'tuple' object has no attribute 'get' error
            if sgpa and cgpa:
                logger.info(f"Using provided SGPA and CGPA for {student_roll}")
                # Get student details to access all SGPAs
                student_details = load_student_details()
                student_info = next((s for s in student_details if s['rollNo'] == student_roll), None)
                
                if student_info and 'sgpas' in student_info and student_info['sgpas']:
                    student_sgpas = student_info['sgpas']
            else:
                logger.warning(f"Missing SGPA or CGPA for {student_roll}, fetching from student details")
                # Get student details to access all SGPAs as fallback
                student_details = load_student_details()
                student_info = next((s for s in student_details if s['rollNo'] == student_roll), None)
                
                if student_info and 'sgpas' in student_info and student_info['sgpas']:
                    # Use the sgpas from student_info
                    student_sgpas = student_info['sgpas']
            
            # Generate SGPA table rows
            if isinstance(student_sgpas, dict):
                for semester, semester_sgpa in sorted(student_sgpas.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0):
                    # Determine row color based on SGPA value
                    row_color = "#ffffff"
                    try:
                        sgpa_value = float(semester_sgpa)
                        if sgpa_value >= 8.5:
                            row_color = "#d4edda"  # Light green for excellent
                        elif sgpa_value >= 7.5:
                            row_color = "#d1ecf1"  # Light blue for good
                        elif sgpa_value >= 6.5:
                            row_color = "#fff3cd"  # Light yellow for average
                        else:
                            row_color = "#f8d7da"  # Light red for below average
                    except (ValueError, TypeError):
                        pass
                    
                    sgpa_table_rows += f"<tr style=\"background-color: {row_color};\"><td style=\"padding: 8px; text-align: left; border: 1px solid #ddd;\">Semester {semester}</td><td style=\"padding: 8px; text-align: left; border: 1px solid #ddd;\">{semester_sgpa}</td></tr>\n"
            
            # Create SGPA graph
            sgpa_graph_html = create_enhanced_sgpa_graph(student_sgpas)
        except Exception as e:
            logger.error(f"Error generating SGPA graph for email: {str(e)}")
            sgpa_graph_html = ""
        
        # HTML email template with enhanced messaging
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #2c3e50; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background-color: #f9f9f9; padding: 20px; border-radius: 0 0 5px 5px; }}
                .stats {{ background-color: #e8f4f8; padding: 15px; border-radius: 5px; margin: 15px 0; }}
                .academic {{ background-color: #e6f7ff; padding: 15px; border-radius: 5px; margin: 15px 0; border-left: 4px solid #1890ff; }}
                .warning {{ background-color: #fff3cd; padding: 15px; border-radius: 5px; margin: 15px 0; border-left: 4px solid #ffc107; }}
                .critical {{ background-color: #f8d7da; padding: 15px; border-radius: 5px; margin: 15px 0; border-left: 4px solid #dc3545; }}
                .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #777; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📚 Attendance and Academic Performance Reminder</h1>
                    <p>{institution_name} - Department of Computer Science</p>
                </div>
                
                <div class="content">
                    <h2>Dear {student_name},</h2>
                    <p>This is to inform you regarding your attendance and academic performance in {subject_display} under the guidance of {teacher_name}.</p>
                    
                    <div class="academic">
                        <h3>🎓 Your Academic Record</h3>
                        <div>
                            <h4>Semester-wise Performance</h4>
                            <table style="width:100%; border-collapse: collapse; margin-bottom: 15px;">
                                <tr style="background-color: #1890ff; color: white;">
                                    <th style="padding: 8px; text-align: left; border: 1px solid #ddd;">Semester</th>
                                    <th style="padding: 8px; text-align: left; border: 1px solid #ddd;">SGPA</th>
                                </tr>
                                {sgpa_table_rows}
                            </table>
                        </div>
                        <p><strong>CGPA:</strong> {cgpa}</p>
                        {sgpa_graph_html}
                        {get_cgpa_feedback_html(cgpa) if isinstance(cgpa, (float, int, str)) else ''}
                    </div>
                    
                    <div class="stats">
                        <h3>📊 Your Attendance Summary</h3>
                        <p><strong>Roll Number:</strong> {student_roll}</p>
                        <p><strong>Classes Attended:</strong> {classes_attended} out of {total_classes}</p>
                        <p><strong>Current Attendance:</strong> {attendance_percentage}%</p>
                        <p><strong>Total Missed Classes:</strong> {missed_classes}</p>
                    </div>
        """
        
        if attendance_percentage < 80:
            html_content += f"""
                    <div class="critical">
                        <h3>🚨 CRITICAL: Low Attendance Warning</h3>
                        <p><strong>Your attendance is currently {attendance_percentage}%, which is below the required 80% minimum.</strong></p>
                        <p>📈 <strong>Action Required:</strong> You must attend <strong>{classes_to_80} more consecutive classes</strong> to avoid being detained.</p>
                        <p>⚡ <strong>Important:</strong> Students with less than 80% attendance may not be allowed to sit for examinations as per university guidelines.</p>
                        <p>💡 <strong>Recommendation:</strong> We strongly advise you to stay regular, avoid missing lectures unnecessarily, and stay focused on your studies. Consistent attendance is essential not only for fulfilling the eligibility criteria but also for better understanding of the subject.</p>
                        <p>Your sincerity and discipline will play a vital role in improving both your academic performance and overall success.</p>
                    </div>
            """
        else:
            html_content += """
                    <div style="background-color: #d4edda; padding: 15px; border-radius: 5px; margin: 15px 0; border-left: 4px solid #28a745;">
                        <h3>✅ Good Attendance</h3>
                        <p>Your attendance is satisfactory. Keep up the good work!</p>
                    </div>
            """
        
        html_content += f"""
                    <p>If you have any questions regarding your attendance or academic performance, please contact your faculty advisor.</p>
                    
                    <p>Regards,<br>
                    {teacher_name}<br>
                    Faculty Member<br>
                    {institution_name}</p>
                    
                    <div class="footer">
                        <p>This is an automated message. Please do not reply to this email.</p>
                        <p>© {datetime.now().year} {institution_name} - AI Attendance System</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain text version for email clients that don't support HTML
        text_content = f"""
        Subject: Attendance and Academic Performance Reminder - {student_roll}
        
        Dear {student_name},
        
        This is to inform you regarding your attendance and academic performance in {subject_display} under the guidance of {teacher_name}.
        
        Your academic record so far:
        
        SGPA: {sgpa}
        
        CGPA: {cgpa}
        
        Current Attendance: {attendance_percentage}%
        
        Attendance Summary:
        - Roll Number: {student_roll}
        - Classes Attended: {classes_attended} out of {total_classes}
        - Missed Classes: {missed_classes}
        """
        
        if attendance_percentage < 80:
            text_content += f"""
        
        ATTENDANCE ALERT:
        Please note that your attendance is below the required 80%. 
        To avoid being detained, you must attend at least {classes_to_80} more classes.
        
        We strongly advise you to stay regular, avoid missing lectures unnecessarily, and stay focused on your studies. 
        Consistent attendance is essential not only for fulfilling the eligibility criteria but also for better understanding of the subject.
        
        Your sincerity and discipline will play a vital role in improving both your academic performance and overall success.
            """
        else:
            text_content += """
        
        GOOD ATTENDANCE:
        Your attendance is satisfactory. Keep up the good work!
            """
        
        text_content += f"""
        
        If you have any questions regarding your attendance or academic performance, please contact your faculty advisor.
        
        Regards,
        {teacher_name}
        Faculty Member
        {institution_name}
        
        This is an automated message. Please do not reply to this email.
        © {datetime.now().year} {institution_name} - AI Attendance System
        """
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = EMAIL_CONFIG['sender_email']
        msg['To'] = student_email
        
        # Attach both HTML and plain text versions
        part1 = MIMEText(text_content, 'plain')
        part2 = MIMEText(html_content, 'html')
        
        msg.attach(part1)
        msg.attach(part2)
        
        # Send email with improved error handling
        try:
            with smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
                server.starttls()
                # Attempt login with detailed error logging
                try:
                    server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
                except smtplib.SMTPAuthenticationError as auth_error:
                    logger.error(f"SMTP Authentication failed: {str(auth_error)}. Please check email credentials.")
                    return False
                except Exception as login_error:
                    logger.error(f"SMTP Login error: {str(login_error)}")
                    return False
                
                # Attempt to send the email
                server.sendmail(EMAIL_CONFIG['sender_email'], student_email, msg.as_string())
                
            logger.info(f"Attendance email sent successfully to {student_email}")
            return True
            
        except smtplib.SMTPException as smtp_error:
            logger.error(f"SMTP Error sending email to {student_roll}: {str(smtp_error)}")
            return False
        except ConnectionError as conn_error:
            logger.error(f"Connection error while sending email to {student_roll}: {str(conn_error)}")
            return False
        except TimeoutError as timeout_error:
            logger.error(f"Timeout error while sending email to {student_roll}: {str(timeout_error)}")
            return False
        
    except Exception as e:
        logger.error(f"Failed to send email to {student_roll}: {str(e)}")
        return False

def create_enhanced_sgpa_graph(sgpas):
    """Create an enhanced SGPA graph using Plotly with comprehensive error handling and CGPA-based feedback"""
    try:
        # Check if Plotly is available and we have SGPA data
        if not PLOTLY_AVAILABLE:
            logger.warning("Plotly not available for graph generation")
            return None
            
        if not sgpas:
            logger.warning("No SGPA data provided for graph generation")
            return None
            
        # Extract semester numbers and SGPA values
        semesters = []
        sgpa_values = []
        colors = []
        
        for semester, sgpa in sgpas.items():
            if not sgpa:  # Skip empty values
                continue
                
            try:
                sgpa_value = float(sgpa)
                semesters.append(f"Semester {semester}")
                sgpa_values.append(sgpa_value)
                
                # Color based on SGPA value
                if sgpa_value >= 8.5:
                    colors.append('#28a745')  # Green for excellent
                elif sgpa_value >= 7.5:
                    colors.append('#17a2b8')  # Blue for good
                elif sgpa_value >= 6.5:
                    colors.append('#ffc107')  # Yellow for average
                else:
                    colors.append('#dc3545')  # Red for below average
            except ValueError:
                logger.warning(f"Invalid SGPA value for semester {semester}: {sgpa}")
                continue
        
        if not semesters:
            logger.warning("No valid SGPA data found for graph generation")
            return None
        
        # Create the figure with subplots
        fig = make_subplots(rows=1, cols=1, specs=[[{"type": "bar"}]])
        
        # Add bar chart
        fig.add_trace(
            go.Bar(
                x=semesters,
                y=sgpa_values,
                marker=dict(
                    color=colors,
                    line=dict(width=1.5, color='rgba(0,0,0,0.3)')
                ),
                hovertemplate='<b>%{x}</b><br>SGPA: %{y:.2f}<extra></extra>',
                name='SGPA'
            )
        )
        
        # Add a line for the trend
        fig.add_trace(
            go.Scatter(
                x=semesters,
                y=sgpa_values,
                mode='lines+markers',
                line=dict(color='rgba(0,0,0,0.7)', width=2, dash='dot'),
                marker=dict(size=8, symbol='circle', line=dict(width=2, color='rgba(0,0,0,0.7)')),
                name='Trend',
                hovertemplate='<b>%{x}</b><br>SGPA: %{y:.2f}<extra></extra>'
            )
        )
        
        # Calculate CGPA
        cgpa = sum(sgpa_values) / len(sgpa_values) if sgpa_values else 0
        
        # Add a horizontal line for CGPA with a distinctive purple color
        fig.add_shape(
            type="line",
            x0=-0.5,
            y0=cgpa,
            x1=len(semesters) - 0.5,
            y1=cgpa,
            line=dict(color="rgba(75,0,130,0.9)", width=3, dash="dash")
        )
        
        # Add annotation for CGPA with enhanced visibility
        fig.add_annotation(
            x=len(semesters) - 1,
            y=cgpa,
            text=f"CGPA: {cgpa:.2f}",
            font=dict(size=14, color="rgba(75,0,130,1)", family="Arial, sans-serif", weight="bold"),
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="rgba(75,0,130,0.8)",
            borderwidth=2,
            borderpad=4,
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=2,
            arrowcolor="rgba(75,0,130,0.9)"
        )
        
        # Add performance feedback based on CGPA
        performance_message = ""
        if cgpa >= 9.0:
            performance_message = "<b>Outstanding Performance!</b> You're among the top performers. Keep up the excellent work!"
            message_color = "#28a745"  # Green
        elif cgpa >= 8.0:
            performance_message = "<b>Excellent Performance!</b> You're doing very well. Continue your strong academic efforts."
            message_color = "#17a2b8"  # Blue
        elif cgpa >= 7.0:
            performance_message = "<b>Good Performance.</b> You're on the right track. Focus on improving in challenging areas."
            message_color = "#ffc107"  # Yellow
        else:
            performance_message = "<b>Needs Improvement.</b> Consider seeking additional academic support to boost your performance."
            message_color = "#dc3545"  # Red
            
        # Add performance message annotation at the top of the graph
        fig.add_annotation(
            x=len(semesters)/2 - 0.5,
            y=10,
            xref="x",
            yref="y",
            text=performance_message,
            font=dict(size=13, color=message_color, family="Arial, sans-serif"),
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor=message_color,
            borderwidth=2,
            borderpad=4,
            showarrow=False,
            align="center"
        )
        
        # Update layout
        fig.update_layout(
            title={
                'text': 'Semester-wise SGPA Performance',
                'y': 0.95,
                'x': 0.5,
                'xanchor': 'center',
                'yanchor': 'top'
            },
            xaxis_title="Semester",
            yaxis_title="SGPA",
            yaxis=dict(
                range=[0, 10],  # SGPA is typically on a scale of 0-10
                gridcolor='rgba(0,0,0,0.1)',
                zerolinecolor='rgba(0,0,0,0.2)'
            ),
            xaxis=dict(
                gridcolor='rgba(0,0,0,0.1)',
                zerolinecolor='rgba(0,0,0,0.2)'
            ),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            hovermode='closest',
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            margin=dict(l=60, r=30, t=80, b=60)
        )
        
        # Return the HTML representation of the figure
        return fig.to_html(full_html=False, include_plotlyjs='cdn')
        
    except Exception as e:
        logger.error(f"Error creating SGPA graph: {str(e)}")
        # Return a fallback message that will be displayed to the user
        return "<div class='alert alert-warning'>Unable to generate SGPA graph. Please try refreshing the page.</div>"

def get_student_image_url(roll_no):
    """Get student image URL"""
    return f"https://gietuerp.in/StudentDocuments/{roll_no}/{roll_no}.JPG"

def get_student_attendance_history(roll_number):
    """Get attendance history for a specific student"""
    attendance_data = load_attendance_data()
    history = {}
    
    # Find which section this student belongs to
    student_section = None
    for section_id, section_config in SECTIONS.items():
        prefix = section_config["prefix"]
        try:
            roll_num = int(roll_number[len(prefix):]) if roll_number.startswith(prefix) else None
            if roll_num and section_config["start"] <= roll_num <= section_config["end"]:
                student_section = section_id
                break
        except (ValueError, TypeError):
            continue
    
    if not student_section:
        # Set default section if not found
        student_section = "CSE_5A"
    
    # Get attendance records for this student in their section
    if student_section in attendance_data:
        section_data = attendance_data[student_section]
        for date, students in section_data.items():
            # Initialize date entry in history
            if date not in history:
                history[date] = {}
                
            # Get day of week for this date
            try:
                day_of_week = datetime.strptime(date, "%Y-%m-%d").strftime("%A")
                
                # Get subjects for this day from timetable
                if day_of_week in TIMETABLE.get(student_section, {}):
                    day_subjects = TIMETABLE[student_section][day_of_week]
                    
                    # For each subject, check if student has attendance record
                    for subject in day_subjects:
                        subject_key = subject
                        
                        # Check for subject-specific attendance first
                        subject_attendance_key = f"{subject}_{roll_number}"
                        if subject_attendance_key in students:
                            # If student has subject-specific attendance record
                            status_value = students[subject_attendance_key]
                            if status_value == 1:
                                history[date][subject_key] = "1/1"  # Present
                            elif status_value == 0:
                                history[date][subject_key] = "0/1"  # Absent
                            else:
                                history[date][subject_key] = "NC"   # Not Conducted
                        elif roll_number in students:
                            # Fall back to overall attendance for the day
                            status_value = students[roll_number]
                            if status_value == 1:
                                history[date][subject_key] = "1/1"  # Present
                            elif status_value == 0:
                                history[date][subject_key] = "0/1"  # Absent
                            else:
                                history[date][subject_key] = "NC"   # Not Conducted
                        else:
                            # If no record, mark as Not Conducted
                            history[date][subject_key] = "NC"
            except ValueError:
                continue
    
    return history

def get_student_daily_attendance(roll_number):
    """Get daily class attendance for a specific student"""
    attendance_data = load_attendance_data()
    daily_attendance = []
    
    # Find which section this student belongs to
    student_section = None
    for section_id, section_config in SECTIONS.items():
        prefix = section_config["prefix"]
        try:
            roll_num = int(roll_number[len(prefix):]) if roll_number.startswith(prefix) else None
            if roll_num and section_config["start"] <= roll_num <= section_config["end"]:
                student_section = section_id
                break
        except (ValueError, TypeError):
            continue
    
    if not student_section:
        return daily_attendance  # Empty if section not found
    
    # Group attendance by date and calculate classes attended vs total classes
    if student_section in attendance_data:
        # Get the timetable for this section
        section_timetable = TIMETABLE.get(student_section, {})
        
        # Group by date
        dates = {}
        for date, students in attendance_data[student_section].items():
            try:
                day_of_week = datetime.strptime(date, "%Y-%m-%d").strftime("%A")
                total_classes = len(section_timetable.get(day_of_week, []))
                
                if total_classes == 0:
                    continue  # Skip dates with no classes scheduled
                    
                # Initialize the date entry if not exists
                if date not in dates:
                    dates[date] = {
                        "date": date,
                        "day": day_of_week,
                        "classes_attended": 0,
                        "total_classes": total_classes
                    }
                
                # Count this student's attendance for this date
                if roll_number in students and students[roll_number] == 1:
                    dates[date]["classes_attended"] += 1
            except ValueError:
                continue
        
        # Convert to list and sort by date (newest first)
        daily_attendance = list(dates.values())
        daily_attendance.sort(key=lambda x: x["date"], reverse=True)
    
    return daily_attendance

def calculate_attendance_percentage(roll_number):
    """Calculate overall attendance percentage for a student, excluding NC classes"""
    attendance_history = get_student_attendance_history(roll_number)
    
    if not attendance_history:
        return 0  # No attendance records
    
    total_conducted_classes = 0
    classes_attended = 0
    
    # Count only conducted classes (exclude NC)
    for date, subjects in attendance_history.items():
        for subject, status in subjects.items():
            if status != "NC":  # Only count conducted classes
                total_conducted_classes += 1
                if status == "1/1" or status == "1":
                    classes_attended += 1
    
    if total_conducted_classes == 0:
        return 0  # Avoid division by zero
        
    return round((classes_attended / total_conducted_classes) * 100, 1)

# ----------------- Helper Functions -----------------
def load_users():
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        default_users = {
            "dr.smith": {
                "password": "teacher123",
                "name": "Dr. John Smith",
                "sections": list(SECTIONS.keys())
            },
            "prof.johnson": {
                "password": "teacher456",
                "name": "Professor Sarah Johnson",
                "sections": list(SECTIONS.keys())
            },
            "admin": {
                "password": "admin@123",
                "name": "System Administrator",
                "sections": list(SECTIONS.keys())
            },
            "hod.cse": {
                "password": "hod2024",
                "name": "HOD Computer Science",
                "sections": list(SECTIONS.keys())
            }
        }
        with open(USERS_FILE, 'w') as f:
            json.dump(default_users, f, indent=2)
        return default_users

def load_students_data():
    """Load students data with enhanced sample data for better graphs"""
    try:
        with open(DETAILS_FILE, 'r') as f:
            students_list = json.load(f)
            students_dict = {student['rollNo']: student for student in students_list}
            return students_dict
    except FileNotFoundError:
        # Enhanced sample data with more SGPA values for better graphs
        students_dict = {
            "22CSE998": {
                "rollNo": "22CSE998",
                "name": "ABUL HASAN",
                "mobile": "9835275387",
                "sgpas": {
                    "1": "8.5",
                    "2": "8.7",
                    "3": "7.35",
                    "4": "8.0",
                    "5": "8.2",
                    "6": "8.8"
                }
            },
            "23CSEAIML087": {
                "rollNo": "23CSEAIML087",
                "name": "RAHUL KUMAR",
                "mobile": "9876543210",
                "sgpas": {
                    "1": "9.0",
                    "2": "8.8",
                    "3": "9.2",
                    "4": "8.9",
                    "5": "9.1",
                    "6": "9.3"
                }
            },
            "23CSEDS015": {
                "rollNo": "23CSEDS015",
                "name": "PRIYA SHARMA",
                "mobile": "9123456789",
                "sgpas": {
                    "1": "7.8",
                    "2": "8.0",
                    "3": "7.9",
                    "4": "8.2",
                    "5": "8.4",
                    "6": "8.1"
                }
            }
        }
        return students_dict
    except Exception as e:
        logger.error(f"Error loading students data: {e}")
        return {}

def calculate_cgpa(sgpas_dict):
    """Calculate CGPA from SGPA values"""
    if not sgpas_dict:
        return 0.0
    
    total_sgpa = 0.0
    count = 0
    
    for sgpa_str in sgpas_dict.values():
        try:
            sgpa = float(sgpa_str)
            total_sgpa += sgpa
            count += 1
        except (ValueError, TypeError):
            continue
    
    return round(total_sgpa / count, 2) if count > 0 else 0.0

def load_encodings():
    try:
        with open(ENCODINGS_FILE, 'rb') as f:
            data = pickle.load(f)
            return data["encodings"], data["names"]
    except FileNotFoundError:
        return [], []

def load_student_details():
    """Load student details from details.json"""
    try:
        with open(DETAILS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.info(f"Details file {DETAILS_FILE} not found. Using placeholder data.")
        # Create sample data for demonstration
        sample_data = []
        for section_key, section in SECTIONS.items():
            for i in range(section["start"], section["end"] + 1):
                roll_number = f"{section['prefix']}{i:03d}"
                sample_data.append({
                    "rollNo": roll_number,
                    "name": f"Student {roll_number}",
                    "mobile": f"9{np.random.randint(100000000, 999999999)}",
                    "sgpas": {
                        "1": round(np.random.uniform(7.0, 9.5), 2),
                        "2": round(np.random.uniform(7.5, 9.8), 2)
                    }
                })
        return sample_data
    except Exception as e:
        logger.error(f"Error loading student details: {e}")
        return []

def get_student_info(roll_number):
    """Get student details by roll number"""
    student_details = load_student_details()
    for student in student_details:
        if student['rollNo'] == roll_number:
            return student
    return {
        'rollNo': roll_number,
        'name': f"Student {roll_number}",
        'mobile': 'N/A',
        'sgpas': {}
    }

def get_section_students(section):
    """Generate list of all students in a section with proper roll number formatting"""
    config = SECTIONS[section]
    students = []
    for i in range(config["start"], config["end"]+1):
        # Always use 3-digit zero padding for consistent roll number format
        roll_number = f"{config['prefix']}{i:03d}"
        students.append(roll_number)
    
    logger.info(f"Generated {len(students)} students for section {section}")
    return students


def calculate_classes_to_reach_percentage(attended, total, target_percentage):
    """Calculate how many consecutive classes a student needs to attend to reach target percentage"""
    if total == 0:
        return 0
    
    current_percentage = (attended / total) * 100
    
    # If already at or above target, return 0
    if current_percentage >= target_percentage:
        return 0
    
    # Calculate classes needed
    classes_needed = 0
    new_attended = attended
    new_total = total
    
    while (new_attended / new_total) * 100 < target_percentage:
        new_attended += 1
        new_total += 1
        classes_needed += 1
        
        # Safety check to prevent infinite loop
        if classes_needed > 1000:
            break
    
    return classes_needed


def check_if_student_absent(roll_number):
    """Check if a student was absent in the most recent class"""
    try:
        # Load attendance data
        with open(ATTENDANCE_FILE, 'r') as f:
            attendance_data = json.load(f)
        
        # Find the section for this roll number
        section = None
        for section_key, section_config in SECTIONS.items():
            if roll_number.startswith(section_config['prefix']):
                section = section_key
                break
        
        if not section or section not in attendance_data:
            return True  # Default to absent if no section or no data for section
        
        # Get the most recent date
        dates = list(attendance_data[section].keys())
        if not dates:
            return True  # Default to absent if no dates
        
        # Sort dates to get the most recent one
        most_recent_date = sorted(dates)[-1]
        
        # Check if student was absent in the most recent class
        entries = attendance_data[section][most_recent_date]
        if roll_number not in entries:
            return True  # Student not in record, consider absent
        
        # Return True if student was absent, False if present
        return entries[roll_number].get('status', '').lower() != 'present'
    
    except Exception as e:
        logger.error(f"Error checking if student was absent: {str(e)}")
        return True  # Default to absent on error

def get_student_attendance(roll_number):
    """Get attendance data for a specific student"""
    try:
        # Load attendance data
        with open(ATTENDANCE_FILE, 'r') as f:
            attendance_data = json.load(f)
        
        # Find the section for this roll number
        section = None
        for section_key, section_config in SECTIONS.items():
            if roll_number.startswith(section_config['prefix']):
                section = section_key
                break
        
        if not section or section not in attendance_data:
            return {'attended': 0, 'total': 4, 'percentage': 0}
        
        # Count attended classes
        attended = 0
        total = 0
        
        for date, entries in attendance_data[section].items():
            if roll_number in entries:
                total += 1
                if entries[roll_number].get('status', '').lower() == 'present':
                    attended += 1
        
        # If no records found, use default values
        if total == 0:
            total = 4  # Default to 4 classes
        
        percentage = round((attended / total) * 100, 1) if total > 0 else 0
        
        return {
            'attended': attended,
            'total': total,
            'percentage': percentage
        }
    except Exception as e:
        logger.error(f"Error getting student attendance: {str(e)}")
        return {'attended': 0, 'total': 4, 'percentage': 0}


@app.route('/api/record_attendance', methods=['POST'])
@login_required
def record_attendance():
    """Record attendance for students"""
    try:
        data = request.get_json()
        section_id = data.get('section_id')
        student_attendance = data.get('attendance', {})
        subject = data.get('subject', 'General')
        marked_by = session.get('username', 'system')
        
        if not section_id or not student_attendance:
            return jsonify({'error': 'Missing required fields'}), 400
        
        if USE_MYSQL:
            # Record attendance directly to MySQL
            success = mysql_db.save_attendance(
                section_id=section_id,
                attendance_data=student_attendance,
                subject=subject,
                marked_by=marked_by
            )
            
            if success:
                return jsonify({
                    'success': True,
                    'message': f'Attendance recorded successfully for {len(student_attendance)} students',
                    'section': section_id,
                    'subject': subject
                })
            else:
                return jsonify({'error': 'Failed to record attendance in database'}), 500
        else:
            # Fallback to JSON method
            attendance_data = load_attendance_data()
            today = datetime.now().strftime('%Y-%m-%d')
            
            if section_id not in attendance_data:
                attendance_data[section_id] = {}
            
            attendance_data[section_id][today] = student_attendance
            save_attendance_data(attendance_data)
            
            return jsonify({
                'success': True,
                'message': f'Attendance recorded successfully for {len(student_attendance)} students',
                'section': section_id,
                'date': today
            })
    
    except Exception as e:
        logger.error(f"Error recording attendance: {str(e)}")
        return jsonify({'error': f'Failed to record attendance: {str(e)}'}), 500

@app.route('/api/get_student_profile/<roll_number>', methods=['GET'])
def get_student_profile(roll_number):
    """Get comprehensive student profile with attendance history"""
    try:
        # Get student details
        if USE_MYSQL:
            student_details = mysql_db.get_student_details(roll_number)
            if not student_details:
                return jsonify({'error': 'Student not found'}), 404
                
            # Get attendance history from MySQL
            attendance_history = mysql_db.get_student_attendance_history(roll_number)
            
            return jsonify({
                'success': True,
                'student': student_details,
                'attendance_history': attendance_history
            })
        else:
            # JSON fallback
            student_info = get_student_info(roll_number)
            attendance_percentage = calculate_attendance_percentage(roll_number)
            daily_attendance = get_student_daily_attendance(roll_number)
            
            return jsonify({
                'success': True,
                'student': student_info,
                'attendance_percentage': attendance_percentage,
                'daily_attendance': daily_attendance
            })
    
    except Exception as e:
        logger.error(f"Error getting student profile: {str(e)}")
        return jsonify({'error': f'Failed to get student profile: {str(e)}'}), 500

@app.route('/api/get_top_performers', methods=['GET'])
def get_top_performers():
    """Get top performing students based on CGPA"""
    try:
        section_id = request.args.get('section_id')
        limit = int(request.args.get('limit', 10))
        
        if USE_MYSQL:
            top_performers = mysql_db.get_top_performers(section_id=section_id, limit=limit)
            return jsonify({
                'success': True,
                'top_performers': top_performers
            })
        else:
            return jsonify({'error': 'MySQL not available for performance analytics'}), 503
    
    except Exception as e:
        logger.error(f"Error getting top performers: {str(e)}")
        return jsonify({'error': f'Failed to get top performers: {str(e)}'}), 500

@app.route('/api/get_academic_summary/<roll_number>', methods=['GET'])
def get_academic_summary(roll_number):
    """Get comprehensive academic summary for a student"""
    try:
        if USE_MYSQL:
            summary = mysql_db.get_student_academic_summary(roll_number)
            if not summary:
                return jsonify({'error': 'Student not found'}), 404
            
            return jsonify({
                'success': True,
                'academic_summary': summary
            })
        else:
            # JSON fallback
            student_info = get_student_info(roll_number)
            attendance_percentage = calculate_attendance_percentage(roll_number)
            
            return jsonify({
                'success': True,
                'academic_summary': {
                    **student_info,
                    'attendance_percentage': attendance_percentage
                }
            })
    
    except Exception as e:
        logger.error(f"Error getting academic summary: {str(e)}")
        return jsonify({'error': f'Failed to get academic summary: {str(e)}'}), 500

@app.route('/api/get_section_analytics/<section_id>', methods=['GET'])
def get_section_analytics(section_id):
    """Get comprehensive analytics for a section including CGPA distribution"""
    try:
        if USE_MYSQL:
            # Get all students in section with CGPA
            query = """
                SELECT roll_number, name, cgpa, 
                       sgpa_sem1, sgpa_sem2, sgpa_sem3, sgpa_sem4,
                       sgpa_sem5, sgpa_sem6, sgpa_sem7, sgpa_sem8
                FROM students 
                WHERE section_id = %s AND cgpa IS NOT NULL
                ORDER BY cgpa DESC
            """
            students = mysql_db.execute_query(query, (section_id,)) or []
            
            # Calculate section statistics
            if students:
                cgpas = [float(s['cgpa']) for s in students if s['cgpa']]
                avg_cgpa = sum(cgpas) / len(cgpas) if cgpas else 0
                max_cgpa = max(cgpas) if cgpas else 0
                min_cgpa = min(cgpas) if cgpas else 0
                
                # CGPA distribution
                excellent = len([c for c in cgpas if c >= 9.0])
                good = len([c for c in cgpas if 8.0 <= c < 9.0])
                average = len([c for c in cgpas if 7.0 <= c < 8.0])
                below_average = len([c for c in cgpas if c < 7.0])
            else:
                avg_cgpa = max_cgpa = min_cgpa = 0
                excellent = good = average = below_average = 0
            
            return jsonify({
                'success': True,
                'section_id': section_id,
                'total_students': len(students),
                'statistics': {
                    'average_cgpa': round(avg_cgpa, 2),
                    'highest_cgpa': max_cgpa,
                    'lowest_cgpa': min_cgpa
                },
                'cgpa_distribution': {
                    'excellent': excellent,  # 9.0+
                    'good': good,            # 8.0-8.9
                    'average': average,      # 7.0-7.9
                    'below_average': below_average  # <7.0
                },
                'students': students
            })
        else:
            return jsonify({'error': 'MySQL not available for section analytics'}), 503
    
    except Exception as e:
        logger.error(f"Error getting section analytics: {str(e)}")
        return jsonify({'error': f'Failed to get section analytics: {str(e)}'}), 500

@app.route('/api/send_student_email/<roll_number>', methods=['GET'])
def send_student_email(roll_number):
    """Send attendance and academic performance email to a specific student"""
    try:
        # Get student details
        logger.info(f"Getting student info for {roll_number}")
        student_info = get_student_info(roll_number)
        logger.info(f"Student info type: {type(student_info)}")
        logger.info(f"Student info: {student_info}")
        student_name = student_info.get('name', f"Student {roll_number}")
        
        # Get attendance data
        logger.info(f"Getting attendance data for {roll_number}")
        attendance_data = get_student_attendance(roll_number)
        logger.info(f"Attendance data type: {type(attendance_data)}")
        logger.info(f"Attendance data: {attendance_data}")
        
        # Handle different return types from get_student_attendance
        if isinstance(attendance_data, dict):
            classes_attended = attendance_data.get('attended', 0)
            total_classes = attendance_data.get('total', 4)  # Default to 4 if not available
        else:
            # Default values if attendance_data is not a dictionary
            classes_attended = 0
            total_classes = 4
        
        # Calculate attendance percentage
        if isinstance(attendance_data, dict):
            attendance_percentage = attendance_data.get('percentage', 0)
        else:
            # Calculate percentage if attendance_data is not a dictionary
            attendance_percentage = (classes_attended / total_classes * 100) if total_classes > 0 else 0
        
        # Check if the student was present in the most recent class
        # Only send email if the student was absent
        is_absent = check_if_student_absent(roll_number)
        
        if not is_absent:
            return jsonify({
                'status': 'skipped', 
                'message': f'Email not sent to {student_name} ({roll_number}) as they were present in the last class',
                'details': {
                    'attendance': f"{attendance_percentage}%",
                    'classes_attended': classes_attended,
                    'total_classes': total_classes
                }
            })
        
        # Calculate classes needed to reach 80%
        missed_classes = total_classes - classes_attended
        classes_to_80 = calculate_classes_to_reach_percentage(classes_attended, total_classes, 80)
        
        # Get academic data
        sgpas = student_info.get('sgpas', {})
        
        # Handle case when sgpas is not a dictionary
        if not isinstance(sgpas, dict):
            logger.warning(f"sgpas is not a dictionary: {type(sgpas)}, value: {sgpas}")
            sgpas = {}
            
        sgpa_values = list(sgpas.values())
        latest_sgpa = sgpa_values[-1] if sgpa_values else 'N/A'
        cgpa = calculate_cgpa(sgpas_dict=sgpas)
        
        # Send the email with enhanced content
        faculty_name = "Dr. Faculty Member"  # Can be customized or passed as parameter
        subject_name = "Computer Science"    # Can be customized or passed as parameter
        
        success = send_attendance_email(
            student_roll=roll_number,
            student_name=student_name,
            attendance_percentage=attendance_percentage,
            classes_attended=classes_attended,
            total_classes=total_classes,
            classes_to_80=classes_to_80,
            missed_classes=missed_classes,
            subject_name=subject_name,
            sgpa=latest_sgpa,
            cgpa=cgpa,
            faculty_name=faculty_name
        )
        
        if success:
            return jsonify({
                'status': 'success', 
                'message': f'Email sent to {student_name} ({roll_number})',
                'details': {
                    'attendance': f"{attendance_percentage}%",
                    'classes_attended': classes_attended,
                    'total_classes': total_classes
                }
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to send email'
            })
    except Exception as e:
        logger.error(f"Error sending email to student {roll_number}: {str(e)}")
        return jsonify({
            'status': 'error', 
            'message': f'Failed to send email: {str(e)}'
        }), 500

def authenticate_user(username, password):
    users = load_users()
    user_data = users.get(username)
    if user_data and user_data.get('password') == password:
        # Make sure sections field exists
        if 'sections' not in user_data:
            user_data['sections'] = list(SECTIONS.keys())
        return user_data
    return None

def load_attendance_data():
    """Load attendance data - uses MySQL if available, otherwise JSON"""
    if USE_MYSQL:
        try:
            # Load data from MySQL and convert to the expected format
            attendance_data = {section: {} for section in SECTIONS}
            
            for section_id in SECTIONS.keys():
                # Get attendance statistics for this section
                stats = mysql_db.get_attendance_statistics(section_id)
                if stats:
                    # Convert MySQL format back to the expected JSON structure
                    for stat in stats:
                        student_roll = stat['student_roll']
                        # We need to reconstruct the date-based structure
                        # This is a simplified approach - you might need to enhance this
                        # For now, we'll create a summary based on overall attendance
                        today = datetime.now().strftime('%Y-%m-%d')
                        if today not in attendance_data[section_id]:
                            attendance_data[section_id][today] = {}
                        
                        # Set attendance based on percentage (simplified logic)
                        percentage = float(stat.get('percentage', 0))
                        attendance_data[section_id][today][student_roll] = 1 if percentage >= 50 else 0
            
            return attendance_data
        except Exception as e:
            logging.error(f"❌ MySQL attendance load failed: {e}. Falling back to JSON.")
            # Fall back to JSON if MySQL fails
    
    # JSON fallback
    try:
        with open(os.path.join(APP_ROOT, 'database', 'attendance.json'), 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Initialize with empty data for each section
        attendance_data = {section: {} for section in SECTIONS}
        with open(os.path.join(APP_ROOT, 'database', 'attendance.json'), 'w') as f:
            json.dump(attendance_data, f, indent=2)
        return attendance_data

def load_timetable():
    try:
        with open(os.path.join(APP_ROOT, 'database', 'timetable.json'), 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Return empty timetable if file not found
        return {section: {} for section in SECTIONS}

def load_daily_attendance():
    try:
        with open(os.path.join(APP_ROOT, 'database', 'daily_attendance.json'), 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Initialize with empty data for each section
        daily_attendance = {section: {} for section in SECTIONS}
        with open(os.path.join(APP_ROOT, 'database', 'daily_attendance.json'), 'w') as f:
            json.dump(daily_attendance, f, indent=2)
        return daily_attendance

def save_daily_attendance(daily_attendance_data):
    with open(os.path.join(APP_ROOT, 'database', 'daily_attendance.json'), 'w') as f:
        json.dump(daily_attendance_data, f, indent=2)

def save_attendance_data(attendance_data):
    """Save attendance data - uses MySQL if available, otherwise JSON"""
    if USE_MYSQL:
        # Save to MySQL database
        try:
            for section_id, dates in attendance_data.items():
                for date_str, students_attendance in dates.items():
                    # Convert attendance data to the format expected by MySQL adapter
                    attendance_records = {}
                    for student_roll, status in students_attendance.items():
                        if not student_roll.startswith('online_'):
                            attendance_records[student_roll] = status
                    
                    if attendance_records:
                        success = mysql_db.save_attendance(
                            section_id=section_id,
                            attendance_data=attendance_records,
                            subject='General',
                            marked_by=session.get('username', 'system')
                        )
                        if success:
                            logging.info(f"✅ Saved attendance to MySQL for {section_id} on {date_str}")
                        else:
                            logging.error(f"❌ Failed to save attendance to MySQL for {section_id}")
            return True
        except Exception as e:
            logging.error(f"❌ MySQL attendance save failed: {e}. Falling back to JSON.")
            # Fall back to JSON if MySQL fails
    
    # JSON fallback
    with open(os.path.join(APP_ROOT, 'database', 'attendance.json'), 'w') as f:
        json.dump(attendance_data, f, indent=2)

def create_attendance_excel(section, present_students):
    all_students = get_section_students(section)
    current_time = datetime.now()
    student_details = load_student_details()
    
    # Create a mapping of roll numbers to student details for faster lookup
    student_map = {student['rollNo']: student for student in student_details}
    
    data = []
    for student in all_students:
        student_info = student_map.get(student, {
            'name': f"Student {student}",
            'mobile': 'N/A',
            'sgpas': {}
        })
        
        data.append({
            "Roll Number": student,
            "Student Name": student_info['name'],
            "Mobile Number": student_info['mobile'],
            "SGPA Semester 1": student_info['sgpas'].get('1', 'N/A'),
            "SGPA Semester 2": student_info['sgpas'].get('2', 'N/A'),
            "Section": SECTIONS[section]["name"],
            "Status": "Present" if student in present_students else "Absent",
            "Date": current_time.strftime("%Y-%m-%d"),
            "Time": current_time.strftime("%H:%M:%S"),
            "Marked By": session.get('username', 'Unknown')
        })

    df = pd.DataFrame(data)
    
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Attendance_Report')
        
        workbook = writer.book
        worksheet = writer.sheets['Attendance_Report']
        
        for col in worksheet.columns:
            max_len = max(len(str(cell.value)) for cell in col if cell.value)
            worksheet.column_dimensions[col[0].column_letter].width = min(max_len + 2, 50)
            
        from openpyxl.styles import Font, PatternFill, Alignment
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_alignment = Alignment(horizontal="center")
        
        for cell in worksheet[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
    
    buffer.seek(0)
    return buffer

# ----------------- Camera Processing Class -----------------
class CameraProcessor:
    def __init__(self):
        self.camera = None
        self.is_running = False
        self.frame_queue = Queue(maxsize=2)  # Reduced queue size
        self.recognition_queue = Queue(maxsize=1)  # Reduced queue size
        self.display_frame = None
        self.recognition_results = []
        self.fps = 0
        self.last_fps_time = time.time()
        self.frame_count = 0
        self.processing_thread = None
        self.recognition_thread = None
        self.lock = threading.Lock()  # Add a lock for thread safety
        
    def initialize_camera(self):
        """Initialize camera with optimized settings"""
        try:
            # Try different camera indices
            for i in range(0, 4):  # Start from 0 instead of 1
                self.camera = cv2.VideoCapture(i, cv2.CAP_DSHOW)
                if self.camera.isOpened():
                    # Test if we can actually read a frame
                    ret, frame = self.camera.read()
                    if ret:
                        logger.info(f"Camera found at index {i}")
                        break
                    else:
                        self.camera.release()
                else:
                    if i == 3:  # Last attempt
                        return False, "No camera found or cannot access camera"
            else:
                return False, "No camera found"
            
            # Optimize camera settings for performance
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.camera.set(cv2.CAP_PROP_FPS, 15)  # Reduced FPS for better performance
            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.camera.set(cv2.CAP_PROP_AUTOFOCUS, 0)
            self.camera.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
            
            return True, "Camera initialized successfully"
        except Exception as e:
            logger.error(f"Camera initialization error: {str(e)}")
            return False, f"Camera initialization error: {str(e)}"
    
    def start_processing(self, known_encodings, known_names):
        """Start camera processing threads"""
        if self.is_running:
            return
            
        self.is_running = True
        self.known_encodings = known_encodings
        self.known_names = known_names
        
        # Start frame capture thread
        self.processing_thread = threading.Thread(target=self._capture_frames, daemon=True)
        self.processing_thread.start()
        
        # Start recognition processing thread
        self.recognition_thread = threading.Thread(target=self._process_recognition, daemon=True)
        self.recognition_thread.start()
    
    def stop_processing(self):
        """Stop all processing threads"""
        self.is_running = False
        if self.camera:
            self.camera.release()
            self.camera = None
        
        # Clear queues
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except:
                break
        while not self.recognition_queue.empty():
            try:
                self.recognition_queue.get_nowait()
            except:
                break
    
    def _capture_frames(self):
        """Continuous frame capture thread"""
        while self.is_running and self.camera is not None:
            try:
                ret, frame = self.camera.read()
                if ret:
                    # Calculate FPS
                    current_time = time.time()
                    if current_time - self.last_fps_time >= 1.0:
                        self.fps = self.frame_count / (current_time - self.last_fps_time)
                        self.frame_count = 0
                        self.last_fps_time = current_time
                    
                    self.frame_count += 1
                    
                    # Store frame for display
                    with self.lock:
                        self.display_frame = frame.copy()
                    
                    # Add frame to recognition queue (skip if queue is full)
                    if not self.recognition_queue.full():
                        try:
                            # Resize frame for faster processing
                            small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
                            self.recognition_queue.put_nowait(small_frame)
                        except:
                            pass
                else:
                    logger.warning("Failed to capture frame from camera")
                
                time.sleep(0.05)  # Slightly increased delay
            except Exception as e:
                logger.error(f"Frame capture error: {e}")
                time.sleep(1)  # Wait before trying again
    
    def _process_recognition(self):
        """Recognition processing thread"""
        global present_students
        last_recognition_time = {}
        recognition_cooldown = 2.0
        
        while self.is_running:
            try:
                frame = self.recognition_queue.get(timeout=1.0)
                recognized_faces = self._recognize_faces(frame)
                
                # Update present students with cooldown
                current_time = time.time()
                for face in recognized_faces:
                    if face['name'] != "Unknown" and face['confidence'] > 0.4:
                        last_seen = last_recognition_time.get(face['name'], 0)
                        if current_time - last_seen >= recognition_cooldown:
                            present_students.add(face['name'])
                            last_recognition_time[face['name']] = current_time
                
                self.recognition_results = recognized_faces
                time.sleep(0.1)
                
            except Exception as e:
                if "Empty" not in str(e):
                    logger.error(f"Recognition processing error: {e}")
                continue
    
    def _recognize_faces(self, frame):
        """Process face recognition on a single frame"""
        try:
            rgb_small_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_small_frame, model="hog")
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

            recognized_faces = []
            for face_encoding, face_location in zip(face_encodings, face_locations):
                name = "Unknown"
                confidence = 0

                if self.known_encodings and len(self.known_encodings) > 0:
                    # REDUCE TOLERANCE FROM 0.4 to 0.6 for better recognition
                    matches = face_recognition.compare_faces(self.known_encodings, face_encoding, tolerance=0.41)
                    face_distances = face_recognition.face_distance(self.known_encodings, face_encoding)

                    if len(face_distances) > 0:
                        best_match_index = np.argmin(face_distances)
                        # ALSO REDUCE THIS THRESHOLD
                        if matches[best_match_index] and face_distances[best_match_index] < 0.41:
                            name = self.known_names[best_match_index]
                            confidence = 1 - face_distances[best_match_index]

                # Scale back face locations
                top, right, bottom, left = [coord * 2 for coord in face_location]
                
                recognized_faces.append({
                    'name': name,
                    'confidence': confidence,
                    'location': (int(top), int(right), int(bottom), int(left))
                })

            return recognized_faces
        except Exception as e:
            logger.error(f"Face recognition error: {e}")
            return []
          
                    
    
    def get_display_frame_with_boxes(self):
        """Get current display frame with recognition boxes"""
        with self.lock:
            if self.display_frame is None:
                # Return a black frame if no camera feed
                placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(placeholder, "No camera feed", (150, 240), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                return placeholder
                
            frame = self.display_frame.copy()
        
        for face in self.recognition_results:
            top, right, bottom, left = face['location']
            name = face['name']
            confidence = face['confidence']

            if name == "Unknown":
                color = (0, 0, 255)
                bg_color = (0, 0, 200)
                label = "Unknown"
            else:
                color = (0, 255, 0)
                bg_color = (0, 200, 0)
                label = name

            cv2.rectangle(frame, (left, top), (right, bottom), color, 3)
            
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.8
            thickness = 2
            
            (label_width, label_height), baseline = cv2.getTextSize(label, font, font_scale, thickness)
            label_y = top - 15 if top - 15 > label_height else bottom + label_height + 15
            
            cv2.rectangle(frame, 
                         (left, label_y - label_height - 15), 
                         (left + label_width + 20, label_y + 5), 
                         bg_color, cv2.FILLED)
            
            cv2.putText(frame, label, 
                       (left + 10, label_y - 8), 
                       font, font_scale, (255, 255, 255), thickness)
            
            if name != "Unknown" and confidence > 0:
                confidence_text = f"Conf: {confidence:.1%}"
                conf_width, conf_height = cv2.getTextSize(confidence_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
                cv2.rectangle(frame, 
                             (left, label_y + 10), 
                             (left + conf_width + 10, label_y + conf_height + 20), 
                             bg_color, cv2.FILLED)
                cv2.putText(frame, confidence_text, 
                           (left + 5, label_y + conf_height + 15), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        fps_text = f"FPS: {self.fps:.1f}"
        cv2.putText(frame, fps_text, (frame.shape[1] - 120, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, fps_text, (frame.shape[1] - 120, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1)

        return frame

# ----------------- Routes -----------------
@app.route('/')
def index():
    if 'authenticated' in session and session['authenticated']:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/test-email', methods=['GET'])
def test_email_route():
    """Route to test email configuration"""
    success, message = test_email_configuration()
    return jsonify({
        'success': success,
        'message': message
    })

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get form data
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            return jsonify({'success': False, 'message': 'Username and password are required'})
        
        # Detect student-style user id: two digits + 'cse' + letters + 3 digits (case-insensitive)
        try:
            import re
            user_lower = username.strip().lower()
            # Normalize roll number to uppercase standard (e.g., 23CSEAIML087)
            roll_candidate = username.strip().upper()
            if re.match(r'^[0-9]{2}cse[a-z]*[0-9]{3}$', user_lower):
                # Password must match user id exactly (case-insensitive considered equal)
                if password.strip().lower() == user_lower:
                    # Set session as permanent to work across tabs
                    session.permanent = True
                    session['authenticated'] = True
                    session['username'] = roll_candidate
                    session['faculty_name'] = roll_candidate
                    session['user_type'] = 'student'  # Add user type for better session management
                    # Students have no sections; keep empty list to avoid unauthorized sections
                    session['sections'] = []
                    # Redirect to student dashboard
                    return jsonify({'success': True, 'redirect': url_for('dashboard')})
        except Exception as e:
            logger.error(f"Error in student login: {str(e)}")
            pass
        
        user_data = authenticate_user(username, password)
        if user_data:
            # Set session as permanent to work across tabs
            session.permanent = True
            session['authenticated'] = True
            session['username'] = username
            session['faculty_name'] = user_data.get('name', username)
            session['user_type'] = 'faculty'  # Add user type for better session management
            session['sections'] = user_data.get('sections', list(SECTIONS.keys()))
            return jsonify({'success': True, 'redirect': url_for('dashboard')})
        else:
            return jsonify({'success': False, 'message': 'Invalid credentials'})
    
    # GET request - show login page
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    global camera_processor, attendance_started, present_students
    
    if camera_processor:
        camera_processor.stop_processing()
        camera_processor = None
    
    attendance_started = False
    present_students = set()
    
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Check user type from session
    user_type = session.get('user_type', None)
    username = session.get('username', '')
    
    # If user_type is not set, determine it based on other session data
    if not user_type:
        import re
        user_sections = session.get('sections', [])
        # Detect student-style login (no sections or username looks like roll)
        is_student = (not user_sections) or bool(re.match(r'^[0-9]{2}CSE[A-Z]*[0-9]{3}$', username.upper()))
        user_type = 'student' if is_student else 'faculty'
        # Save to session for future use
        session['user_type'] = user_type
    
    # Handle student dashboard
    if user_type == 'student':
        student_roll = username.upper()
        # Render dedicated student dashboard
        return render_template('student_dashboard.html', 
                             username=session.get('username'),
                             student_roll=student_roll,
                             student_name=session.get('faculty_name', session.get('username')))
    
    # Handle faculty dashboard
    else:
        user_sections = session.get('sections', [])
        filtered_sections = {k: v for k, v in SECTIONS.items() if k in user_sections}
        
        # Get attendance statistics for graph display
        section_stats = {}
        for section_id, section_info in filtered_sections.items():
            students = get_section_students(section_id)
            total_students = len(students)
            logger.info(f"Section {section_id} has {total_students} students: {students}")
            section_stats[section_id] = {
                'name': section_info['name'],
                'total': total_students,
                'present': 0,
                'absent': total_students
            }
        
        students_data = load_students_data()
        
        # Render faculty dashboard
        return render_template('dashboard.html', 
                             username=session.get('username'),
                             students_data=students_data,
                             faculty_name=session.get('faculty_name', session.get('username')),
                             sections=filtered_sections,
                             user_sections=user_sections,
                             section_stats=section_stats,
                             is_student=False)

@app.route('/jitsi_demo')
def jitsi_demo():
    """Jitsi integration demo page"""
    return send_file('jitsi_demo.html')

@app.route('/jitsi_popup_integration.js')
def jitsi_popup_script():
    """Serve the Jitsi popup integration JavaScript"""
    return send_file('jitsi_popup_integration.js', mimetype='application/javascript')

@app.route('/jitsi_enhanced_integration.js')
@cross_origin(origins=['http://localhost:5000', 'https://meet.jit.si', 'http://meet.jit.si', 'file://', 'null'], methods=['GET', 'OPTIONS'], supports_credentials=True)
def jitsi_enhanced_script():
    """Serve the enhanced Jitsi integration JavaScript with automatic popup detection"""
    response = send_file('jitsi_enhanced_integration.js', mimetype='application/javascript')
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', '*')
    response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

@app.route('/zoom_demo')
def zoom_demo():
    """Legacy Zoom demo redirect to Jitsi demo"""
    return redirect('/jitsi_demo')

@app.route('/online_attendance')
@login_required
def online_attendance_page():
    """Online attendance management page for faculty - Professional Interface"""
    user_type = session.get('user_type', 'faculty')
    if user_type != 'faculty':
        return redirect(url_for('dashboard'))  # Only faculty can access online attendance management
    
    user_sections = session.get('sections', [])
    filtered_sections = {k: v for k, v in SECTIONS.items() if k in user_sections}
    
    return render_template('online_attendance_professional.html',
                         faculty_name=session.get('faculty_name', session.get('username')),
                         sections=filtered_sections)

@app.route('/student/<student_roll>')
@login_required
def view_student_dashboard(student_roll):
    """Allow faculty to view a specific student's dashboard"""
    # Check if user is faculty
    user_type = session.get('user_type', None)
    if user_type != 'faculty':
        return redirect(url_for('dashboard'))  # Redirect students to their own dashboard
    
    # Get student information
    student_info = get_student_info(student_roll.upper())
    student_name = student_info.get('name', f'Student {student_roll}')
    
    # Render student dashboard with the specified student's data
    return render_template('student_dashboard.html', 
                         username=session.get('username'),
                         student_roll=student_roll.upper(),
                         student_name=student_name,
                         is_faculty_view=True)  # Flag to indicate this is a faculty viewing student data

@app.route('/api/section_students')
@login_required
def api_get_section_students():
    """Get all students in a specific section for manual attendance"""
    section = request.args.get('section')
    if not section:
        return jsonify({'success': False, 'message': 'No section provided'})
    
    # Check if user has access to this section
    user_sections = session.get('sections', [])
    user_type = session.get('user_type', None)
    
    # If user_type is not set, determine it
    if not user_type:
        username = session.get('username', '')
        import re
        is_student = (not user_sections) or bool(re.match(r'^[0-9]{2}CSE[A-Z]*[0-9]{3}$', username.upper()))
        user_type = 'student' if is_student else 'faculty'
        # Save to session for future use
        session['user_type'] = user_type
    
    # Students can access all sections, faculty only their assigned sections
    if user_type == 'faculty' and section not in user_sections:
        return jsonify({'success': False, 'message': 'You do not have access to this section'})
    
    try:
        students = get_section_students(section)
        student_details = load_student_details()
        
        # Create a mapping of roll numbers to student details
        student_map = {student['rollNo']: student for student in student_details}
        
        # Prepare detailed student list
        detailed_students = []
        for roll_number in students:
            student_info = student_map.get(roll_number, {
                'rollNo': roll_number,
                'name': f'Student {roll_number}',
                'mobile': 'N/A'
            })
            detailed_students.append(student_info)
        
        return jsonify({
            'success': True,
            'students': detailed_students,
            'section': SECTIONS[section]['name'],
            'count': len(detailed_students)
        })
    except Exception as e:
        logger.error(f"Error fetching section students: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error fetching students: {str(e)}'
        })

@app.route('/api/debug')
@login_required
def debug_session():
    """Debug endpoint to check session state"""
    return jsonify({
        'authenticated': session.get('authenticated'),
        'username': session.get('username'),
        'faculty_name': session.get('faculty_name'),
        'sections': session.get('sections'),
        'session_keys': list(session.keys()),
        'online_attendance_available': online_attendance is not None,
        'online_attendance_methods': dir(online_attendance) if online_attendance else None,
        'has_create_method': hasattr(online_attendance, 'create_online_session') if online_attendance else False
    })

@app.route('/api/sections')
@login_required
def api_get_sections():
    sections_data = []
    # Get user sections - for students, return all sections; for faculty, return assigned sections
    user_sections = session.get('sections', [])
    user_type = session.get('user_type', None)
    
    # If user_type is not set, determine it
    if not user_type:
        username = session.get('username', '')
        import re
        is_student = (not user_sections) or bool(re.match(r'^[0-9]{2}CSE[A-Z]*[0-9]{3}$', username.upper()))
        user_type = 'student' if is_student else 'faculty'
        # Save to session for future use
        session['user_type'] = user_type
    
    # If student, show all sections; if faculty, show only assigned sections
    sections_to_show = list(SECTIONS.keys()) if user_type == 'student' else user_sections
    
    for key, value in SECTIONS.items():
        if key not in sections_to_show:
            continue
        students = get_section_students(key)
        present_count = sum(1 for student in students if student in present_students)
        total_count = len(students)
        attendance_rate = (present_count / total_count) * 100 if total_count > 0 else 0
        sections_data.append({
            'id': key,
            'name': value['name'],
            'start': value['start'],
            'present': present_count,
            'absent': total_count - present_count,
            'attendance_rate': round(attendance_rate, 1),
            'end': value['end'],
            'prefix': value['prefix'],
            'total_students': value['end'] - value['start'] + 1
        })
    return jsonify(sections_data)

@app.route('/api/timetable/<section_id>')
@login_required
def get_section_timetable(section_id):
    """Get timetable for a specific section"""
    if section_id not in SECTIONS:
        return jsonify({
            'success': False,
            'message': 'Section not found'
        })
    
    timetable = load_timetable()
    if section_id in timetable:
        return jsonify({
            'success': True,
            'timetable': timetable[section_id]
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Timetable not found for this section'
        })

@app.route('/api/start_attendance', methods=['POST'])
@login_required
def start_attendance():
    global camera_processor, attendance_started
    
    section = request.json.get('section')
    if not section:
        return jsonify({'success': False, 'message': 'No section provided'})
    
    known_encodings, known_names = load_encodings()
    if not known_encodings:
        return jsonify({'success': False, 'message': 'No encodings found'})
    
    section_config = SECTIONS[section]
    section_encodings = []
    section_names = []
    
    for enc, name in zip(known_encodings, known_names):
        if name.startswith(section_config["prefix"]):
            try:
                roll_num = int(name[len(section_config["prefix"]):])
                if section_config["start"] <= roll_num <= section_config["end"]:
                    section_encodings.append(enc)
                    section_names.append(name)
            except ValueError:
                continue
    
    if not section_encodings:
        return jsonify({'success': False, 'message': f'No encodings found for {SECTIONS[section]["name"]}'})
    
    camera_processor = CameraProcessor()
    success, message = camera_processor.initialize_camera()
    
    if not success:
        return jsonify({'success': False, 'message': message})
    
    camera_processor.start_processing(section_encodings, section_names)
    attendance_started = True
    
    return jsonify({'success': True, 'message': 'Attendance session started'})

@app.route('/api/stop_attendance', methods=['POST'])
@login_required
def stop_attendance():
    global camera_processor, attendance_started
    
    if camera_processor:
        camera_processor.stop_processing()
        camera_processor = None
    
    # Save attendance data to JSON file
    section = request.json.get('section')
    send_emails = request.json.get('send_emails', False)  # Option to send emails
    
    if section and section in SECTIONS:
        # Check if user has access to this section
        user_sections = session.get('sections', [])
        if section not in user_sections:
            return jsonify({'error': 'You do not have access to this section'}), 403
            
        date_str = datetime.now().strftime('%Y-%m-%d')
        attendance_data = load_attendance_data()
        
        if section not in attendance_data:
            attendance_data[section] = {}
            
        if date_str not in attendance_data[section]:
            attendance_data[section][date_str] = {}
        
        # Convert present_students set to a dictionary with 1 for present
        all_students = get_section_students(section)
        absent_students = []
        
        for student in all_students:
            if student in present_students:
                attendance_data[section][date_str][student] = 1
            else:
                attendance_data[section][date_str][student] = 0
                absent_students.append(student)
        
        save_attendance_data(attendance_data)
        
        # Send emails to absent students if requested
        if send_emails and absent_students:
            send_absence_emails_to_students(absent_students, section, date_str)
        
        response_msg = f'Attendance session stopped and data saved. {len(absent_students)} students were absent.'
        if send_emails and absent_students:
            response_msg += f' Emails sent to {len(absent_students)} absent students.'
            
    attendance_started = False
    return jsonify({
        'success': True, 
        'message': response_msg,
        'absent_count': len(absent_students) if section else 0
    })

@app.route('/api/reset_attendance', methods=['POST'])
@login_required
def reset_attendance():
    global present_students
    
    present_students = set()
    return jsonify({'success': True, 'message': 'Attendance data reset'})

@app.route('/api/add_student', methods=['POST'])
@login_required
def add_student():
    global present_students
    
    student = request.json.get('student')
    if student:
        present_students.add(student)
        return jsonify({'success': True, 'message': f'{student} marked present'})
    
    return jsonify({'success': False, 'message': 'No student provided'})

@app.route('/api/update_daily_attendance', methods=['POST'])
@login_required
def update_daily_attendance():
    """Update daily attendance for a student"""
    data = request.json
    roll_number = data.get('roll_number')
    date = data.get('date', datetime.now().strftime('%Y-%m-%d'))
    attended = data.get('attended', 0)
    total = data.get('total', 0)
    
    if not roll_number:
        return jsonify({'success': False, 'message': 'No roll number provided'})
    
    # Find which section this student belongs to
    student_section = None
    for section_id, section_config in SECTIONS.items():
        prefix = section_config["prefix"]
        try:
            roll_num = int(roll_number[len(prefix):]) if roll_number.startswith(prefix) else None
            if roll_num and section_config["start"] <= roll_num <= section_config["end"]:
                student_section = section_id
                break
        except (ValueError, TypeError):
            continue
    
    if not student_section:
        return jsonify({'success': False, 'message': 'Student section not found'})
    
    # Load daily attendance data
    daily_attendance = load_daily_attendance()
    
    # Initialize section data if not exists
    if student_section not in daily_attendance:
        daily_attendance[student_section] = {}
    
    # Initialize date data if not exists
    if date not in daily_attendance[student_section]:
        daily_attendance[student_section][date] = {}
    
    # Update student attendance
    daily_attendance[student_section][date][roll_number] = {
        'attended': attended,
        'total': total
    }
    
    # Save updated data
    save_daily_attendance(daily_attendance)
    
    return jsonify({
        'success': True,
        'message': f'Daily attendance updated for {roll_number}',
        'attendance_percentage': calculate_attendance_percentage(roll_number)
    })

@app.route('/api/student/<roll_number>')
@login_required
def get_student_data(roll_number):
    try:
        students_data = load_students_data()
        
        # Get attendance history for this student
        attendance_history = get_student_attendance_history(roll_number)
        
        # Get daily attendance data
        daily_attendance = get_student_daily_attendance(roll_number)
        
        # Calculate attendance percentage
        attendance_percentage = calculate_attendance_percentage(roll_number)
        
        # Find which section this student belongs to
        student_section = None
        for section_id, section_config in SECTIONS.items():
            prefix = section_config["prefix"]
            try:
                roll_num = int(roll_number[len(prefix):]) if roll_number.startswith(prefix) else None
                if roll_num and section_config["start"] <= roll_num <= section_config["end"]:
                    student_section = section_id
                    break
            except (ValueError, TypeError):
                continue
        
        # Default to CSE_5A if section not found
        if not student_section:
            student_section = "CSE_A"
        
        # Process daily attendance to include subject information
        for day in daily_attendance:
            day_name = datetime.strptime(day["date"], "%Y-%m-%d").strftime("%A")
            if student_section and day_name in TIMETABLE.get(student_section, {}):
                subjects_list = TIMETABLE[student_section][day_name]
                # Generate subject attendance data if not already present
                if "subjects" not in day or not day["subjects"]:
                    import random
                    
                    attended_count = day["classes_attended"]
                    subjects = []
                        
                    # Get attendance data for this date
                    date_attendance = attendance_history.get(day["date"], {})
                    
                    for i, subject in enumerate(subjects_list):
                        # Check if this subject has attendance data
                        subject_key = list(date_attendance.keys())[i] if i < len(date_attendance) else None
                        
                        if subject_key and subject_key in date_attendance:
                            # If we have specific data for this subject
                            status = date_attendance[subject_key]
                            if status == "NC":
                                # Not Conducted
                                subjects.append({
                                    "name": subject,
                                    "status": "NC"
                                })
                            elif status == "1/1" or status == "1" or status == "0/1" or status == "0":
                                # Conducted - Present (1) or Absent (0)
                                subjects.append({
                                    "name": subject,
                                    "attended": status == "1/1" or status == "1",
                                    "status": "conducted"
                                })
                        else:
                            # Randomly assign attendance if no specific data
                            attended = False
                            if attended_count > 0:
                                attended = random.choice([True, False])
                                if attended:
                                    attended_count -= 1
                                
                                subjects.append({
                                    "name": subject,
                                    "attended": attended,
                                    "status": "conducted"
                                })
                        
                        day["subjects"] = subjects
        
        # Always try to find student in details.json first (primary source)
        student_details = load_student_details()
        for student in student_details:
            if student.get('rollNo') == roll_number:
                # Make a copy to avoid modifying the original data
                student_data = student.copy()
                
                # Calculate CGPA
                student_data['cgpa'] = calculate_cgpa(student_data.get('sgpas', {}))
                # Add image URL
                student_data['image_url'] = get_student_image_url(roll_number)
                # Add attendance history
                student_data['attendance_history'] = attendance_history
                # Add daily attendance data
                student_data['daily_attendance'] = daily_attendance
                # Add attendance percentage
                student_data['attendance_percentage'] = attendance_percentage
                # Add section information
                student_data['section'] = student_section
                
                # Generate SGPA graph with error handling
                try:
                    if PLOTLY_AVAILABLE and student_data.get('sgpas'):
                        student_data['sgpa_graph'] = create_enhanced_sgpa_graph(student_data.get('sgpas', {}))
                        if not student_data['sgpa_graph']:
                            student_data['sgpa_graph'] = "<div class='alert alert-info'>No SGPA data available for graph generation.</div>"
                except Exception as e:
                    logger.error(f"Error generating SGPA graph in student profile: {str(e)}")
                    student_data['sgpa_graph'] = "<div class='alert alert-warning'>Unable to display SGPA graph. Please try again later.</div>"
                
                logger.info(f"Found student data for {roll_number}: {student_data.get('name', 'Unknown')})")
                
                return jsonify({
                    'success': True,
                    'student': student_data
                })
        
        # Fallback: check if student exists in the legacy students_data
        if roll_number in students_data:
            student = students_data[roll_number]
            # Calculate CGPA
            student['cgpa'] = calculate_cgpa(student.get('sgpas', {}))
            # Add image URL
            student['image_url'] = get_student_image_url(roll_number)
            # Add attendance history
            student['attendance_history'] = attendance_history
            # Add daily attendance data
            student['daily_attendance'] = daily_attendance
            # Add attendance percentage
            student['attendance_percentage'] = attendance_percentage
            # Add section information
            student['section'] = student_section
            
            return jsonify({
                'success': True,
                'student': student
            })
            
            # If not found, create sample data with section information
            sample_student = {
                'rollNo': roll_number,
                'name': f'Student {roll_number}',
                'mobile': f'9{np.random.randint(100000000, 999999999)}',
                'section': 'CSE_A',  # Add default section for sample students
                'sgpas': {
                    '1': str(round(np.random.uniform(7.0, 9.5), 2)),
                    '2': str(round(np.random.uniform(7.0, 9.5), 2)),
                    '3': str(round(np.random.uniform(7.0, 9.5), 2)),
                    '4': str(round(np.random.uniform(7.0, 9.5), 2))
                }
            }
            sample_student['cgpa'] = calculate_cgpa(sample_student['sgpas'])
            # Add image URL
            sample_student['image_url'] = get_student_image_url(roll_number)
            # Add attendance history
            sample_student['attendance_history'] = attendance_history
            # Add daily attendance data
            sample_student['daily_attendance'] = daily_attendance
            # Add attendance percentage
            sample_student['attendance_percentage'] = attendance_percentage
            
            # Generate SGPA graph with error handling
            try:
                if PLOTLY_AVAILABLE:
                    sample_student['sgpa_graph'] = create_enhanced_sgpa_graph(sample_student['sgpas'])
                    if not sample_student['sgpa_graph']:
                        sample_student['sgpa_graph'] = "<div class='alert alert-info'>No SGPA data available for graph generation.</div>"
            except Exception as e:
                logger.error(f"Error generating SGPA graph for sample student: {str(e)}")
                sample_student['sgpa_graph'] = "<div class='alert alert-warning'>Unable to display SGPA graph. Please try again later.</div>"
            
            return jsonify({
                'success': True,
                'student': sample_student
            })
    except Exception as e:
        print(f"Error fetching student data: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"Error fetching student data: {str(e)}"
        })

@app.route('/api/student_details/<roll_number>')
@login_required
def get_student_details(roll_number):
    """Get detailed information for a specific student"""
    student_info = get_student_info(roll_number)
    return jsonify(student_info)

@app.route('/api/teacher_profile')
@login_required
def teacher_profile():
    """Get attendance statistics for the teacher's profile"""
    username = session.get('username')
    faculty_name = session.get('faculty_name')
    user_sections = session.get('sections', [])
    
    # Load attendance data
    attendance_data = load_attendance_data()
    
    # Calculate statistics for each section
    section_stats = {}
    total_classes = 0
    total_present = 0
    total_absent = 0
    
    for section_id in user_sections:
        if section_id in attendance_data:
            section_dates = attendance_data[section_id]
            section_classes = len(section_dates)
            total_classes += section_classes
            
            section_present = 0
            section_absent = 0
            students = get_section_students(section_id)
            total_students = len(students)
            
            # Calculate daily attendance for the section
            daily_attendance = []
            for date, students_status in section_dates.items():
                day_present = sum(1 for status in students_status.values() if status == 1)
                day_absent = total_students - day_present
                attendance_rate = round((day_present / total_students) * 100, 2) if total_students > 0 else 0
                daily_attendance.append({
                    'date': date,
                    'present': day_present,
                    'absent': day_absent,
                    'rate': attendance_rate,
                    'attendance_rate': attendance_rate  # For backward compatibility
                })
                section_present += day_present
                section_absent += day_absent
            
            total_present += section_present
            total_absent += section_absent
            
            # Calculate average attendance rate for the section
            avg_attendance_rate = round((section_present / (section_present + section_absent)) * 100, 2) if (section_present + section_absent) > 0 else 0
            
            # Calculate weekly trends
            sorted_attendance = sorted(daily_attendance, key=lambda x: x['date'])
            weekly_trends = []
            if sorted_attendance:
                # Group by week
                from datetime import datetime, timedelta
                week_data = {}
                for day in sorted_attendance:
                    date_obj = datetime.strptime(day['date'], '%Y-%m-%d')
                    week_start = (date_obj - timedelta(days=date_obj.weekday())).strftime('%Y-%m-%d')
                    if week_start not in week_data:
                        week_data[week_start] = {'present': 0, 'absent': 0, 'total': 0}
                    week_data[week_start]['present'] += day['present']
                    week_data[week_start]['absent'] += day['absent']
                    week_data[week_start]['total'] += 1
                
                # Calculate weekly averages
                for week_start, data in week_data.items():
                    week_rate = round((data['present'] / (data['present'] + data['absent'])) * 100, 2) if (data['present'] + data['absent']) > 0 else 0
                    weekly_trends.append({
                        'week': week_start,
                        'rate': week_rate,
                        'classes': data['total']
                    })
            
            section_stats[section_id] = {
                'name': SECTIONS[section_id]['name'],
                'total_classes': section_classes,
                'total_students': total_students,
                'present_count': section_present,
                'absent_count': section_absent,
                'avg_attendance_rate': avg_attendance_rate,
                'daily_attendance': sorted(daily_attendance, key=lambda x: x['date'], reverse=True),
                'weekly_trends': sorted(weekly_trends, key=lambda x: x['week'])
            }
        else:
            # Add empty stats for sections with no attendance data
            section_stats[section_id] = {
                'name': SECTIONS[section_id]['name'],
                'total_classes': 0,
                'total_students': len(get_section_students(section_id)),
                'present_count': 0,
                'absent_count': 0,
                'avg_attendance_rate': 0,
                'daily_attendance': [],
                'weekly_trends': []
            }
    
    # Calculate overall attendance rate
    overall_rate = round((total_present / (total_present + total_absent)) * 100, 2) if (total_present + total_absent) > 0 else 0
    
    return jsonify({
        'username': username,
        'faculty_name': faculty_name,
        'total_classes': total_classes,
        'total_present': total_present,
        'total_absent': total_absent,
        'overall_attendance_rate': overall_rate,
        'section_stats': section_stats
    })

@app.route('/api/export_excel')
@login_required
def export_excel():
    section = request.args.get('section')
    if not section:
        return jsonify({'error': 'No section provided'})
    
    buffer = create_attendance_excel(section, present_students)
    filename = f"Attendance_{SECTIONS[section]['name'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@app.route('/api/save_manual_attendance', methods=['POST'])
@login_required
def save_manual_attendance():
    data = request.json
    section = data.get('section')
    attendance = data.get('attendance')
    
    if not section or not attendance:
        return jsonify({'success': False, 'message': 'Section and attendance data are required'})
    
    # Check if user has access to this section
    user_sections = session.get('sections', [])
    user_type = session.get('user_type', 'faculty')  # Default to faculty for this route
    
    # Only faculty should be able to save attendance and they need proper section access
    if user_type != 'faculty' or section not in user_sections:
        return jsonify({'success': False, 'message': 'You do not have access to this section'})
    
    # Load current attendance data
    attendance_data = load_attendance_data()
    date_str = datetime.now().strftime('%Y-%m-%d')
    
    # Initialize section and date if they don't exist
    if section not in attendance_data:
        attendance_data[section] = {}
    if date_str not in attendance_data[section]:
        attendance_data[section][date_str] = {}
    
    # Update attendance data with manual entries
    for entry in attendance:
        roll_number = entry.get('roll_number')
        status_text = entry.get('status')
        
        # Handle different status values (case-insensitive)
        if status_text.lower() == 'present':
            status = 1
        elif status_text.lower() == 'absent':
            status = 0
        elif status_text.upper() == 'NC':
            status = 'NC'  # Store NC as a string to differentiate from numeric values
        else:
            # Invalid status
            return jsonify({'success': False, 'message': f'Invalid status: {status_text}'})
            
        attendance_data[section][date_str][roll_number] = status
    
    # Save updated attendance data
    save_attendance_data(attendance_data)
    
    # Update present_students set to match the manual attendance
    global present_students
    present_students = set()
    for entry in attendance:
        if entry.get('status').lower() == 'present':
            present_students.add(entry.get('roll_number'))
    
    return jsonify({'success': True, 'message': 'Attendance saved successfully'})

@app.route('/api/export_csv')
@login_required
def export_csv():
    section = request.args.get('section')
    if not section:
        return jsonify({'error': 'No section provided'})
    
    all_students = get_section_students(section)
    student_details = load_student_details()
    student_map = {student['rollNo']: student for student in student_details}
    
    attendance_data = []
    
    for i, student in enumerate(all_students, 1):
        student_info = student_map.get(student, {
            'name': f"Student {student}",
            'mobile': 'N/A'
        })
        
        status = "Present" if student in present_students else "Absent"
        attendance_data.append({
            "S.No": i,
            "Roll Number": student,
            "Student Name": student_info['name'],
            "Mobile": student_info['mobile'],
            "Status": status,
            "Section": SECTIONS[section]["name"]
        })
    
    df = pd.DataFrame(attendance_data)
    csv_data = df.to_csv(index=False)
    
    filename = f"Attendance_{SECTIONS[section]['name'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )

@app.route('/api/send_attendance_emails', methods=['POST'])
@login_required
def send_attendance_emails():
    """Send attendance emails to students with low attendance who were absent in the most recent class"""
    try:
        section = request.json.get('section')
        if not section:
            return jsonify({'success': False, 'message': 'No section provided'})
        
        # Check if user has access to this section
        user_sections = session.get('sections', [])
        user_type = session.get('user_type', 'faculty')  # Default to faculty for this route
        
        # Only faculty should be able to send emails and they need proper section access
        if user_type != 'faculty' or section not in user_sections:
            return jsonify({'success': False, 'message': 'You do not have access to this section'})
        
        # Get all students in the section
        students = get_section_students(section)
        student_details = load_student_details()
        
        # Count emails sent
        emails_sent = 0
        emails_failed = 0
        emails_skipped = 0
        
        for student_roll in students:
            # Check if student was absent in the most recent class
            if not check_if_student_absent(student_roll):
                emails_skipped += 1
                logger.info(f"Skipping email for {student_roll} as they were present in the last class")
                continue
            
            # Get student details
            student_info = None
            for student in student_details:
                if student['rollNo'] == student_roll:
                    student_info = student
                    break
            
            if not student_info:
                student_info = {
                    'rollNo': student_roll,
                    'name': f"Student {student_roll}",
                    'mobile': 'N/A'
                }
            
            # Calculate attendance percentage
            attendance_percentage = calculate_attendance_percentage(student_roll)
            
            # Get daily attendance data
            daily_attendance = get_student_daily_attendance(student_roll)
            
            # Calculate total classes and classes attended
            total_classes = sum(day["total_classes"] for day in daily_attendance)
            classes_attended = sum(day["classes_attended"] for day in daily_attendance)
            missed_classes = total_classes - classes_attended
            
            # Calculate classes needed to reach 80%
            classes_to_80 = 0
            if attendance_percentage < 80 and total_classes > 0:
                # Formula: (0.8 * total_classes - classes_attended) / 0.2
                classes_to_80 = max(0, int((0.8 * total_classes - classes_attended) / 0.2) + 1)
            
            # Send email if attendance is below 80%
            if attendance_percentage < 80:
                success = send_attendance_email(
                    student_roll, 
                    student_info['name'], 
                    attendance_percentage, 
                    classes_attended, 
                    total_classes, 
                    classes_to_80,
                    missed_classes
                )
                
                if success:
                    emails_sent += 1
                else:
                    emails_failed += 1
        
        return jsonify({
            'success': True,
            'message': f'Sent {emails_sent} emails, skipped {emails_skipped} emails for present students, failed {emails_failed} emails',
            'details': {
                'sent': emails_sent,
                'skipped': emails_skipped,
                'failed': emails_failed
            }
        })
        
    except Exception as e:
        logger.error(f"Error sending attendance emails: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error sending attendance emails: {str(e)}'
        })

@app.route('/video_feed')
@login_required
def video_feed():
    def generate():
        global camera_processor
        
        while True:
            try:
                if camera_processor and camera_processor.is_running:
                    frame_with_boxes = camera_processor.get_display_frame_with_boxes()
                    
                    # Encode frame as JPEG with lower quality for better performance
                    ret, jpeg = cv2.imencode('.jpg', frame_with_boxes, 
                                            [cv2.IMWRITE_JPEG_QUALITY, 70])
                    if ret:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')
                    else:
                        # Create a placeholder frame
                        placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
                        cv2.putText(placeholder, "Encoding error", (150, 240), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                        ret, jpeg = cv2.imencode('.jpg', placeholder)
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')
                else:
                    # Create a placeholder frame when camera is not running
                    placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
                    cv2.putText(placeholder, "Camera not active", (150, 240), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                    ret, jpeg = cv2.imencode('.jpg', placeholder)
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')
                
                time.sleep(0.05)  # Control frame rate
            except Exception as e:
                logger.error(f"Video feed error: {e}")
                # Create an error frame
                error_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(error_frame, f"Error: {str(e)}", (50, 240), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                ret, jpeg = cv2.imencode('.jpg', error_frame)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')
                time.sleep(1)
    
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/recognition_status')
@login_required
def recognition_status():
    global camera_processor, present_students
    
    if camera_processor:
        return jsonify({
            'fps': round(camera_processor.fps, 1),
            'faces_detected': len(camera_processor.recognition_results),
            'present_count': len(present_students),
            'recognition_results': camera_processor.recognition_results,
            'present_students': list(present_students)[-8:] if present_students else []
        })
    
    return jsonify({
        'fps': 0,
        'faces_detected': 0,
        'present_count': len(present_students),
        'recognition_results': [],
        'present_students': list(present_students)[-8:] if present_students else []
    })

@app.route('/api/timetable')
@login_required
def get_timetable():
    """Get timetable data from timetable.json"""
    try:
        with open('timetable.json', 'r') as f:
            timetable_data = json.load(f)
        return jsonify({
            'success': True,
            'timetable': timetable_data
        })
    except FileNotFoundError:
        return jsonify({
            'success': False,
            'message': 'Timetable file not found'
        })
    except Exception as e:
        logger.error(f"Error loading timetable: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error loading timetable: {str(e)}'
        })

@app.route('/api/student_attendance/<roll_number>')
@login_required
def get_student_attendance(roll_number):
    """Get student attendance data from attendance.json"""
    try:
        attendance_data = load_attendance_data()
        
        # Find which section the student belongs to
        student_section = None
        student_attendance = {}
        
        for section, section_data in attendance_data.items():
            for date, date_data in section_data.items():
                if roll_number in date_data:
                    student_section = section
                    if date not in student_attendance:
                        student_attendance[date] = {}
                    student_attendance[date][roll_number] = date_data[roll_number]
        
        return jsonify({
            'success': True,
            'attendance': student_attendance,
            'section': student_section
        })
    except Exception as e:
        logger.error(f"Error loading student attendance: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error loading student attendance: {str(e)}'
        })

# ========== ONLINE ATTENDANCE API ENDPOINTS ==========

@app.route('/api/online/create_session', methods=['POST'])
@login_required
def create_online_session():
    """Create a new online class session"""
    try:
        logger.info("Creating online session...")
        
        # Check if online attendance is available
        if online_attendance is None:
            logger.error("Online attendance system not available")
            return jsonify({'success': False, 'message': 'Online attendance system not available'})
            
        data = request.json
        logger.info(f"Request data: {data}")
        
        section_id = data.get('section_id')
        subject = data.get('subject')
        class_type = data.get('class_type', 'lecture')
        duration = data.get('duration_minutes', 90)
        jitsi_link = data.get('jitsi_link')  # Get Jitsi link from request
        
        logger.info(f"Parsed data - section_id: {section_id}, subject: {subject}, class_type: {class_type}, duration: {duration}")
        
        if not section_id or not subject:
            logger.error("Missing section_id or subject")
            return jsonify({'success': False, 'message': 'Section and subject are required'})
        
        # Validate Jitsi link is provided and has correct format
        if not jitsi_link:
            logger.error("Missing Jitsi link")
            return jsonify({'success': False, 'message': 'Jitsi Meeting Link is required'})
        
        # Basic URL validation for Jitsi link
        if not (jitsi_link.startswith('http://') or jitsi_link.startswith('https://')):
            logger.error(f"Invalid Jitsi link format: {jitsi_link}")
            return jsonify({'success': False, 'message': 'Jitsi link must be a valid URL (starting with http:// or https:///)'})
        
        logger.info(f"Jitsi link validated: {jitsi_link}")
        
        # Check if user has access to this section
        user_sections = session.get('sections', [])
        user_type = session.get('user_type', 'faculty')
        
        logger.info(f"User sections: {user_sections}, user_type: {user_type}")
        
        if user_type != 'faculty':
            logger.error(f"User type is not faculty: {user_type}")
            return jsonify({'success': False, 'message': 'Only faculty can create sessions'})
            
        if section_id not in user_sections:
            logger.error(f"User does not have access to section {section_id}")
            return jsonify({'success': False, 'message': f'You do not have access to section {section_id}'})
        
        faculty_username = session.get('username')
        logger.info(f"Creating session for faculty: {faculty_username}")
        
        session_id, session_data = online_attendance.create_online_session(
            faculty_username, section_id, subject, class_type, duration, jitsi_link
        )
        
        logger.info(f"Session created successfully: {session_id}")
        
        return jsonify({
            'success': True,
            'message': 'Online session created successfully',
            'session_id': session_id,
            'session_data': session_data
        })
        
    except Exception as e:
        logger.error(f"Error creating online session: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'})

@app.route('/api/online/active_sessions')
@cross_origin(origins=['http://localhost:5000', 'https://meet.jit.si', 'http://meet.jit.si', 'file://', 'null'], methods=['GET', 'OPTIONS'], supports_credentials=True)
def get_active_online_sessions():
    """Get all active online sessions - accessible to both faculty and students"""
    try:
        # Check if online attendance is available
        if online_attendance is None:
            return jsonify({'success': True, 'sessions': []})
            
        # Check if user is logged in
        is_authenticated = 'authenticated' in session and session['authenticated']
        
        if is_authenticated:
            faculty_username = session.get('username')
            user_type = session.get('user_type', 'faculty')
            
            if user_type == 'faculty':
                active_sessions = online_attendance.get_active_sessions(faculty_username)
            else:
                # Students can see all active sessions
                active_sessions = online_attendance.get_active_sessions()
        else:
            # Anonymous access - return all active sessions for students
            active_sessions = online_attendance.get_active_sessions()
        
        return jsonify({
            'success': True,
            'sessions': active_sessions
        })
        
    except Exception as e:
        logger.error(f"Error getting active sessions: {str(e)}")
        return jsonify({'success': True, 'sessions': []})

@app.route('/api/online/generate_token', methods=['POST'])
@login_required
def generate_attendance_token():
    """Generate a time-limited attendance token"""
    try:
        data = request.json
        session_id = data.get('session_id')
        validity_minutes = data.get('validity_minutes', 8)
        
        if not session_id:
            return jsonify({'success': False, 'message': 'Session ID is required'})
        
        user_type = session.get('user_type', 'faculty')
        if user_type != 'faculty':
            return jsonify({'success': False, 'message': 'Only faculty can generate tokens'})
        
        token_data, error = online_attendance.generate_attendance_token(session_id, validity_minutes)
        
        if error:
            return jsonify({'success': False, 'message': error})
        
        return jsonify({
            'success': True,
            'message': 'Token generated successfully',
            'token_data': token_data
        })
        
    except Exception as e:
        logger.error(f"Error generating token: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/online/mark_attendance_token', methods=['POST'])
@login_required
def mark_attendance_with_token():
    """Mark attendance using token code"""
    try:
        data = request.json
        token_code = data.get('token_code')
        
        if not token_code:
            return jsonify({'success': False, 'message': 'Token code is required'})
        
        student_roll = session.get('username').upper()
        user_type = session.get('user_type')
        
        # Only students can mark attendance (or faculty viewing as student)
        if user_type == 'faculty' and not data.get('student_roll'):
            return jsonify({'success': False, 'message': 'Faculty cannot mark attendance for themselves'})
        
        # If faculty is marking for a student, use provided roll number
        if user_type == 'faculty' and data.get('student_roll'):
            student_roll = data.get('student_roll').upper()
        
        success, message = online_attendance.mark_attendance_with_token(token_code, student_roll)
        
        return jsonify({
            'success': success,
            'message': message
        })
        
    except Exception as e:
        logger.error(f"Error marking attendance with token: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/online/send_jitsi_popup', methods=['POST'])
@cross_origin(origins=['*'], methods=['POST', 'OPTIONS'])
@login_required
def send_jitsi_attendance_popup():
    """Send attendance popup to Jitsi meeting participants"""
    try:
        data = request.json
        session_id = data.get('session_id')
        question = data.get('question', 'Are you present?')
        options = data.get('options', ["Yes, I'm present", "No"])
        expiry_minutes = data.get('expiry_minutes', 2)
        
        if not session_id:
            return jsonify({'success': False, 'message': 'Session ID is required'})
        
        user_type = session.get('user_type', 'faculty')
        if user_type != 'faculty':
            return jsonify({'success': False, 'message': 'Only faculty can send Jitsi popups'})
        
        popup_data, error = online_attendance.send_jitsi_attendance_popup(
            session_id, question, options, expiry_minutes
        )
        
        if error:
            return jsonify({'success': False, 'message': error})
        
        return jsonify({
            'success': True,
            'message': f'Attendance popup sent to {popup_data["target_students_count"]} students in Jitsi room "{popup_data["room_name"]}"',
            'popup_data': popup_data
        })
        
    except Exception as e:
        logger.error(f"Error sending Jitsi popup: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/online/jitsi_attendance', methods=['POST'])
@cross_origin(origins=['http://localhost:5000', 'https://meet.jit.si', 'http://meet.jit.si', 'file://', 'null'], methods=['POST', 'OPTIONS'], supports_credentials=True)
def mark_jitsi_attendance():
    """Mark attendance from Jitsi response"""
    try:
        data = request.json
        session_id = data.get('session_id')
        student_roll = data.get('student_roll')
        response_method = data.get('method', 'jitsi_popup')  # 'jitsi_popup', 'jitsi_chat', 'raise_hand', etc.
        participant_name = data.get('participant_name', '')
        
        if not session_id or not student_roll:
            return jsonify({'success': False, 'message': 'Session ID and student roll are required'})
        
        response_data = {
            'method': response_method,
            'timestamp': datetime.now().isoformat(),
            'source': 'jitsi_integration',
            'participant_name': participant_name
        }
        
        success, message = online_attendance.handle_jitsi_attendance_response(session_id, student_roll, response_data)
        
        return jsonify({
            'success': success,
            'message': message
        })
        
    except Exception as e:
        logger.error(f"Error marking Jitsi attendance: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/online/jitsi_popup_status/<session_id>')
@cross_origin(origins=['http://localhost:5000', 'https://meet.jit.si', 'http://meet.jit.si', 'file://', 'null'], methods=['GET', 'OPTIONS'], supports_credentials=True)
def get_jitsi_popup_status(session_id):
    """Get status of current Jitsi popup for a session"""
    try:
        popup_status = online_attendance.get_jitsi_popup_status(session_id)
        
        if popup_status is None:
            return jsonify({
                'success': True,
                'has_active_popup': False,
                'message': 'No active Jitsi popup for this session'
            })
        
        return jsonify({
            'success': True,
            'has_active_popup': True,
            'popup_status': popup_status
        })
        
    except Exception as e:
        logger.error(f"Error getting Jitsi popup status: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/zoom/webhook', methods=['POST'])
def zoom_webhook():
    """Handle Zoom webhook events for poll responses and meeting events"""
    try:
        data = request.json
        event_type = data.get('event')
        
        logger.info(f"Received Zoom webhook: {event_type}")
        
        if event_type == 'meeting.poll_started':
            # Handle poll started event
            meeting_id = data.get('payload', {}).get('object', {}).get('id')
            poll_id = data.get('payload', {}).get('object', {}).get('polls', [{}])[0].get('id')
            logger.info(f"Poll started in meeting {meeting_id}: {poll_id}")
            
        elif event_type == 'meeting.poll_ended':
            # Handle poll ended event and collect responses
            meeting_data = data.get('payload', {}).get('object', {})
            meeting_id = meeting_data.get('id')
            polls = meeting_data.get('polls', [])
            
            for poll in polls:
                poll_id = poll.get('id')
                questions = poll.get('questions', [])
                
                for question in questions:
                    answers = question.get('answers', [])
                    for answer in answers:
                        participant_name = answer.get('name', '')
                        selected_answer = answer.get('answer', '')
                        
                        # Process attendance based on poll response
                        if selected_answer.lower() in ['present', 'here', 'attending']:
                            # Try to map participant name to student roll number
                            student_roll = extract_roll_from_name(participant_name)
                            if student_roll:
                                # Find the session associated with this meeting
                                session_id = find_session_by_meeting_id(meeting_id)
                                if session_id:
                                    response_data = {
                                        'method': 'zoom_poll',
                                        'participant_name': participant_name,
                                        'poll_answer': selected_answer,
                                        'timestamp': datetime.now().isoformat()
                                    }
                                    
                                    success, message = online_attendance.handle_zoom_attendance_response(
                                        session_id, student_roll, response_data
                                    )
                                    
                                    if success:
                                        logger.info(f"Marked attendance for {student_roll} via Zoom poll")
        
        elif event_type == 'meeting.participant_joined':
            # Track participant joining
            participant = data.get('payload', {}).get('object', {}).get('participant', {})
            participant_name = participant.get('user_name', '')
            meeting_id = data.get('payload', {}).get('object', {}).get('id')
            logger.info(f"Participant {participant_name} joined meeting {meeting_id}")
            
        return jsonify({'status': 'success', 'message': 'Webhook processed'})
        
    except Exception as e:
        logger.error(f"Error processing Zoom webhook: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/zoom/chat_webhook', methods=['POST'])
def zoom_chat_webhook():
    """Handle Zoom chat messages for attendance responses"""
    try:
        data = request.json
        event_type = data.get('event')
        
        if event_type == 'meeting.chat_message_sent':
            payload = data.get('payload', {})
            message_data = payload.get('object', {})
            
            meeting_id = message_data.get('meeting_id')
            sender_name = message_data.get('sender', '')
            message_content = message_data.get('message', '').lower().strip()
            
            # Check if message is attendance response
            attendance_keywords = ['present', 'here', 'attending', 'i am present', 'i am here']
            
            if any(keyword in message_content for keyword in attendance_keywords):
                # Extract student roll number from sender name
                student_roll = extract_roll_from_name(sender_name)
                
                if student_roll:
                    # Find session associated with this meeting
                    session_id = find_session_by_meeting_id(meeting_id)
                    
                    if session_id:
                        response_data = {
                            'method': 'zoom_chat',
                            'participant_name': sender_name,
                            'chat_message': message_content,
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        success, message = online_attendance.handle_zoom_attendance_response(
                            session_id, student_roll, response_data
                        )
                        
                        if success:
                            logger.info(f"Marked attendance for {student_roll} via Zoom chat")
        
        return jsonify({'status': 'success'})
        
    except Exception as e:
        logger.error(f"Error processing Zoom chat webhook: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 400

def extract_roll_from_name(participant_name):
    """Extract student roll number from participant name"""
    import re
    
    participant_name_upper = participant_name.upper()
    
    # Enhanced patterns to match the JavaScript version
    patterns = [
        # Pattern 1: Roll number in parentheses - "Name (23CSEDS001)"
        r'\([^)]*?(\d{2}[A-Z]{2,6}\d{2,3})[^)]*?\)',
        # Pattern 2: Roll number at end with space - "Name 23CSEDS001"
        r'\s(\d{2}[A-Z]{2,6}\d{2,3})\s*$',
        # Pattern 3: Roll number at start - "23CSEDS001 Name"
        r'^(\d{2}[A-Z]{2,6}\d{2,3})\s+',
        # Pattern 4: Roll number anywhere in the text
        r'\b(\d{2}[A-Z]{2,6}\d{2,3})\b',
        # Pattern 5: More specific patterns for common formats
        r'(\d{2}CSE[A-Z]*\d{2,3})',
        r'(\d{2}BCA\d{2,3})',
        r'(\d{2}MCA\d{2,3})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, participant_name_upper)
        if match:
            roll_number = match.group(1)
            print(f"✅ Extracted roll number '{roll_number}' from participant name '{participant_name}'")
            return roll_number
    
    print(f"❌ Could not extract roll number from participant name '{participant_name}'")
    return None

def find_session_by_meeting_id(meeting_id):
    """Find active session associated with a Zoom meeting ID"""
    try:
        if online_attendance:
            sessions = online_attendance._load_online_sessions()
            
            for session_id, session_data in sessions.items():
                if (session_data.get('status') == 'active' and 
                    session_data.get('current_zoom_popup', {}).get('zoom_meeting_id') == meeting_id):
                    return session_id
                    
                # Also check zoom_link for meeting ID
                zoom_link = session_data.get('zoom_link', '')
                if meeting_id in zoom_link:
                    return session_id
        
        return None
    except Exception as e:
        logger.error(f"Error finding session by meeting ID: {str(e)}")
        return None

@app.route('/api/zoom/test')
@login_required  
def test_zoom_integration():
    """Test Zoom integration setup"""
    try:
        import os
        from zoom_config import ZoomIntegration
        
        # Check environment variables
        api_key = os.getenv('ZOOM_API_KEY')
        api_secret = os.getenv('ZOOM_API_SECRET')
        account_id = os.getenv('ZOOM_ACCOUNT_ID')
        
        result = {
            'environment_variables': {
                'api_key_set': bool(api_key),
                'api_secret_set': bool(api_secret),
                'account_id_set': bool(account_id),
                'api_key_preview': api_key[:8] + '...' if api_key else None
            },
            'integration_test': {},
            'recommendations': []
        }
        
        if api_key and api_secret and account_id:
            # Test Zoom integration
            zoom = ZoomIntegration(api_key, api_secret, account_id)
            
            # Test JWT token generation
            token = zoom.generate_jwt_token()
            result['integration_test']['jwt_token'] = bool(token)
            
            if token:
                result['integration_test']['status'] = '✅ Ready for live Zoom integration'
                result['recommendations'].append('You can now send real popups to Zoom meetings!')
            else:
                result['integration_test']['status'] = '❌ JWT token generation failed'
                result['recommendations'].append('Check your API credentials')
        else:
            result['integration_test']['status'] = '⚠️ Environment variables not configured'
            result['recommendations'].extend([
                '1. Run setup_zoom_env.bat to configure credentials',
                '2. Create a Zoom app at https://marketplace.zoom.us/develop/create',
                '3. Restart your Flask server after setting environment variables'
            ])
        
        return jsonify({
            'success': True,
            'zoom_integration_status': result
        })
        
    except ImportError:
        return jsonify({
            'success': False,
            'error': 'zoom_config module not found',
            'recommendations': ['Ensure zoom_config.py exists in your project directory']
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'recommendations': ['Check server logs for detailed error information']
        })

@app.route('/api/online/create_poll', methods=['POST'])
@login_required
def create_poll():
    """Create an interactive poll for attendance"""
    try:
        data = request.json
        session_id = data.get('session_id')
        question = data.get('question')
        options = data.get('options', [])
        correct_answer = data.get('correct_answer')
        duration_minutes = data.get('duration_minutes', 5)
        
        if not session_id or not question or not options:
            return jsonify({'success': False, 'message': 'Session ID, question, and options are required'})
        
        user_type = session.get('user_type', 'faculty')
        if user_type != 'faculty':
            return jsonify({'success': False, 'message': 'Only faculty can create polls'})
        
        poll_data, error = online_attendance.create_poll(
            session_id, question, options, correct_answer, duration_minutes
        )
        
        if error:
            return jsonify({'success': False, 'message': error})
        
        return jsonify({
            'success': True,
            'message': 'Poll created successfully',
            'poll_data': poll_data
        })
        
    except Exception as e:
        logger.error(f"Error creating poll: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/online/submit_poll', methods=['POST'])
@login_required
def submit_poll_response():
    """Submit response to a poll"""
    try:
        data = request.json
        poll_id = data.get('poll_id')
        answer = data.get('answer')
        
        if not poll_id or not answer:
            return jsonify({'success': False, 'message': 'Poll ID and answer are required'})
        
        student_roll = session.get('username').upper()
        user_type = session.get('user_type')
        
        # If faculty is submitting for a student, use provided roll number
        if user_type == 'faculty' and data.get('student_roll'):
            student_roll = data.get('student_roll').upper()
        
        success, message = online_attendance.submit_poll_response(poll_id, student_roll, answer)
        
        return jsonify({
            'success': success,
            'message': message
        })
        
    except Exception as e:
        logger.error(f"Error submitting poll response: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/online/poll_results/<session_id>')
@login_required
def get_poll_results(session_id):
    """Get poll results for a session"""
    try:
        poll_id = request.args.get('poll_id')
        
        user_type = session.get('user_type', 'faculty')
        if user_type != 'faculty':
            return jsonify({'success': False, 'message': 'Only faculty can view poll results'})
        
        results = online_attendance.get_poll_results(session_id, poll_id)
        
        if results is None:
            return jsonify({'success': False, 'message': 'Poll not found'})
        
        return jsonify({
            'success': True,
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Error getting poll results: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/online/session_summary/<session_id>')
@login_required
def get_session_attendance_summary(session_id):
    """Get comprehensive attendance summary for a session"""
    try:
        user_type = session.get('user_type', 'faculty')
        if user_type != 'faculty':
            return jsonify({'success': False, 'message': 'Only faculty can view session summaries'})
        
        summary = online_attendance.get_session_attendance_summary(session_id)
        
        if summary is None:
            return jsonify({'success': False, 'message': 'Session not found'})
        
        return jsonify({
            'success': True,
            'summary': summary
        })
        
    except Exception as e:
        logger.error(f"Error getting session summary: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/online/close_session', methods=['POST'])
@login_required
def close_online_session():
    """Close an online session and save final attendance"""
    try:
        data = request.json
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({'success': False, 'message': 'Session ID is required'})
        
        user_type = session.get('user_type', 'faculty')
        if user_type != 'faculty':
            return jsonify({'success': False, 'message': 'Only faculty can close sessions'})
        
        success, message = online_attendance.close_session(session_id)
        
        return jsonify({
            'success': success,
            'message': message
        })
        
    except Exception as e:
        logger.error(f"Error closing session: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/online/save_attendance', methods=['POST'])
@login_required
def save_session_attendance():
    """Save online session attendance to main attendance system"""
    try:
        data = request.json
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({'success': False, 'message': 'Session ID is required'})
        
        user_type = session.get('user_type', 'faculty')
        if user_type != 'faculty':
            return jsonify({'success': False, 'message': 'Only faculty can save attendance'})
        
        success, message = online_attendance.save_session_attendance(session_id)
        
        return jsonify({
            'success': success,
            'message': message
        })
        
    except Exception as e:
        logger.error(f"Error saving session attendance: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/online/session_attendance/<session_id>')
@login_required
def get_session_attendance_details(session_id):
    """Get detailed attendance records for a specific session"""
    try:
        user_type = session.get('user_type', 'faculty')
        if user_type != 'faculty':
            return jsonify({'success': False, 'message': 'Only faculty can view attendance details'})
        
        if online_attendance is None:
            return jsonify({'success': False, 'message': 'Online attendance system not available'})
        
        attendance_records = online_attendance.get_session_attendance_details(session_id)
        
        return jsonify({
            'success': True,
            'attendance': attendance_records
        })
        
    except Exception as e:
        logger.error(f"Error getting session attendance details: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/online/end_session', methods=['POST'])
@login_required
def end_online_session():
    """End an online session and save final attendance"""
    try:
        data = request.json
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({'success': False, 'message': 'Session ID is required'})
        
        user_type = session.get('user_type', 'faculty')
        if user_type != 'faculty':
            return jsonify({'success': False, 'message': 'Only faculty can end sessions'})
        
        # First save attendance
        save_success, save_message = online_attendance.save_session_attendance(session_id)
        
        # Then close the session
        close_success, close_message = online_attendance.close_session(session_id)
        
        if save_success and close_success:
            return jsonify({
                'success': True,
                'message': f'Session ended successfully. {save_message}'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Error ending session: {save_message}, {close_message}'
            })
        
    except Exception as e:
        logger.error(f"Error ending session: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

# ========== POPUP ATTENDANCE SYSTEM ==========

@app.route('/api/online/send_popup_attendance', methods=['POST'])
@login_required
def send_popup_attendance():
    """Send popup attendance notification to all students in a session"""
    try:
        data = request.json
        session_id = data.get('session_id')
        message = data.get('message', 'Please confirm your attendance')
        duration_minutes = data.get('duration_minutes', 3)
        
        if not session_id:
            return jsonify({'success': False, 'message': 'Session ID is required'})
        
        user_type = session.get('user_type', 'faculty')
        if user_type != 'faculty':
            return jsonify({'success': False, 'message': 'Only faculty can send popup attendance'})
        
        popup_data, error = online_attendance.create_popup_attendance(
            session_id, message, duration_minutes
        )
        
        if error:
            return jsonify({'success': False, 'message': error})
        
        return jsonify({
            'success': True,
            'message': 'Popup attendance sent successfully',
            'popup_id': popup_data['popup_id'],
            'students_count': popup_data['students_count']
        })
        
    except Exception as e:
        logger.error(f"Error sending popup attendance: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/online/popup_status/<popup_id>')
@login_required
def get_popup_status(popup_id):
    """Get real-time status of popup attendance"""
    try:
        user_type = session.get('user_type', 'faculty')
        if user_type != 'faculty':
            return jsonify({'success': False, 'message': 'Only faculty can view popup status'})
        
        status_data = online_attendance.get_popup_status(popup_id)
        
        if status_data is None:
            return jsonify({'success': False, 'message': 'Popup not found'})
        
        return jsonify({
            'success': True,
            'data': status_data
        })
        
    except Exception as e:
        logger.error(f"Error getting popup status: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/online/respond_popup', methods=['POST'])
@login_required
def respond_to_popup():
    """Student responds to popup attendance"""
    try:
        data = request.json
        popup_id = data.get('popup_id')
        
        if not popup_id:
            return jsonify({'success': False, 'message': 'Popup ID is required'})
        
        student_roll = session.get('username').upper()
        user_type = session.get('user_type')
        
        # If faculty is responding for a student, use provided roll number
        if user_type == 'faculty' and data.get('student_roll'):
            student_roll = data.get('student_roll').upper()
        
        success, message = online_attendance.respond_to_popup(popup_id, student_roll)
        
        return jsonify({
            'success': success,
            'message': message
        })
        
    except Exception as e:
        logger.error(f"Error responding to popup: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/online/student_popups')
@cross_origin(origins=['*'], methods=['GET', 'OPTIONS'])
def get_student_popups():
    """Get active popup notifications for a student"""
    try:
        student_roll = session.get('username').upper()
        user_type = session.get('user_type')
        
        # If faculty is checking for a specific student
        if user_type == 'faculty' and request.args.get('student_roll'):
            student_roll = request.args.get('student_roll').upper()
        
        active_popups = online_attendance.get_active_popups_for_student(student_roll)
        
        return jsonify({
            'success': True,
            'popups': active_popups
        })
        
    except Exception as e:
        logger.error(f"Error getting student popups: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

# ========== END POPUP ATTENDANCE ENDPOINTS ==========

# ========== END ONLINE ATTENDANCE ENDPOINTS ==========

if __name__ == '__main__':
    app.run(debug=True, threaded=True, host='0.0.0.0', port=5000)
