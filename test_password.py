import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

# Test database connection and password verification
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Khamlesh@1234',
    'database': 'dwcra',
    'ssl_disabled': True
}

try:
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    
    # Check if kg@gmail.com user exists
    cursor.execute('SELECT * FROM users WHERE email = %s', ('kg@gmail.com',))
    user = cursor.fetchone()
    
    if user:
        print(f"✓ User found: {user['name']}")
        print(f"  Email: {user['email']}")
        print(f"  Unique ID: {user['unique_id']}")
        print(f"  Role: {user['role']}")
        print(f"  Password hash: {user['password_hash'][:50]}...")
        
        # Test with a password (change this to what you registered)
        test_password = "your_password_here"  # Change to your password
        
        if check_password_hash(user['password_hash'], test_password):
            print(f"✓ Password verification PASSED with: {test_password}")
        else:
            print(f"✗ Password verification FAILED with: {test_password}")
            print(f"\nTry your actual password to test")
    else:
        print("✗ User not found in database")
        print("\nAll users:")
        cursor.execute('SELECT unique_id, email, name FROM users LIMIT 10')
        for u in cursor.fetchall():
            print(f"  - {u['unique_id']} ({u['email']}) - {u['name']}")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"✗ Error: {e}")
