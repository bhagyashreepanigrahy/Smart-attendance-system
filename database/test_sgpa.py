#!/usr/bin/env python3
"""
Test script for SGPA functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.mysql_adapter import mysql_db

def test_sgpa_functionality():
    """Test SGPA and CGPA features"""
    print("🧪 Testing SGPA Functionality...")
    
    try:
        # Test 1: Get top performers
        print("\n📊 Top 5 Performers:")
        top_performers = mysql_db.get_top_performers(limit=5)
        for i, student in enumerate(top_performers, 1):
            print(f"{i}. {student['roll_number']}: {student['name']} - CGPA: {student['cgpa']}")
        
        # Test 2: Get a specific student's academic summary
        if top_performers:
            test_roll = top_performers[0]['roll_number']
            print(f"\n🎓 Academic Summary for {test_roll}:")
            summary = mysql_db.get_student_academic_summary(test_roll)
            if summary:
                print(f"   Name: {summary['name']}")
                print(f"   CGPA: {summary['cgpa']}")
                print(f"   Semester SGPAs:")
                for sem in range(1, 9):
                    sgpa_key = f'sgpa_sem{sem}'
                    if summary.get(sgpa_key):
                        print(f"     Sem {sem}: {summary[sgpa_key]}")
                print(f"   Attendance: {summary.get('attendance_percentage', 0)}%")
        
        # Test 3: Section analytics
        print(f"\n📈 Section Analytics for CSE_DS:")
        # First get a sample section from students
        students_query = "SELECT DISTINCT section_id FROM students LIMIT 3"
        sections = mysql_db.execute_query(students_query)
        
        for section in sections[:2]:  # Test first 2 sections
            section_id = section['section_id']
            print(f"\n--- {section_id} ---")
            
            # Get section statistics
            query = """
                SELECT COUNT(*) as total_students,
                       AVG(cgpa) as avg_cgpa,
                       MAX(cgpa) as max_cgpa,
                       MIN(cgpa) as min_cgpa
                FROM students 
                WHERE section_id = %s AND cgpa IS NOT NULL
            """
            stats = mysql_db.execute_query(query, (section_id,))
            if stats and stats[0]['total_students'] > 0:
                stat = stats[0]
                print(f"   Total Students: {stat['total_students']}")
                print(f"   Average CGPA: {float(stat['avg_cgpa']):.2f}")
                print(f"   Highest CGPA: {stat['max_cgpa']}")
                print(f"   Lowest CGPA: {stat['min_cgpa']}")
            else:
                print("   No CGPA data available for this section")
        
        print("\n✅ SGPA functionality test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_sgpa_functionality()