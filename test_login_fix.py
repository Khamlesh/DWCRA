import mysql.connector
from werkzeug.security import check_password_hash

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Khamlesh@1234',
    'database': 'dwcra',
    'ssl_disabled': True
}

def test_login(identifier, password):
    """Test login with identifier (unique_id or email) and password"""
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    
    # Match the updated login query
    cursor.execute('SELECT * FROM users WHERE unique_id = %s OR email = %s', (identifier, identifier))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if user:
        print(f"✓ User found: {user['name']}")
        print(f"  Unique ID: {user['unique_id']}")
        print(f"  Email: {user['email']}")
        
        if check_password_hash(user['password_hash'], password):
            print(f"✓ Password verification PASSED for: {identifier}")
            return True
        else:
            print(f"✗ Password verification FAILED for: {identifier}")
            print(f"  Password entered: {password}")
            return False
    else:
        print(f"✗ User not found with identifier: {identifier}")
        return False

print("=" * 80)
print("TESTING LOGIN FUNCTIONALITY")
print("=" * 80)

# Test users from database
test_cases = [
    ("047", "password_to_test"),      # siddu unique_id
    ("siddu@gmail.com", "password_to_test"),  # siddu email
    ("0808", "password_to_test"),    # Khamlesh unique_id
    ("Khamlesh@gmail.com", "password_to_test"), # Khamlesh email
]

for identifier, password in test_cases:
    print(f"\nTest Login with: {identifier}")
    print("-" * 80)
    test_login(identifier, password)

print("\n" + "=" * 80)
print("NOTE: Update 'password_to_test' with the actual password to verify!")
print("=" * 80)
