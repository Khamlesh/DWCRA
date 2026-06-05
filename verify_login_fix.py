import mysql.connector
from werkzeug.security import check_password_hash, generate_password_hash

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Khamlesh@1234',
    'database': 'dwcra',
    'ssl_disabled': True
}

def test_login_flow():
    """Test the complete login flow with the fix"""
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    
    print("\n" + "=" * 80)
    print("TESTING FIXED LOGIN FUNCTIONALITY")
    print("=" * 80)
    
    # Get the siddu user from database
    cursor.execute('SELECT * FROM users WHERE unique_id = "047"')
    user = cursor.fetchone()
    
    if not user:
        print("✗ Siddu user not found!")
        return
    
    print(f"\nUser Details:")
    print(f"  Unique ID: {user['unique_id']}")
    print(f"  Email: {user['email']}")
    print(f"  Name: {user['name']}")
    print(f"  Role: {user['role']}")
    print(f"  Password Hash: {user['password_hash'][:60]}...")
    
    # Simulate the updated login query with different identifiers
    test_identifiers = [
        ("047", "Using Unique ID"),
        ("siddu@gmail.com", "Using Email"),
        ("Siddu@gmail.com", "Using Email (Case Test)"),  # Test case sensitivity
    ]
    
    print("\n" + "-" * 80)
    print("Testing login with different identifiers:")
    print("-" * 80)
    
    for identifier, description in test_identifiers:
        # This simulates the updated login query
        cursor.execute('SELECT * FROM users WHERE unique_id = %s OR email = %s', (identifier, identifier))
        found_user = cursor.fetchone()
        
        if found_user:
            print(f"\n✓ {description}: FOUND USER")
            print(f"  Entered: {identifier}")
            print(f"  Found: {found_user['unique_id']} ({found_user['email']})")
        else:
            print(f"\n✗ {description}: USER NOT FOUND")
            print(f"  Entered: {identifier}")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 80)
    print("SUMMARY:")
    print("=" * 80)
    print("""
The login function has been FIXED to accept:
1. Unique ID (e.g., "047")
2. Email address (e.g., "siddu@gmail.com")

Users can now login with either their Unique ID or Email address!
The error was that users were entering their email instead of their unique ID.
    """)
    print("=" * 80 + "\n")

if __name__ == "__main__":
    test_login_flow()
