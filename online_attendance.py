"""
Online Attendance Module - Hybrid Token + Polling System
Handles both time-based tokens and interactive polling for online classes
"""

import json
import secrets
import time
import os
from datetime import datetime, timedelta

class OnlineAttendanceManager:
    def __init__(self, app_root):
        self.app_root = app_root
        self.online_sessions_file = os.path.join(app_root, 'online_sessions.json')
        self.online_attendance_file = os.path.join(app_root, 'online_attendance.json')
        
    # ========== SESSION MANAGEMENT ==========
    
    def create_online_session(self, faculty_username, section_id, 
                            subject, class_type="lecture", 
                            duration_minutes=90, jitsi_link=None):
        """Create a new online class session"""
        session_id = self._generate_session_id()
        current_time = datetime.now()
        
        session_data = {
            'session_id': session_id,
            'faculty_username': faculty_username,
            'section_id': section_id,
            'subject': subject,
            'class_type': class_type,
            'start_time': current_time.isoformat(),
            'end_time': (current_time + timedelta(minutes=duration_minutes)).isoformat(),
            'status': 'active',
            'created_at': current_time.isoformat(),
            'jitsi_link': jitsi_link,  # Store Jitsi meeting link
            
            # Token system data
            'current_token': None,
            'token_history': [],
            
            # Polling system data
            'polls': [],
            'current_poll': None,
            
            # Jitsi integration data
            'jitsi_popups': [],  # Track Jitsi popups sent
            'jitsi_responses': {},  # Student responses from Jitsi
            'jitsi_participants': {},  # Track Jitsi participants
            
            # Attendance tracking
            'attendees': {},  # {roll_number: {method: 'token'/'poll'/'jitsi', marked_at: timestamp, details: {}}}
            'attendance_summary': {
                'total_tokens': 0,
                'total_polls': 0,
                'total_jitsi_responses': 0,
                'unique_attendees': 0
            }
        }
        
        sessions = self._load_online_sessions()
        sessions[session_id] = session_data
        self._save_online_sessions(sessions)
        
        return session_id, session_data
    
    def get_active_sessions(self, faculty_username=None):
        """Get all active online sessions"""
        sessions = self._load_online_sessions()
        active_sessions = []
        current_time = datetime.now()
        
        for session_id, session in sessions.items():
            if session['status'] == 'active':
                end_time = datetime.fromisoformat(session['end_time'])
                
                if current_time <= end_time:
                    if not faculty_username or session['faculty_username'] == faculty_username:
                        active_sessions.append({
                            'session_id': session_id,
                            **session
                        })
                else:
                    # Auto-expire sessions
                    session['status'] = 'expired'
                    
        self._save_online_sessions(sessions)
        return active_sessions
    
    def close_session(self, session_id):
        """Close an online session and save final attendance"""
        sessions = self._load_online_sessions()
        
        if session_id not in sessions:
            return False, "Session not found"
            
        session = sessions[session_id]
        session['status'] = 'closed'
        session['end_time'] = datetime.now().isoformat()
        
        # Save to main attendance system
        self._save_to_main_attendance(session)
        
        sessions[session_id] = session
        self._save_online_sessions(sessions)
        
        return True, "Session closed successfully"
    
    def save_session_attendance(self, session_id):
        """Save current session attendance to main attendance system"""
        sessions = self._load_online_sessions()
        
        if session_id not in sessions:
            return False, "Session not found"
            
        session = sessions[session_id]
        
        # Save to main attendance system
        try:
            self._save_to_main_attendance(session)
            return True, f"Attendance saved successfully for {len(session['attendees'])} students"
        except Exception as e:
            return False, f"Error saving attendance: {str(e)}"
    
    # ========== POPUP ATTENDANCE SYSTEM ==========
    
    def create_popup_attendance(self, session_id, message, duration_minutes=3):
        """Create a popup attendance request for all students in a session"""
        sessions = self._load_online_sessions()
        
        if session_id not in sessions:
            return None, "Session not found"
            
        session = sessions[session_id]
        
        if session['status'] != 'active':
            return None, "Session is not active"
        
        # Generate popup ID
        popup_id = f"popup_{int(time.time())}_{secrets.token_hex(4)}"
        current_time = datetime.now()
        expiry_time = current_time + timedelta(minutes=duration_minutes)
        
        # Get all students in section
        all_students = self._get_section_students(session['section_id'])
        
        popup_data = {
            'popup_id': popup_id,
            'session_id': session_id,
            'message': message,
            'created_at': current_time.isoformat(),
            'expires_at': expiry_time.isoformat(),
            'status': 'active',
            'target_students': all_students,
            'responses': {},  # {student_roll: {responded_at: timestamp, status: 'present'}}
            'total_students': len(all_students)
        }
        
        # Add popup to session
        if 'popups' not in session:
            session['popups'] = []
        
        session['popups'].append(popup_data)
        session['current_popup'] = popup_data
        
        sessions[session_id] = session
        self._save_online_sessions(sessions)
        
        # Return success data
        return {
            'popup_id': popup_id,
            'message': message,
            'students_count': len(all_students),
            'expires_at': expiry_time.isoformat()
        }, None
        
    def send_jitsi_attendance_popup(self, session_id, question="Are you present?", options=None, expiry_minutes=2):
        """Send attendance popup to Jitsi meeting participants - Simplified Version"""
        sessions = self._load_online_sessions()
        
        if session_id not in sessions:
            return None, "Session not found"
            
        session = sessions[session_id]
        
        if session['status'] != 'active':
            return None, "Session is not active"
            
        if not session.get('jitsi_link'):
            return None, "No Jitsi link configured for this session"
        
        # Set default options if not provided - DEFAULT POLL
        if options is None:
            options = ["Yes, I'm present", "No"]
        
        # Set default expiry time - 30 SECONDS DEFAULT
        if expiry_minutes is None:
            expiry_minutes = 0.5  # 30 seconds default
        
        # Create popup data directly (simplified approach)
        current_time = datetime.now()
        expiry_time = current_time + timedelta(minutes=expiry_minutes)
        popup_id = f"jitsi_{session_id}_{int(time.time())}_{secrets.token_hex(4)}"
        
        # Extract room name from Jitsi URL
        try:
            room_name = session['jitsi_link'].split('/')[-1]
        except:
            room_name = "jitsi_room"
        
        popup_data = {
            'popup_id': popup_id,
            'session_id': session_id,
            'question': question,
            'options': options,
            'created_at': current_time.isoformat(),
            'expires_at': expiry_time.isoformat(),
            'status': 'active',
            'room_name': room_name,
            'expiry_minutes': expiry_minutes,
            'responses': {},
            'jitsi_link': session['jitsi_link']
        }
        
        print(f"✅ Simplified Jitsi popup created! Room: {room_name}, Duration: {expiry_minutes*60} seconds")
        
        # Add to session's jitsi popups
        if 'jitsi_popups' not in session:
            session['jitsi_popups'] = []
        
        session['jitsi_popups'].append(popup_data)
        session['current_jitsi_popup'] = popup_data
        
        sessions[session_id] = session
        self._save_online_sessions(sessions)
        
        # Get target students
        target_students = self._get_section_students(session['section_id'])
        
        return {
            'popup_id': popup_data['popup_id'],
            'jitsi_link': session['jitsi_link'],
            'room_name': room_name,
            'target_students_count': len(target_students),
            'question': question,
            'options': options,
            'expiry_minutes': expiry_minutes,
            'sent_at': popup_data['created_at'],
            'expires_at': popup_data['expires_at'],
            'jitsi_status': popup_data['status']
        }, None
    
    def handle_jitsi_attendance_response(self, session_id, student_roll, response_data):
        """Handle student response from Jitsi attendance popup"""
        sessions = self._load_online_sessions()
        
        if session_id not in sessions:
            return False, "Session not found"
            
        session = sessions[session_id]
        current_time = datetime.now()
        
        # Mark attendance for the student
        if student_roll not in session['attendees']:
            session['attendees'][student_roll] = {
                'method': 'jitsi',
                'marked_at': current_time.isoformat(),
                'details': response_data,
                'jitsi_popup_id': session.get('current_jitsi_popup', {}).get('popup_id')
            }
            
            # Update jitsi responses
            if 'current_jitsi_popup' in session:
                session['current_jitsi_popup']['responses'][student_roll] = {
                    'responded_at': current_time.isoformat(),
                    'status': 'present',
                    'response_method': response_data.get('method', 'popup')
                }
            
            # Update summary
            session['attendance_summary']['total_jitsi_responses'] += 1
            session['attendance_summary']['unique_attendees'] = len(session['attendees'])
            
            sessions[session_id] = session
            self._save_online_sessions(sessions)
            
            return True, "Attendance marked successfully via Jitsi"
        else:
            return False, "Attendance already marked for this student"
    
    def get_jitsi_popup_status(self, session_id):
        """Get status of current Jitsi popup for a session"""
        sessions = self._load_online_sessions()
        
        if session_id not in sessions:
            return None
            
        session = sessions[session_id]
        current_popup = session.get('current_jitsi_popup')
        
        if not current_popup:
            return None
            
        # Check if popup has expired
        expiry_time = datetime.fromisoformat(current_popup['expires_at'])
        if datetime.now() > expiry_time and current_popup['status'] == 'active':
            current_popup['status'] = 'expired'
            # Clear current popup to prevent repetition
            session['current_jitsi_popup'] = None
            sessions[session_id] = session
            self._save_online_sessions(sessions)
            return None  # Return None for expired popup to stop showing
            
        target_students = self._get_section_students(session['section_id'])
        total_students = len(target_students)
        responded = len(current_popup['responses'])
        
        return {
            'popup_id': current_popup['popup_id'],
            'question': current_popup['question'],
            'options': current_popup['options'],
            'sent_at': current_popup['created_at'],
            'expires_at': current_popup['expires_at'],
            'status': current_popup['status'],
            'total_students': total_students,
            'responded_count': responded,
            'response_rate': round((responded / total_students) * 100, 1) if total_students > 0 else 0,
            'responses': current_popup['responses'],
            'room_name': current_popup.get('room_name'),
            'expiry_minutes': current_popup.get('expiry_minutes', 2)
        }
    
    def get_popup_status(self, popup_id):
        """Get real-time status of popup attendance"""
        sessions = self._load_online_sessions()
        
        # Find popup across all sessions
        target_popup = None
        target_session = None
        
        for session_id, session in sessions.items():
            if 'popups' in session:
                for popup in session['popups']:
                    if popup['popup_id'] == popup_id:
                        target_popup = popup
                        target_session = session
                        break
            
            # Also check current_popup
            if session.get('current_popup') and session['current_popup']['popup_id'] == popup_id:
                target_popup = session['current_popup']
                target_session = session
                break
        
        if not target_popup:
            return None
        
        # Check if popup has expired
        expiry_time = datetime.fromisoformat(target_popup['expires_at'])
        if datetime.now() > expiry_time and target_popup['status'] == 'active':
            target_popup['status'] = 'expired'
            self._save_online_sessions(sessions)
        
        # Calculate statistics
        total_students = target_popup['total_students']
        responded = len(target_popup['responses'])
        pending = total_students - responded
        response_rate = round((responded / total_students) * 100, 1) if total_students > 0 else 0
        
        # Get recent responses (last 10)
        recent_responses = []
        for student, response_data in sorted(target_popup['responses'].items(), 
                                           key=lambda x: x[1]['responded_at'], reverse=True)[:10]:
            recent_responses.append({
                'student': student,
                'responded_at': response_data['responded_at']
            })
        
        return {
            'popup_id': popup_id,
            'status': target_popup['status'],
            'message': target_popup['message'],
            'created_at': target_popup['created_at'],
            'expires_at': target_popup['expires_at'],
            'total_students': total_students,
            'responded': responded,
            'pending': pending,
            'response_rate': response_rate,
            'recent_responses': recent_responses
        }
    
    def respond_to_popup(self, popup_id, student_roll):
        """Student responds to popup attendance"""
        sessions = self._load_online_sessions()
        
        # Find popup and session
        target_popup = None
        target_session = None
        session_id = None
        
        for sid, session in sessions.items():
            if session.get('current_popup') and session['current_popup']['popup_id'] == popup_id:
                target_popup = session['current_popup']
                target_session = session
                session_id = sid
                break
            
            if 'popups' in session:
                for popup in session['popups']:
                    if popup['popup_id'] == popup_id and popup['status'] == 'active':
                        target_popup = popup
                        target_session = session
                        session_id = sid
                        break
        
        if not target_popup:
            return False, "Popup attendance not found or expired"
        
        # Check expiry
        expiry_time = datetime.fromisoformat(target_popup['expires_at'])
        if datetime.now() > expiry_time:
            target_popup['status'] = 'expired'
            self._save_online_sessions(sessions)
            return False, "Popup attendance has expired"
        
        # Verify student belongs to section
        if not self._verify_student_section(student_roll, target_session['section_id']):
            return False, "You are not enrolled in this section"
        
        # Check if already responded
        if student_roll in target_popup['responses']:
            return False, "You have already responded to this attendance check"
        
        # Record response
        current_time = datetime.now()
        target_popup['responses'][student_roll] = {
            'responded_at': current_time.isoformat(),
            'status': 'present'
        }
        
        # Mark attendance in session if not already marked
        if student_roll not in target_session['attendees']:
            attendance_record = {
                'method': 'popup',
                'marked_at': current_time.isoformat(),
                'popup_id': popup_id,
                'details': {
                    'message': target_popup['message'],
                    'response_time': current_time.isoformat()
                }
            }
            target_session['attendees'][student_roll] = attendance_record
        
        # Update summary
        target_session['attendance_summary']['unique_attendees'] = len(target_session['attendees'])
        
        sessions[session_id] = target_session
        self._save_online_sessions(sessions)
        
        return True, "Attendance marked successfully!"
    
    def get_active_popups_for_student(self, student_roll):
        """Get active popups that a student needs to respond to"""
        sessions = self._load_online_sessions()
        active_popups = []
        current_time = datetime.now()
        
        for session in sessions.values():
            if session['status'] != 'active':
                continue
            
            # Check if student belongs to this section
            if not self._verify_student_section(student_roll, session['section_id']):
                continue
            
            # Check current popup
            if session.get('current_popup'):
                popup = session['current_popup']
                expiry_time = datetime.fromisoformat(popup['expires_at'])
                
                if (popup['status'] == 'active' and 
                    current_time <= expiry_time and 
                    student_roll not in popup['responses']):
                    
                    active_popups.append({
                        'popup_id': popup['popup_id'],
                        'session_id': popup['session_id'],
                        'subject': session['subject'],
                        'message': popup['message'],
                        'expires_at': popup['expires_at'],
                        'time_left_minutes': int((expiry_time - current_time).total_seconds() / 60)
                    })
        
        return active_popups
    
    # ========== TOKEN SYSTEM ==========
    
    def generate_attendance_token(self, session_id, validity_minutes=8):
        """Generate a time-limited attendance token"""
        sessions = self._load_online_sessions()
        
        if session_id not in sessions:
            return None, "Session not found"
            
        session = sessions[session_id]
        
        if session['status'] != 'active':
            return None, "Session is not active"
            
        # Deactivate previous token
        if session['current_token']:
            session['current_token']['status'] = 'expired'
            session['token_history'].append(session['current_token'])
        
        # Generate new token
        token_code = self._generate_token_code()
        current_time = datetime.now()
        expiry_time = current_time + timedelta(minutes=validity_minutes)
        
        token_data = {
            'token_code': token_code,
            'created_at': current_time.isoformat(),
            'expires_at': expiry_time.isoformat(),
            'status': 'active',
            'used_by': [],
            'session_id': session_id,
            'subject': session['subject'],
            'section': session['section_id']
        }
        
        session['current_token'] = token_data
        session['attendance_summary']['total_tokens'] += 1
        
        sessions[session_id] = session
        self._save_online_sessions(sessions)
        
        return {
            'token_code': token_code,
            'expires_at': expiry_time.isoformat(),
            'validity_minutes': validity_minutes,
            'session_info': {
                'subject': session['subject'],
                'section': session['section_id'],
                'faculty': session['faculty_username']
            }
        }, None
    
    def mark_attendance_with_token(self, token_code, student_roll):
        """Mark attendance using token code"""
        sessions = self._load_online_sessions()
        
        # Find session with this token
        target_session = None
        session_id = None
        
        for sid, session in sessions.items():
            if (session['current_token'] and 
                session['current_token']['token_code'] == token_code and
                session['current_token']['status'] == 'active'):
                target_session = session
                session_id = sid
                break
        
        if not target_session:
            return False, "Invalid or expired token"
        
        # Check token expiry
        expiry_time = datetime.fromisoformat(target_session['current_token']['expires_at'])
        if datetime.now() > expiry_time:
            target_session['current_token']['status'] = 'expired'
            self._save_online_sessions(sessions)
            return False, "Token has expired"
        
        # Verify student belongs to section
        if not self._verify_student_section(student_roll, target_session['section_id']):
            return False, "You are not enrolled in this section"
        
        # Check if already marked present in this session
        if student_roll in target_session['attendees']:
            return False, f"Already marked present via {target_session['attendees'][student_roll]['method']}"
        
        # Mark attendance
        attendance_record = {
            'method': 'token',
            'marked_at': datetime.now().isoformat(),
            'token_code': token_code,
            'details': {
                'token_created_at': target_session['current_token']['created_at']
            }
        }
        
        target_session['attendees'][student_roll] = attendance_record
        target_session['current_token']['used_by'].append({
            'student': student_roll,
            'marked_at': datetime.now().isoformat()
        })
        
        # Update summary
        target_session['attendance_summary']['unique_attendees'] = len(target_session['attendees'])
        
        sessions[session_id] = target_session
        self._save_online_sessions(sessions)
        
        return True, f"Attendance marked for {target_session['subject']}"
    
    # ========== POLLING SYSTEM ==========
    
    def create_poll(self, session_id, question, options, 
                   correct_answer=None, duration_minutes=5):
        """Create an interactive poll for attendance"""
        sessions = self._load_online_sessions()
        
        if session_id not in sessions:
            return None, "Session not found"
            
        session = sessions[session_id]
        
        if session['status'] != 'active':
            return None, "Session is not active"
        
        # Close previous poll
        if session['current_poll']:
            session['current_poll']['status'] = 'closed'
            session['polls'].append(session['current_poll'])
        
        # Create new poll
        poll_id = f"poll_{int(time.time())}_{secrets.token_hex(4)}"
        current_time = datetime.now()
        expiry_time = current_time + timedelta(minutes=duration_minutes)
        
        poll_data = {
            'poll_id': poll_id,
            'question': question,
            'options': options,
            'correct_answer': correct_answer,
            'created_at': current_time.isoformat(),
            'expires_at': expiry_time.isoformat(),
            'status': 'active',
            'responses': {},  # {student_roll: {'answer': 'A', 'answered_at': timestamp, 'is_correct': bool}}
            'session_id': session_id
        }
        
        session['current_poll'] = poll_data
        session['attendance_summary']['total_polls'] += 1
        
        sessions[session_id] = session
        self._save_online_sessions(sessions)
        
        return {
            'poll_id': poll_id,
            'question': question,
            'options': options,
            'expires_at': expiry_time.isoformat(),
            'duration_minutes': duration_minutes,
            'session_info': {
                'subject': session['subject'],
                'section': session['section_id'],
                'faculty': session['faculty_username']
            }
        }, None
    
    def submit_poll_response(self, poll_id, student_roll, answer):
        """Submit response to a poll"""
        sessions = self._load_online_sessions()
        
        # Find session with this poll
        target_session = None
        session_id = None
        
        for sid, session in sessions.items():
            if (session['current_poll'] and 
                session['current_poll']['poll_id'] == poll_id and
                session['current_poll']['status'] == 'active'):
                target_session = session
                session_id = sid
                break
        
        if not target_session:
            return False, "Poll not found or expired"
        
        poll = target_session['current_poll']
        
        # Check poll expiry
        expiry_time = datetime.fromisoformat(poll['expires_at'])
        if datetime.now() > expiry_time:
            poll['status'] = 'expired'
            self._save_online_sessions(sessions)
            return False, "Poll has expired"
        
        # Verify student belongs to section
        if not self._verify_student_section(student_roll, target_session['section_id']):
            return False, "You are not enrolled in this section"
        
        # Check if valid answer
        if answer not in poll['options']:
            return False, "Invalid answer option"
        
        # Check if already answered
        if student_roll in poll['responses']:
            return False, "You have already answered this poll"
        
        # Record response
        is_correct = (poll['correct_answer'] is None or answer == poll['correct_answer'])
        
        poll['responses'][student_roll] = {
            'answer': answer,
            'answered_at': datetime.now().isoformat(),
            'is_correct': is_correct
        }
        
        # Mark attendance if not already marked
        if student_roll not in target_session['attendees']:
            attendance_record = {
                'method': 'poll',
                'marked_at': datetime.now().isoformat(),
                'poll_id': poll_id,
                'details': {
                    'question': poll['question'],
                    'answer': answer,
                    'is_correct': is_correct
                }
            }
            target_session['attendees'][student_roll] = attendance_record
        
        # Update summary
        target_session['attendance_summary']['unique_attendees'] = len(target_session['attendees'])
        
        sessions[session_id] = target_session
        self._save_online_sessions(sessions)
        
        result_msg = "Response submitted"
        if poll['correct_answer']:
            result_msg += f" - {'Correct!' if is_correct else 'Incorrect'}"
        
        return True, result_msg
    
    def get_poll_results(self, session_id, poll_id=None):
        """Get results of a poll"""
        sessions = self._load_online_sessions()
        
        if session_id not in sessions:
            return None
            
        session = sessions[session_id]
        
        if poll_id:
            # Get specific poll results
            poll = None
            if session['current_poll'] and session['current_poll']['poll_id'] == poll_id:
                poll = session['current_poll']
            else:
                for p in session['polls']:
                    if p['poll_id'] == poll_id:
                        poll = p
                        break
            
            if not poll:
                return None
                
            return self._format_poll_results(poll)
        else:
            # Get current poll results
            if session['current_poll']:
                return self._format_poll_results(session['current_poll'])
            return None
    
    # ========== UTILITY METHODS ==========
    
    def get_session_attendance_summary(self, session_id):
        """Get comprehensive attendance summary for a session"""
        sessions = self._load_online_sessions()
        
        if session_id not in sessions:
            return None
            
        session = sessions[session_id]
        
        # Get all students in section
        all_students = self._get_section_students(session['section_id'])
        present_students = list(session['attendees'].keys())
        absent_students = [s for s in all_students if s not in present_students]
        
        # Method breakdown
        token_attendance = sum(1 for record in session['attendees'].values() if record['method'] == 'token')
        poll_attendance = sum(1 for record in session['attendees'].values() if record['method'] == 'poll')
        
        return {
            'session_info': {
                'session_id': session_id,
                'subject': session['subject'],
                'section': session['section_id'],
                'faculty': session['faculty_username'],
                'start_time': session['start_time'],
                'status': session['status']
            },
            'attendance_summary': {
                'total_students': len(all_students),
                'present': len(present_students),
                'absent': len(absent_students),
                'attendance_rate': round((len(present_students) / len(all_students)) * 100, 1) if all_students else 0
            },
            'method_breakdown': {
                'token_attendance': token_attendance,
                'poll_attendance': poll_attendance,
                'total_tokens_generated': session['attendance_summary']['total_tokens'],
                'total_polls_created': session['attendance_summary']['total_polls']
            },
            'present_students': present_students,
            'absent_students': absent_students,
            'detailed_attendance': session['attendees']
        }
    
    def get_session_attendance_details(self, session_id):
        """Get detailed attendance records for a session - formatted for frontend display"""
        sessions = self._load_online_sessions()
        
        if session_id not in sessions:
            return []
            
        session = sessions[session_id]
        attendance_records = []
        
        # Convert session attendees to frontend-friendly format
        for student_roll, attendance_data in session['attendees'].items():
            attendance_records.append({
                'student_roll': student_roll,
                'status': 'present',  # All entries in attendees are present
                'method': attendance_data.get('method', 'unknown'),
                'timestamp': attendance_data.get('marked_at'),
                'details': attendance_data.get('details', {})
            })
        
        return attendance_records
    
    def _format_poll_results(self, poll):
        """Format poll results for display"""
        total_responses = len(poll['responses'])
        option_counts = {option: 0 for option in poll['options']}
        correct_responses = 0
        
        for response in poll['responses'].values():
            option_counts[response['answer']] += 1
            if response.get('is_correct', False):
                correct_responses += 1
        
        return {
            'poll_info': {
                'poll_id': poll['poll_id'],
                'question': poll['question'],
                'options': poll['options'],
                'correct_answer': poll.get('correct_answer'),
                'created_at': poll['created_at'],
                'expires_at': poll['expires_at'],
                'status': poll['status']
            },
            'results': {
                'total_responses': total_responses,
                'correct_responses': correct_responses,
                'accuracy_rate': round((correct_responses / total_responses) * 100, 1) if total_responses > 0 else 0,
                'option_breakdown': option_counts,
                'responses': poll['responses']
            }
        }
    
    def _save_to_main_attendance(self, session):
        """Save online session attendance to main attendance system"""
        try:
            from app import load_attendance_data, save_attendance_data
            
            main_attendance = load_attendance_data()
            section_id = session['section_id']
            date_str = datetime.fromisoformat(session['start_time']).strftime('%Y-%m-%d')
            
            if section_id not in main_attendance:
                main_attendance[section_id] = {}
            
            if date_str not in main_attendance[section_id]:
                main_attendance[section_id][date_str] = {}
            
            # Get all students in section
            all_students = self._get_section_students(section_id)
            
            # Mark online attendance
            for student in all_students:
                online_key = f"online_{session['subject']}_{student}"
                if student in session['attendees']:
                    main_attendance[section_id][date_str][online_key] = 1
                else:
                    main_attendance[section_id][date_str][online_key] = 0
            
            save_attendance_data(main_attendance)
            
        except Exception as e:
            print(f"Error saving to main attendance: {e}")
    
    def _generate_session_id(self):
        """Generate unique session ID"""
        return f"online_{int(time.time())}_{secrets.token_hex(4)}"
    
    def _generate_token_code(self):
        """Generate 6-digit attendance token"""
        return f"{secrets.randbelow(900000) + 100000:06d}"
    
    def _verify_student_section(self, student_roll, section_id):
        """Verify if student belongs to the section"""
        try:
            section_students = self._get_section_students(section_id)
            return student_roll in section_students
        except:
            return False
    
    def _get_section_students(self, section_id):
        """Get all students in a section"""
        try:
            from app import get_section_students
            return get_section_students(section_id)
        except:
            return []
    
    def _load_online_sessions(self):
        """Load online sessions from JSON file"""
        try:
            with open(self.online_sessions_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _save_online_sessions(self, sessions):
        """Save online sessions to JSON file"""
        with open(self.online_sessions_file, 'w') as f:
            json.dump(sessions, f, indent=2, default=str)
