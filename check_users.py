import mysql.connector

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Khamlesh@1234',
    'database': 'dwcra',
    'ssl_disabled': True
}

conn = mysql.connector.connect(**DB_CONFIG)
cursor = conn.cursor(dictionary=True)

print("=" * 80)
print("ALL USERS IN DATABASE:")
print("=" * 80)
cursor.execute('SELECT user_id, unique_id, email, name, role, password_hash FROM users')
for user in cursor.fetchall():
    pwd_hash = user['password_hash'][:50] if user['password_hash'] else "NULL"
    print(f"ID: {user['user_id']:3d} | Unique ID: {user['unique_id']:20s} | Email: {user['email']:25s} | Role: {user['role']:6s}")
    print(f"       Name: {user['name']:30s}")
    print(f"       Hash: {pwd_hash}...")
    print("-" * 80)

cursor.close()
conn.close()
