import requests

BASE_URL = "http://127.0.0.1:5000"

# Test routes
routes = [
    "/feedback",
    "/report",
    "/report-preview",
    "/api/feedback/",
    "/api/feedback/report/",
    "/api/dashboard/refresh/"
]

for route in routes:
    try:
        response = requests.get(f"{BASE_URL}{route}")
        print(f"✅ {route}: {response.status_code}")
    except Exception as e:
        print(f"❌ {route}: {e}")