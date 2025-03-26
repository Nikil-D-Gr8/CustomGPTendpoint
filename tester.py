import requests
# https://drive.google.com/file/d/1vNKQI4hrxkwx-2ck8z4D7ugPL4QvVMr3/view?usp=sharing
BASE_URL = "https://s8zqg06h-5000.inc1.devtunnels.ms"

# === Step 1: POST /store ===
store_url = f"{BASE_URL}/store"
store_payload = {
    "file_id": "1vNKQI4hrxkwx-2ck8z4D7ugPL4QvVMr3",
    "collection": "pythonnote"
}

print("Sending POST to /store...")
store_response = requests.post(
    store_url,
    json=store_payload,
    headers={"Content-Type": "application/json"}
)

print("Store Response:")
print("Status Code:", store_response.status_code)
try:
    print("JSON:", store_response.json())
except Exception:
    print("Raw Response:", store_response.text)

# === Step 2: GET /query ===
query_url = f"{BASE_URL}/query"
query_params = {
    "query": "is python an interpreted language",
    "collection": "pythonnote"
}

print("\nSending GET to /query...")
query_response = requests.get(
    query_url,
    params=query_params,
    headers={"Accept": "application/json"}
)

print("Query Response:")
print("Status Code:", query_response.status_code)
try:
    print("JSON:", query_response.json())
except Exception:
    print("Raw Response:", query_response.text)
