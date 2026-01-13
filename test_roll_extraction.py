#!/usr/bin/env python3
"""
Test script to verify roll number extraction from participant names
"""

import re

def extract_roll_from_name(participant_name):
    """Extract student roll number from participant name - Enhanced version"""
    
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
            return roll_number
    
    return None

# Test cases
test_cases = [
    # Format: name(rollno)
    "John Doe (23CSEDS001)",
    "jane smith(24CSEAIML002)",
    "Alice Johnson (23BCA003)",
    "Bob Wilson (24MCA004)",
    
    # Format: name rollno
    "John Doe 23CSEDS001",
    "Jane Smith 24CSEAIML002",
    
    # Format: rollno name
    "23CSEDS001 John Doe",
    "24CSEAIML002 Jane Smith",
    
    # Just roll number
    "23CSEDS001",
    "24CSEAIML002",
    
    # Edge cases
    "UDDHAB CHAKRABORTY (23CSEDS101)",
    "Student Name(22CSE070)",
    "Name with spaces (23CSEAIML123)",
    
    # Should not match
    "Just a Name",
    "123456789",
    "Random Text"
]

def test_extraction():
    print("🧪 Testing Roll Number Extraction")
    print("=" * 50)
    
    passed = 0
    failed = 0
    
    for test_name in test_cases:
        result = extract_roll_from_name(test_name)
        
        if result:
            print(f"✅ '{test_name}' → '{result}'")
            passed += 1
        else:
            print(f"❌ '{test_name}' → No match")
            failed += 1
    
    print("=" * 50)
    print(f"📊 Results: {passed} passed, {failed} failed")
    print(f"Success rate: {(passed / len(test_cases) * 100):.1f}%")

if __name__ == "__main__":
    test_extraction()