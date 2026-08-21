"""
Automated test suite for Supabase / JWT Authentication and Protected Routes.
Run with: python test_auth.py
"""

import requests
import sys

BASE = "http://localhost:8000"
passed = 0
failed = 0


def test(name, response, expected_status, check_json=None):
    global passed, failed
    ok = response.status_code == expected_status
    if check_json and ok:
        body = response.json() if response.text else {}
        for key, val in check_json.items():
            if body.get(key) != val:
                ok = False
                break
    status = "PASS" if ok else "FAIL"
    if ok:
        passed += 1
    else:
        failed += 1
    print(f"  [{status}] {name} -> {response.status_code} (expected {expected_status})")
    if not ok and response.text:
        print(f"         Body: {response.text[:200]}")


print("=" * 60)
print("  Auth · Login & Protect — Full Test Suite")
print("=" * 60)

# --- Stage 1 & 2: Public Route ---
print("\n--- Public Gate ---")
test("GET /public/info (no auth)", requests.get(f"{BASE}/public/info"), 200, {"message": "Welcome stranger! This info is public."})

# --- Stage 1: Sign Up & Login Validation ---
print("\n--- Sign Up & Login ---")
test("POST /auth/signup (empty body)", requests.post(f"{BASE}/auth/signup", json={}), 400)
test("POST /auth/signup (missing password)", requests.post(f"{BASE}/auth/signup", json={"email": "tester@example.com"}), 400)
test("POST /auth/signup (missing email)", requests.post(f"{BASE}/auth/signup", json={"password": "secret"}), 400)

signup_res = requests.post(f"{BASE}/auth/signup", json={"email": "student@example.com", "password": "password123"})
test("POST /auth/signup (valid credentials)", signup_res, 201)

test("POST /auth/login (empty body)", requests.post(f"{BASE}/auth/login", json={}), 400)
test("POST /auth/login (wrong password)", requests.post(f"{BASE}/auth/login", json={"email": "student@example.com", "password": "wrong"}), 401)

login_res = requests.post(f"{BASE}/auth/login", json={"email": "student@example.com", "password": "password123"})
test("POST /auth/login (valid credentials)", login_res, 200)

token_data = login_res.json() if login_res.status_code == 200 else {}
access_token = token_data.get("access_token")

# --- Stage 2 & 3: Protected Profile Route ---
print("\n--- Protected Profile Route ---")
test("GET /protected/profile (no token)", requests.get(f"{BASE}/protected/profile"), 401)
test("GET /protected/profile (malformed header)", requests.get(f"{BASE}/protected/profile", headers={"Authorization": "Basic 1234"}), 401)
test("GET /protected/profile (forged/tampered token)", requests.get(f"{BASE}/protected/profile", headers={"Authorization": "Bearer invalid_forged_token_xyz"}), 401)

if access_token:
    test(
        "GET /protected/profile (valid Bearer token)",
        requests.get(f"{BASE}/protected/profile", headers={"Authorization": f"Bearer {access_token}"}),
        200,
        {"email": "student@example.com"}
    )
    # Stage 4: Second protected route reusing middleware
    test(
        "GET /protected/dashboard (valid token)",
        requests.get(f"{BASE}/protected/dashboard", headers={"Authorization": f"Bearer {access_token}"}),
        200
    )
    # Stage 4: Logout endpoint
    test(
        "POST /auth/logout (valid token)",
        requests.post(f"{BASE}/auth/logout", headers={"Authorization": f"Bearer {access_token}"}),
        204
    )

# --- Stretch: 403 Forbidden Demo ---
print("\n--- 403 Forbidden Stretch ---")
if access_token:
    test(
        "GET /protected/admin (non-admin token)",
        requests.get(f"{BASE}/protected/admin", headers={"Authorization": f"Bearer {access_token}"}),
        403
    )

# --- Summary ---
print("\n" + "=" * 60)
total = passed + failed
print(f"  Results: {passed}/{total} passed, {failed} failed")
print("=" * 60)

sys.exit(0 if failed == 0 else 1)
