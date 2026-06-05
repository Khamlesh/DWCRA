import requests
import json

def test_admin_login():
    """Test admin login functionality"""
    base_url = "http://localhost:5000"
    
    # Test admin login
    login_data = {
        'unique_id': 'ADMIN001',
        'password': 'Admin@123'
    }
    
    try:
        # Test login
        response = requests.post(f"{base_url}/login", data=login_data)
        print(f"Login response status: {response.status_code}")
        
        if response.status_code == 302:  # Redirect after successful login
            print("✅ Admin login successful!")
            
            # Test admin dashboard access
            session = requests.Session()
            session.post(f"{base_url}/login", data=login_data)
            
            # Test various admin routes
            routes_to_test = [
                "/admin_dashboard",
                "/admin/users",
                "/admin/groups", 
                "/admin/loans",
                "/admin/reports",
                "/admin/notifications",
                "/admin/audit-logs"
            ]
            
            for route in routes_to_test:
                try:
                    response = session.get(f"{base_url}{route}")
                    if response.status_code == 200:
                        print(f"✅ {route} - Accessible")
                    else:
                        print(f"❌ {route} - Status: {response.status_code}")
                except Exception as e:
                    print(f"❌ {route} - Error: {e}")
                    
        else:
            print("❌ Admin login failed!")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Connection error: {e}")

if __name__ == "__main__":
    print("Testing DWCRA Admin Portal...")
    print("=" * 50)
    test_admin_login()
    print("=" * 50)
    print("Test completed!") 