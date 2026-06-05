import mysql.connector
from werkzeug.security import generate_password_hash
import os

# Database configuration - matching app.py
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Khamlesh@1234',
    'database': 'dwcra',
    'ssl_disabled': True
}

def create_admin_user():
    try:
        # Connect to database
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # Admin credentials
        admin_credentials = {
            'unique_id': 'ADMIN001',
            'name': 'System Administrator',
            'email': 'admin@dwcra.com',
            'password': 'Admin@123',  # You can change this password
            'role': 'admin',
            'bank_name': 'DWCRA Bank'
        }
        
        # Check if admin already exists
        cursor.execute('SELECT * FROM users WHERE unique_id = %s OR email = %s', 
                      (admin_credentials['unique_id'], admin_credentials['email']))
        existing_admin = cursor.fetchone()
        
        if existing_admin:
            print("Admin user already exists!")
            print(f"Unique ID: {existing_admin['unique_id']}")
            print(f"Email: {existing_admin['email']}")
            print("If you need to reset the password, please do it manually in the database.")
        else:
            # Create admin user
            password_hash = generate_password_hash(admin_credentials['password'])
            cursor.execute('''
                INSERT INTO users (unique_id, name, email, password_hash, role, bank_name) 
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (
                admin_credentials['unique_id'],
                admin_credentials['name'],
                admin_credentials['email'],
                password_hash,
                admin_credentials['role'],
                admin_credentials['bank_name']
            ))
            conn.commit()
            print("Admin user created successfully!")
            print("=" * 50)
            print("ADMIN CREDENTIALS:")
            print("=" * 50)
            print(f"Unique ID: {admin_credentials['unique_id']}")
            print(f"Email: {admin_credentials['email']}")
            print(f"Password: {admin_credentials['password']}")
            print(f"Role: {admin_credentials['role']}")
            print("=" * 50)
            print("IMPORTANT: Change the password after first login for security!")
        
        cursor.close()
        conn.close()
        
    except mysql.connector.Error as err:
        print(f"Database error: {err}")
        print("\nPlease check your database configuration:")
        print(f"Host: {DB_CONFIG['host']}")
        print(f"User: {DB_CONFIG['user']}")
        print(f"Database: {DB_CONFIG['database']}")
        print("Make sure the database exists and the credentials are correct.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("Creating admin user for DWCRA Portal...")
    print("Make sure your MySQL server is running and the database exists.")
    print()
    
    # Ask user to confirm database settings
    print("Current database settings:")
    print(f"Host: {DB_CONFIG['host']}")
    print(f"User: {DB_CONFIG['user']}")
    print(f"Database: {DB_CONFIG['database']}")
    print()
    
    response = input("Do you want to proceed with these settings? (y/n): ")
    if response.lower() in ['y', 'yes']:
        create_admin_user()
    else:
        print("Please update the DB_CONFIG in this script with your database settings and run again.") 