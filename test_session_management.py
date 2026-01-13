#!/usr/bin/env python3
"""
Session Management Test Script
Tests the complete online attendance session management functionality
"""

import requests
import json
from datetime import datetime
import time

# Configuration
BASE_URL = "http://localhost:5000"
TEST_SESSION_DATA = {
    "section_id": "CSE_DS",
    "subject": "Data Structures",
    "class_type": "lecture", 
    "duration_minutes": 90,
    "jitsi_link": "https://meet.jit.si/TestSessionManagement"
}

def test_session_management():
    """Test complete session management workflow"""
    print("🧪 Testing Session Management System")
    print("=" * 50)
    
    session_id = None
    
    try:
        # 1. Create Session
        print("\n1️⃣ Creating Online Session...")
        create_response = requests.post(
            f"{BASE_URL}/api/online/create_session",
            json=TEST_SESSION_DATA,
            headers={"Content-Type": "application/json"}
        )
        
        if create_response.status_code == 200:
            create_result = create_response.json()
            if create_result.get('success'):
                session_id = create_result['session_id']
                print(f"✅ Session created successfully: {session_id}")
                print(f"   📋 Subject: {TEST_SESSION_DATA['subject']}")
                print(f"   🎓 Section: {TEST_SESSION_DATA['section_id']}")
                print(f"   🔗 Jitsi Link: {TEST_SESSION_DATA['jitsi_link']}")
            else:
                print(f"❌ Failed to create session: {create_result.get('message')}")
                return
        else:
            print(f"❌ HTTP Error {create_response.status_code}: {create_response.text}")
            return
            
        # 2. Check Active Sessions
        print("\n2️⃣ Checking Active Sessions...")
        active_response = requests.get(f"{BASE_URL}/api/online/active_sessions")
        
        if active_response.status_code == 200:
            active_result = active_response.json()
            if active_result.get('success'):
                sessions = active_result.get('sessions', [])
                print(f"✅ Found {len(sessions)} active session(s)")
                for session in sessions:
                    print(f"   📝 Session: {session.get('session_id', 'N/A')}")
                    print(f"   📚 Subject: {session.get('subject', 'N/A')}")
                    print(f"   🎯 Present: {session.get('attendance_summary', {}).get('unique_attendees', 0)}")
            else:
                print("❌ Failed to get active sessions")
        else:
            print(f"❌ HTTP Error {active_response.status_code}")
            
        # 3. Send Quick Poll (Simulate)
        print("\n3️⃣ Sending Quick Poll...")
        poll_response = requests.post(
            f"{BASE_URL}/api/online/send_jitsi_popup",
            json={
                "session_id": session_id,
                "question": "Are you present in class?",
                "options": ["Present", "Not Present"],
                "expiry_minutes": 0.5
            },
            headers={"Content-Type": "application/json"}
        )
        
        if poll_response.status_code == 200:
            poll_result = poll_response.json()
            if poll_result.get('success'):
                print(f"✅ Quick poll sent successfully")
                print(f"   📊 Target students: {poll_result.get('popup_data', {}).get('target_students_count', 0)}")
            else:
                print(f"❌ Failed to send poll: {poll_result.get('message')}")
        else:
            print(f"❌ HTTP Error {poll_response.status_code}")
            
        # 4. Simulate Student Response
        print("\n4️⃣ Simulating Student Response...")
        response_data = requests.post(
            f"{BASE_URL}/api/online/jitsi_attendance",
            json={
                "session_id": session_id,
                "student_roll": "23CSEDS001", 
                "method": "jitsi_popup_test",
                "participant_name": "Test Student (23CSEDS001)"
            },
            headers={"Content-Type": "application/json"}
        )
        
        if response_data.status_code == 200:
            response_result = response_data.json()
            if response_result.get('success'):
                print("✅ Student attendance marked successfully")
                print("   👤 Student: Test Student (23CSEDS001)")
            else:
                print(f"❌ Failed to mark attendance: {response_result.get('message')}")
        else:
            print(f"❌ HTTP Error {response_data.status_code}")
            
        # 5. Get Session Attendance Details
        print("\n5️⃣ Getting Session Attendance Details...")
        attendance_response = requests.get(f"{BASE_URL}/api/online/session_attendance/{session_id}")
        
        if attendance_response.status_code == 200:
            attendance_result = attendance_response.json()
            if attendance_result.get('success'):
                attendance_records = attendance_result.get('attendance', [])
                print(f"✅ Retrieved {len(attendance_records)} attendance record(s)")
                for record in attendance_records:
                    print(f"   👤 {record.get('student_roll')}: {record.get('status')} via {record.get('method')}")
            else:
                print(f"❌ Failed to get attendance: {attendance_result.get('message')}")
        else:
            print(f"❌ HTTP Error {attendance_response.status_code}")
            
        # 6. Save Session Attendance  
        print("\n6️⃣ Saving Session Attendance...")
        save_response = requests.post(
            f"{BASE_URL}/api/online/save_attendance",
            json={"session_id": session_id},
            headers={"Content-Type": "application/json"}
        )
        
        if save_response.status_code == 200:
            save_result = save_response.json()
            if save_result.get('success'):
                print("✅ Session attendance saved successfully")
                print(f"   💾 Message: {save_result.get('message', 'Saved')}")
            else:
                print(f"❌ Failed to save attendance: {save_result.get('message')}")
        else:
            print(f"❌ HTTP Error {save_response.status_code}")
            
        # 7. End Session
        print("\n7️⃣ Ending Session...")
        end_response = requests.post(
            f"{BASE_URL}/api/online/end_session",
            json={"session_id": session_id},
            headers={"Content-Type": "application/json"}
        )
        
        if end_response.status_code == 200:
            end_result = end_response.json()
            if end_result.get('success'):
                print("✅ Session ended successfully")
                print(f"   🏁 Message: {end_result.get('message', 'Session closed')}")
            else:
                print(f"❌ Failed to end session: {end_result.get('message')}")
        else:
            print(f"❌ HTTP Error {end_response.status_code}")
            
        # 8. Final Status Check
        print("\n8️⃣ Final Status Check...")
        final_response = requests.get(f"{BASE_URL}/api/online/active_sessions")
        
        if final_response.status_code == 200:
            final_result = final_response.json()
            if final_result.get('success'):
                sessions = final_result.get('sessions', [])
                print(f"✅ Active sessions remaining: {len(sessions)}")
                if len(sessions) == 0:
                    print("   🎉 All sessions properly closed!")
            else:
                print("❌ Failed final status check")
        else:
            print(f"❌ HTTP Error {final_response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Make sure the Flask app is running at http://localhost:5000")
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        
    print("\n" + "=" * 50)
    print("🏁 Session Management Test Complete!")

def print_session_management_features():
    """Print all available session management features"""
    print("\n🎯 Session Management Features Available:")
    print("-" * 40)
    
    features = [
        "✅ Create Online Sessions with Jitsi Integration",
        "✅ View Active Sessions with Real-time Status", 
        "✅ Send Quick Attendance Polls (30-second default)",
        "✅ Monitor Live Statistics (Present/Absent/Pending)",
        "✅ Export Attendance Data to Excel",
        "✅ Copy Jitsi Meeting Links",
        "✅ View Session Details & Duration",
        "✅ Track Recent Activity Feed",
        "✅ Refresh Session Data in Real-time",
        "✅ End Sessions with Attendance Save",
        "✅ Professional Modal Interface",
        "✅ Auto-update Student Lists"
    ]
    
    for feature in features:
        print(f"  {feature}")
    
    print("\n🎮 How to Use:")
    print("  1. Start your Flask app: python app.py")
    print("  2. Go to: http://localhost:5000/online_attendance")
    print("  3. Create a session with Jitsi link")
    print("  4. Click 'Manage Session' for full control panel")
    print("  5. Use Quick Poll to send attendance popups")
    print("  6. Export data or end session when done")

if __name__ == "__main__":
    print_session_management_features()
    print("\nStarting test in 3 seconds...")
    time.sleep(3)
    test_session_management()