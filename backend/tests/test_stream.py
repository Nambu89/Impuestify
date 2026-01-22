"""
Test script for SSE streaming endpoint
"""
import requests
import json

API_URL = "http://localhost:8000"

def test_streaming_endpoint():
    """Test the /api/ask/stream endpoint"""
    
    # First, try to register (in case user doesn't exist)
    print("📝 Registering test user...")
    register_response = requests.post(
        f"{API_URL}/auth/register",
        json={
            "email": "test@example.com",
            "password": "testpassword123",
            "name": "Test User"
        }
    )
    
    if register_response.status_code == 201:
        print("✅ User registered successfully")
        token = register_response.json().get("tokens", {}).get("access_token")
    elif register_response.status_code == 400:
        print("ℹ️  User already exists, logging in...")
        # User exists, login instead
        login_response = requests.post(
            f"{API_URL}/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpassword123"
            }
        )
        
        if login_response.status_code != 200:
            print(f"❌ Login failed: {login_response.status_code}")
            print(f"Response: {login_response.text}")
            return False
        
        token = login_response.json().get("tokens", {}).get("access_token")
        print(f"✅ Login successful")
    else:
        print(f"❌ Registration failed: {register_response.status_code}")
        print(f"Response: {register_response.text}")
        return False
    
    if not token:
        print("❌ Failed to get authentication token")
        return False
    
    print(f"✅ Got token: {token[:20]}...")
    
    # Test OPTIONS (CORS preflight)
    print("\n🔍 Testing OPTIONS request...")
    options_response = requests.options(f"{API_URL}/api/ask/stream")
    print(f"OPTIONS status: {options_response.status_code}")
    print(f"Allow methods: {options_response.headers.get('Allow', 'N/A')}")
    
    # Test POST to streaming endpoint
    print("\n📡 Testing POST streaming request...")
    try:
        response = requests.post(
            f"{API_URL}/api/ask/stream",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json={
                "question": "¿Cuánto pagaré de IRPF si gano 35000€ brutos al año en Aragón?",
                "conversation_id": None
            },
            stream=True,
            timeout=30
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type', 'N/A')}")
        
        if response.status_code == 200:
            print("\n✅ Streaming response received:")
            print("=" * 60)
            
            # Read SSE stream
            event_count = 0
            for line in response.iter_lines():
                if line:
                    decoded = line.decode('utf-8')
                    if decoded.startswith('event:'):
                        event_type = decoded[6:].strip()
                        print(f"\n📨 Event type: {event_type}")
                    elif decoded.startswith('data:'):
                        data = decoded[5:].strip()
                        if data and data != '[DONE]':
                            try:
                                event_data = json.loads(data)
                                print(f"  Data: {event_data}")
                                event_count += 1
                            except json.JSONDecodeError:
                                print(f"  Raw: {data[:100]}")
            
            print("=" * 60)
            print(f"✅ Stream completed! Received {event_count} events")
            return True
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Testing SSE Streaming Endpoint")
    print("=" * 60)
    success = test_streaming_endpoint()
    print("\n" + "=" * 60)
    if success:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ TESTS FAILED")
