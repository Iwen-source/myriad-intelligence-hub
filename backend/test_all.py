"""Test all API endpoints"""
import urllib.request
import json

BASE = "http://localhost:8088"

# Login
login_data = json.dumps({"username": "admin", "password": "admin123456"}).encode()
req = urllib.request.Request(f"{BASE}/api/auth/login", data=login_data,
                             headers={"Content-Type": "application/json"})
resp = urllib.request.urlopen(req)
login = json.load(resp)
token = login["data"]["token"]
print(f"[LOGIN] {login['code']} {login['message']}")

headers = {"Authorization": f"Bearer {token}"}

def test(method, path, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        resp = urllib.request.urlopen(req)
        d = json.load(resp)
        status = "OK" if d.get("code") == 200 else "FAIL"
        info = ""
        if isinstance(d.get("data"), list):
            info = f" ({len(d['data'])} items)"
        if isinstance(d.get("data"), dict):
            if "isMlGenerated" in d["data"]:
                info = f" (isMlGenerated={d['data']['isMlGenerated']})"
            if "isCarbonMlEstimated" in d["data"]:
                info = f" (carbonMlEstimated={d['data']['isCarbonMlEstimated']})"
            if "predictions" in d["data"]:
                info = f" ({len(d['data']['predictions'])} preds, isMlGenerated={d['data']['predictions'][0].get('isMlGenerated','?')})" if d["data"]["predictions"] else " (no preds)"
        print(f"[{method:3s}] {path:55s} {status}{info}")
        return True
    except urllib.error.HTTPError as e:
        print(f"[{method:3s}] {path:55s} ERROR {e.code} - {e.reason}")
        return False
    except Exception as e:
        print(f"[{method:3s}] {path:55s} FAIL - {str(e)[:80]}")
        return False

# Medical
test("GET", "/api/medical/patients")
test("GET", "/api/medical/patients/1")
test("GET", "/api/medical/disease-library/overview")
test("POST", "/api/medical/ai-doctor/consult",
     {"name": "Test", "age": 30, "gender": "M", "symptoms": "fever,cough",
      "durationDays": 3, "history": "", "medications": ""})

# Finance
test("GET", "/api/finance/analysis/suspicious")
test("GET", "/api/finance/analysis/trend-prediction?days=3")
test("GET", "/api/finance/analysis/user-profiles")
test("GET", "/api/finance/analysis/rule-hits")
test("GET", "/api/finance/analysis/risk/1")
test("GET", "/api/finance/analysis/multi-risk/1")
test("GET", "/api/finance/analysis/market/predict")

# Environment
test("GET", "/api/environment/analysis/prediction?days=3")
test("GET", "/api/environment/analysis/alerts")
test("GET", "/api/environment/analysis/health-index")
test("GET", "/api/environment/analysis/pollution-source")

# Energy
test("GET", "/api/energy/analysis/prediction?days=3")
test("GET", "/api/energy/analysis/anomalies")
test("GET", "/api/energy/analysis/optimization")

# Traffic
test("GET", "/api/traffic/analysis/congestion")
test("GET", "/api/traffic/analysis/routes")
test("GET", "/api/traffic/analysis/prediction-calendar?days=3")
test("GET", "/api/traffic/analysis/heatmap")
test("GET", "/api/traffic/analysis/anomalies")

# MISC page endpoints
test("GET", "/api/energy/devices")
test("GET", "/api/traffic/sections")
test("GET", "/api/finance/transactions")
test("GET", "/api/environment/monitor-points")

print("\n=== DONE ===")
