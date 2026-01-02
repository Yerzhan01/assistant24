import requests
import time
import sys

BASE_URL = "http://localhost:3000/api/v1"

def login():
    try:
        resp = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": "test@test.kz", "password": "test123"}
        )
        resp.raise_for_status()
        token = resp.json()["access_token"]
        print(f"✅ Login successful. Token: {token[:10]}...")
        return token
    except Exception as e:
        print(f"❌ Login failed: {e}")
        sys.exit(1)

def send_msg(token, message):
    print(f"\n📤 Sending: {message}")
    start = time.time()
    try:
        resp = requests.post(
            f"{BASE_URL}/chat",
            json={"message": message},
            headers={"Authorization": f"Bearer {token}"},
            timeout=60
        )
        duration = time.time() - start
        
        if resp.status_code == 200:
            print(f"✅ Response ({duration:.2f}s):")
            print(resp.text[:500])
        else:
            print(f"❌ Error {resp.status_code} ({duration:.2f}s): {resp.text}")
            
    except requests.exceptions.Timeout:
        print(f"❌ Timeout after {time.time() - start:.2f}s")
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    token = login()
    send_msg(token, "запиши мой доход на сегодня 1000тенге")
