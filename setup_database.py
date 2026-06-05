import mysql.connector
from mysql.connector import Error

def setup_database():
    try:
        # Connect to database
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='Khamlesh@1234',
            database='dwcra',
            ssl_disabled=True
        )
        cursor = conn.cursor(dictionary=True)
        
        print("Connected to database successfully!")
        
        # Check existing tables
        cursor.execute("SHOW TABLES")
        existing_tables = [table[list(table.keys())[0]] for table in cursor.fetchall()]
        print(f"Existing tables: {existing_tables}")
        
        # Create missing tables if they don't exist
        tables_to_create = [
            "audit_logs",
            "notifications", 
            "user_activity_logs",
            "reports",
            "loan_tracking",
            "system_settings"
        ]
        
        for table in tables_to_create:
            if table not in existing_tables:
                print(f"Creating table: {table}")
                if table == "audit_logs":
                    cursor.execute('''
                        CREATE TABLE audit_logs (
                            log_id INT AUTO_INCREMENT PRIMARY KEY,
                            admin_id INT NOT NULL,
                            action_type VARCHAR(100) NOT NULL,
                            action_description TEXT NOT NULL,
                            target_table VARCHAR(50) NULL,
                            target_id INT NULL,
                            ip_address VARCHAR(45) NULL,
                            user_agent TEXT NULL,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (admin_id) REFERENCES users(user_id)
                        )
                    ''')
                elif table == "notifications":
                    cursor.execute('''
                        CREATE TABLE notifications (
                            notification_id INT AUTO_INCREMENT PRIMARY KEY,
                            sender_id INT NULL,
                            recipient_id INT NULL,
                            subject VARCHAR(200) NOT NULL,
                            message TEXT NOT NULL,
                            notification_type ENUM('info', 'warning', 'success', 'error') DEFAULT 'info',
                            is_read BOOLEAN DEFAULT FALSE,
                            attachment_path VARCHAR(500) NULL,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (sender_id) REFERENCES users(user_id),
                            FOREIGN KEY (recipient_id) REFERENCES users(user_id)
                        )
                    ''')
                elif table == "user_activity_logs":
                    cursor.execute('''
                        CREATE TABLE user_activity_logs (
                            activity_id INT AUTO_INCREMENT PRIMARY KEY,
                            user_id INT NOT NULL,
                            activity_type VARCHAR(100) NOT NULL,
                            activity_description TEXT NOT NULL,
                            ip_address VARCHAR(45) NULL,
                            user_agent TEXT NULL,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (user_id) REFERENCES users(user_id)
                        )
                    ''')
                elif table == "reports":
                    cursor.execute('''
                        CREATE TABLE reports (
                            report_id INT AUTO_INCREMENT PRIMARY KEY,
                            report_name VARCHAR(200) NOT NULL,
                            report_type VARCHAR(100) NOT NULL,
                            generated_by INT NOT NULL,
                            file_path VARCHAR(500) NULL,
                            parameters JSON NULL,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (generated_by) REFERENCES users(user_id)
                        )
                    ''')
                elif table == "loan_tracking":
                    cursor.execute('''
                        CREATE TABLE loan_tracking (
                            tracking_id INT AUTO_INCREMENT PRIMARY KEY,
                            loan_id INT NOT NULL,
                            user_id INT NOT NULL,
                            tracking_type ENUM('payment_missed', 'payment_due', 'loan_overdue', 'suspicious_activity') NOT NULL,
                            description TEXT NOT NULL,
                            severity ENUM('low', 'medium', 'high', 'critical') DEFAULT 'medium',
                            is_resolved BOOLEAN DEFAULT FALSE,
                            resolved_by INT NULL,
                            resolved_at DATETIME NULL,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (loan_id) REFERENCES loans(loan_id),
                            FOREIGN KEY (user_id) REFERENCES users(user_id),
                            FOREIGN KEY (resolved_by) REFERENCES users(user_id)
                        )
                    ''')
                elif table == "system_settings":
                    cursor.execute('''
                        CREATE TABLE system_settings (
                            setting_id INT AUTO_INCREMENT PRIMARY KEY,
                            setting_key VARCHAR(100) NOT NULL UNIQUE,
                            setting_value TEXT NOT NULL,
                            setting_description TEXT NULL,
                            updated_by INT NULL,
                            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                            FOREIGN KEY (updated_by) REFERENCES users(user_id)
                        )
                    ''')
                    
                    # Insert default settings
                    cursor.execute('''
                        INSERT IGNORE INTO system_settings (setting_key, setting_value, setting_description) VALUES
                        ('max_loan_amount', '100000', 'Maximum loan amount allowed'),
                        ('min_group_size', '6', 'Minimum number of members required in a group'),
                        ('max_group_size', '7', 'Maximum number of members allowed in a group'),
                        ('payment_reminder_days', '5', 'Days before payment due to send reminder'),
                        ('system_language', 'en', 'Default system language (en/te)'),
                        ('email_notifications_enabled', 'true', 'Enable/disable email notifications'),
                        ('maintenance_mode', 'false', 'Enable/disable maintenance mode')
                    ''')
        
        # Update existing tables if needed
        try:
            # Check if columns exist before adding them
            cursor.execute("SHOW COLUMNS FROM users LIKE 'is_active'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE")
            
            cursor.execute("SHOW COLUMNS FROM users LIKE 'created_at'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE users ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP")
            
            cursor.execute("SHOW COLUMNS FROM users LIKE 'updated_at'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE users ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
            
            cursor.execute("SHOW COLUMNS FROM loans LIKE 'disbursement_date'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE loans ADD COLUMN disbursement_date DATE NULL")
            
            cursor.execute("SHOW COLUMNS FROM loans LIKE 'repayment_terms'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE loans ADD COLUMN repayment_terms TEXT NULL")
            
            cursor.execute("SHOW COLUMNS FROM loans LIKE 'created_at'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE loans ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP")
            
            cursor.execute("SHOW COLUMNS FROM loans LIKE 'updated_at'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE loans ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
            
            cursor.execute("SHOW COLUMNS FROM payments LIKE 'created_at'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE payments ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP")
            
            cursor.execute("SHOW COLUMNS FROM identity_verification LIKE 'verified_by'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE identity_verification ADD COLUMN verified_by INT NULL")
            
            cursor.execute("SHOW COLUMNS FROM identity_verification LIKE 'verification_status'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE identity_verification ADD COLUMN verification_status ENUM('pending', 'verified', 'rejected') DEFAULT 'verified'")
            
        except Error as e:
            print(f"Error updating tables: {e}")
        
        conn.commit()
        print("Database setup completed successfully!")
        
        # Check admin user exists
        cursor.execute("SELECT * FROM users WHERE unique_id = 'ADMIN001'")
        admin = cursor.fetchone()
        if admin:
            print(f"Admin user found: {admin['name']} ({admin['email']})")
        else:
            print("Admin user not found!")
        
        cursor.close()
        conn.close()
        
    except Error as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    setup_database() 