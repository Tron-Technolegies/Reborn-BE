import os
import sys
import django
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "perfectfitsoftware.settings")
django.setup()

from django.test import Client
from django.contrib.auth.models import User

client = Client(enforce_csrf_checks=False)

print("--- Running Authentication Tests ---")

# Clean up test users if they exist
User.objects.filter(username__in=["test_superuser", "test_regular_user"]).delete()

# Create test users
superuser = User.objects.create_superuser(
    username="test_superuser",
    email="admin@test.com",
    password="SuperPassword123!"
)

regular_user = User.objects.create_user(
    username="test_regular_user",
    email="user@test.com",
    password="UserPassword123!"
)

# 1. Test unauthenticated /api/auth/me/
print("\n1. Testing GET /api/auth/me/ when unauthenticated...")
res = client.get('/api/auth/me/')
assert res.status_code == 401, f"Expected 401, got {res.status_code}"
assert res.json().get('authenticated') is False
print("Passed: returns 401 for unauthenticated session.")

# 2. Test login with wrong password
print("\n2. Testing POST /api/auth/login/ with wrong password...")
res = client.post(
    '/api/auth/login/',
    data=json.dumps({"username": "test_superuser", "password": "WrongPassword"}),
    content_type='application/json'
)
assert res.status_code == 401, f"Expected 401, got {res.status_code}"
print("Passed: returns 401 for incorrect password.")

# 3. Test login with non-existent user
print("\n3. Testing POST /api/auth/login/ with non-existent user...")
res = client.post(
    '/api/auth/login/',
    data=json.dumps({"username": "non_existent_user", "password": "Password123"}),
    content_type='application/json'
)
assert res.status_code == 401, f"Expected 401, got {res.status_code}"
print("Passed: returns 401 for non-existent user.")

# 4. Test login with non-superuser
print("\n4. Testing POST /api/auth/login/ with non-superuser...")
res = client.post(
    '/api/auth/login/',
    data=json.dumps({"username": "test_regular_user", "password": "UserPassword123!"}),
    content_type='application/json'
)
assert res.status_code == 403, f"Expected 403, got {res.status_code}"
assert "Superuser access required." in res.json().get('error', '')
print("Passed: returns 403 for non-superuser.")

# 5. Test login with superuser
print("\n5. Testing POST /api/auth/login/ with valid superuser...")
res = client.post(
    '/api/auth/login/',
    data=json.dumps({"username": "test_superuser", "password": "SuperPassword123!"}),
    content_type='application/json'
)
assert res.status_code == 200, f"Expected 200, got {res.status_code}"
data = res.json()
assert data.get('success') is True
assert data.get('user', {}).get('username') == "test_superuser"
assert data.get('user', {}).get('is_superuser') is True
assert 'password' not in data.get('user', {})
print("Passed: superuser login succeeds and session created.")

# 6. Test GET /api/auth/me/ with active superuser session
print("\n6. Testing GET /api/auth/me/ with active superuser session...")
res = client.get('/api/auth/me/')
assert res.status_code == 200, f"Expected 200, got {res.status_code}"
data = res.json()
assert data.get('authenticated') is True
assert data.get('user', {}).get('username') == "test_superuser"
assert data.get('user', {}).get('is_superuser') is True
print("Passed: authenticated superuser session verified.")

# 7. Test POST /api/auth/logout/
print("\n7. Testing POST /api/auth/logout/...")
res = client.post('/api/auth/logout/')
assert res.status_code == 200, f"Expected 200, got {res.status_code}"
assert res.json().get('success') is True
print("Passed: logout endpoint returns success.")

# 8. Test GET /api/auth/me/ after logout
print("\n8. Testing GET /api/auth/me/ after logout...")
res = client.get('/api/auth/me/')
assert res.status_code == 401, f"Expected 401, got {res.status_code}"
assert res.json().get('authenticated') is False
print("Passed: session is destroyed on backend.")

# Cleanup test users
User.objects.filter(username__in=["test_superuser", "test_regular_user"]).delete()
print("\nALL AUTHENTICATION TESTS PASSED SUCCESSFULLY!")
