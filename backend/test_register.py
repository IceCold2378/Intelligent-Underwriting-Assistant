"""Quick diagnostic: test the /auth/register endpoint."""
import urllib.request
import urllib.error
import json

url = "http://localhost:8000/api/v1/auth/register"
payload = {
    "email": "diag001@example.com",
    "password": "testpass123",
    "full_name": "Diag User",
    "organization": "TestCorp",
}
data = json.dumps(payload).encode()
req = urllib.request.Request(
    url, data=data, headers={"Content-Type": "application/json"}, method="POST"
)
try:
    with urllib.request.urlopen(req) as resp:
        print("STATUS:", resp.status)
        print("BODY:", resp.read().decode())
except urllib.error.HTTPError as e:
    print("HTTP ERROR:", e.code)
    print("BODY:", e.read().decode())
except Exception as exc:
    print("ERROR:", exc)
