"""
Automated test script for the Task CRUD API.
Run with: python test_api.py
Requires the server to be running on http://localhost:8000
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
        body = response.json()
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
print("  Task CRUD API — Full Test Suite")
print("=" * 60)

# --- General ---
print("\n--- General Endpoints ---")
test("GET /", requests.get(f"{BASE}/"), 200, {"name": "Task API"})
test("GET /health", requests.get(f"{BASE}/health"), 200, {"status": "ok"})
test("GET /docs (Swagger)", requests.get(f"{BASE}/docs"), 200)
test("GET /openapi.json", requests.get(f"{BASE}/openapi.json"), 200)

# --- Read ---
print("\n--- Read Endpoints ---")
test("GET /tasks (list all)", requests.get(f"{BASE}/tasks"), 200)
test("GET /tasks/1 (exists)", requests.get(f"{BASE}/tasks/1"), 200, {"id": 1})
test("GET /tasks/999 (not found)", requests.get(f"{BASE}/tasks/999"), 404)

# --- Create ---
print("\n--- Create Endpoint ---")
r = requests.post(f"{BASE}/tasks", json={"title": "Test task"})
test("POST /tasks (valid)", r, 201)
new_id = r.json().get("id") if r.status_code == 201 else None
test("POST /tasks (empty body)", requests.post(f"{BASE}/tasks", json={}), 400)
test("POST /tasks (empty title)", requests.post(f"{BASE}/tasks", json={"title": ""}), 400)
test("POST /tasks (whitespace title)", requests.post(f"{BASE}/tasks", json={"title": "   "}), 400)

# Verify the created task is readable
if new_id:
    test(f"GET /tasks/{new_id} (just created)", requests.get(f"{BASE}/tasks/{new_id}"), 200, {"id": new_id, "title": "Test task", "done": False})

# --- Update ---
print("\n--- Update Endpoint ---")
test("PUT /tasks/1 (update title)", requests.put(f"{BASE}/tasks/1", json={"title": "Updated groceries"}), 200)
test("PUT /tasks/1 (mark done)", requests.put(f"{BASE}/tasks/1", json={"done": True}), 200, {"done": True})
test("PUT /tasks/1 (update both)", requests.put(f"{BASE}/tasks/1", json={"title": "Final title", "done": False}), 200)
test("PUT /tasks/999 (not found)", requests.put(f"{BASE}/tasks/999", json={"title": "x"}), 404)
test("PUT /tasks/1 (empty body)", requests.put(f"{BASE}/tasks/1", json={}), 400)
test("PUT /tasks/1 (empty title)", requests.put(f"{BASE}/tasks/1", json={"title": ""}), 400)
test("PUT /tasks/1 (bad done type)", requests.put(f"{BASE}/tasks/1", json={"done": "yes"}), 400)

# --- Delete ---
print("\n--- Delete Endpoint ---")
test("DELETE /tasks/2 (exists)", requests.delete(f"{BASE}/tasks/2"), 204)
test("GET /tasks/2 (after delete)", requests.get(f"{BASE}/tasks/2"), 404)
test("DELETE /tasks/999 (not found)", requests.delete(f"{BASE}/tasks/999"), 404)

# --- Summary ---
print("\n" + "=" * 60)
total = passed + failed
print(f"  Results: {passed}/{total} passed, {failed} failed")
print("=" * 60)

sys.exit(0 if failed == 0 else 1)
