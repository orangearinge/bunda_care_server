#!/usr/bin/env python3
"""
Simple test script to verify login redirect fix
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.controllers.auth_controller import check_user_preferences_status

def test_check_user_preferences_status():
    """Test the preference status checker function"""
    print("Testing check_user_preferences_status function...")
    
    # Test with non-existent user (should return False)
    has_prefs, pref = check_user_preferences_status(99999)
    print(f"Non-existent user: has_preferences={has_prefs}, preference={pref}")
    assert has_prefs == False
    assert pref == None
    
    print("✓ check_user_preferences_status function works correctly")

if __name__ == "__main__":
    test_check_user_preferences_status()
    print("All tests passed!")