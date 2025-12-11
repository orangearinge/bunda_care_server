#!/bin/bash
# Test script to verify login fix

echo "Testing login endpoint with preference status check..."

# Test 1: Login with non-existent user (should fail)
echo "Test 1: Login with invalid credentials"
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "nonexistent@test.com", "password": "wrongpassword"}' \
  -w "\nStatus: %{http_code}\n" \
  -s

echo -e "\n---"

# Test 2: Check preferences status endpoint (should fail without auth)
echo "Test 2: Check preferences status without auth (should fail)"
curl -X GET http://localhost:5000/api/auth/preferences-status \
  -w "\nStatus: %{http_code}\n" \
  -s

echo -e "\n---"

echo "Note: For full testing, the server needs to be running with a real database"
echo "The login endpoints now include 'has_preferences' and 'needs_preferences' fields"