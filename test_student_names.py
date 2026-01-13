#!/usr/bin/env python3
"""
Test script to verify student names are loaded correctly from details.json
"""

import requests
import json
import os

# Configuration
BASE_URL = "http://localhost:5000"
TEST_SECTION = "CSE_DS"

def test_student_data():
    """Test if student names are properly loaded from details.json"""
    print("🧪 Testing Student Name Loading from details.json")
    print("=" * 60)
    
    # First, let's check what's in the details.json file
    details_file_path = os.path.join("database", "details.json")
    if os.path.exists(details_file_path):
        print(f"✅ Found details.json at: {details_file_path}")
        
        with open(details_file_path, 'r') as f:
            details_data = json.load(f)
        
        print(f"📊 Total students in details.json: {len(details_data)}")
        
        # Show first few students
        print("\n📋 Sample students from details.json:")
        for i, student in enumerate(details_data[:5]):
            print(f"  {i+1}. {student.get('rollNo', 'N/A')} - {student.get('name', 'N/A')}")
        
        # Check if we have CSE_DS students
        cse_ds_students = [s for s in details_data if s.get('rollNo', '').startswith('22CSE') or s.get('rollNo', '').startswith('23CSEDS')]
        print(f"\n🎯 CSE-DS related students found: {len(cse_ds_students)}")
        
        if cse_ds_students:
            print("📝 Sample CSE-DS students:")
            for student in cse_ds_students[:3]:
                print(f"  • {student.get('rollNo')} - {student.get('name', 'No name')}")
    else:
        print(f"❌ details.json not found at: {details_file_path}")
        return
    
    # Now test the API
    print(f"\n🔗 Testing API: {BASE_URL}/api/section_students?section={TEST_SECTION}")
    
    try:
        response = requests.get(f"{BASE_URL}/api/section_students?section={TEST_SECTION}")
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('success'):
                students = result.get('students', [])
                print(f"✅ API returned {len(students)} students for section {TEST_SECTION}")
                
                # Check if students have names
                students_with_names = [s for s in students if s.get('name') and s.get('name') != f"Student {s.get('rollNo')}"]
                students_without_names = [s for s in students if not s.get('name') or s.get('name') == f"Student {s.get('rollNo')}"]
                
                print(f"✅ Students WITH proper names: {len(students_with_names)}")
                print(f"❌ Students WITHOUT proper names: {len(students_without_names)}")
                
                if students_with_names:
                    print(f"\n🎉 SUCCESS - Sample students with names:")
                    for student in students_with_names[:5]:
                        print(f"  • {student.get('rollNo')} - {student.get('name')}")
                        # Check if image URL would work
                        image_url = f"https://gietuerp.in/StudentDocuments/{student.get('rollNo')}/{student.get('rollNo')}.JPG"
                        print(f"    🖼️  Image: {image_url}")
                
                if students_without_names:
                    print(f"\n⚠️  Students without proper names (showing first 3):")
                    for student in students_without_names[:3]:
                        print(f"  • {student.get('rollNo')} - {student.get('name', 'No name')}")
                
            else:
                print(f"❌ API returned error: {result.get('message')}")
        else:
            print(f"❌ HTTP Error {response.status_code}: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Make sure Flask app is running at http://localhost:5000")
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
    
    print("\n" + "=" * 60)
    print("🏁 Student Name Test Complete!")

def test_specific_students():
    """Test specific students that should exist"""
    print("\n🎯 Testing Specific Known Students")
    print("-" * 40)
    
    # Known students from details.json sample
    known_students = [
        "22CSE998",
        "22CSE1000", 
        "22CSEAIML128"
    ]
    
    details_file_path = os.path.join("database", "details.json")
    if os.path.exists(details_file_path):
        with open(details_file_path, 'r') as f:
            details_data = json.load(f)
        
        for roll_no in known_students:
            student_info = next((s for s in details_data if s.get('rollNo') == roll_no), None)
            if student_info:
                print(f"✅ {roll_no}: {student_info.get('name', 'No name')}")
                print(f"   📱 Mobile: {student_info.get('mobile', 'No mobile')}")
                if 'sgpas' in student_info:
                    print(f"   📊 SGPAs: {len(student_info['sgpas'])} semesters")
            else:
                print(f"❌ {roll_no}: Not found in details.json")

if __name__ == "__main__":
    test_student_data()
    test_specific_students()