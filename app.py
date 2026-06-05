from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask_mail import Mail, Message
import os
from dotenv import load_dotenv
import json
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from decimal import Decimal
import re
import time
import csv
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Serve static files
@app.route('/static/<path:filename>')
def static_files(filename):
    return app.send_static_file(filename)

# Load translations
def load_translations(lang):
    with open(f'translations/{lang}.json', 'r', encoding='utf-8') as f:
        return json.load(f)

@app.context_processor
def inject_translations():
    lang = session.get('language', 'en') # Default to English
    translations = load_translations(lang)
    role = getattr(current_user, 'role', None)
    user_name = getattr(current_user, 'name', None)
    unique_id = getattr(current_user, 'unique_id', None)
    return dict(
        translations=translations, 
        current_language=lang, 
        user_logged_in=current_user.is_authenticated,
        role=role,
        user_name=user_name,
        unique_id=unique_id,
        now=datetime.now()
    )

@app.route('/language/<lang>')
def set_language(lang):
    session['language'] = lang
    return redirect(request.referrer or url_for('home'))

# MySQL connection configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Khamlesh@1234',
    'database': 'dwcra',
    'ssl_disabled': True
}

# Helper function to get fresh database connection
def get_db():
    """Get a fresh database connection and cursor for each request"""
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    return conn, cursor

# Initialize connection for load_user (will be called at startup)
conn = mysql.connector.connect(**DB_CONFIG)
cursor = conn.cursor(dictionary=True)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)

# Flask-Mail setup
load_dotenv()
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
mail = Mail(app)

serializer = URLSafeTimedSerializer(app.secret_key)

def is_system_administrator():
    """Check if the current user is the system administrator"""
    return current_user.is_authenticated and current_user.unique_id == 'ADMIN001'

class User(UserMixin):
    def __init__(self, user_id, unique_id, name, email, role):
        self.id = user_id
        self.unique_id = unique_id
        self.name = name
        self.email = email
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    db_conn, db_cursor = get_db()
    db_cursor.execute('SELECT * FROM users WHERE user_id = %s', (user_id,))
    user = db_cursor.fetchone()
    db_cursor.close()
    db_conn.close()
    if user:
        return User(user['user_id'], user['unique_id'], user['name'], user['email'], user['role'])
    return None

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        unique_id = request.form.get('unique_id')
        name = request.form.get('name')
        email = request.form.get('email')
        bank_name = request.form.get('bank_name')
        password = request.form.get('password')
        role = request.form.get('role')
        if not bank_name:
            flash('Bank Name is required.', 'danger')
            return render_template('register.html', user_name=None)
        if role not in ['leader', 'member', 'admin']:
            flash('Invalid role selected.', 'danger')
            return render_template('register.html', user_name=None)
        password_hash = generate_password_hash(password)
        try:
            db_conn, db_cursor = get_db()
            db_cursor.execute('INSERT INTO users (unique_id, name, email, password_hash, role, bank_name) VALUES (%s, %s, %s, %s, %s, %s)',
                           (unique_id, name, email, password_hash, role, bank_name))
            db_conn.commit()
            db_cursor.close()
            db_conn.close()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('home'))
        except mysql.connector.Error:
            flash('Registration failed. Unique ID or email may already exist.', 'danger')
    return render_template('register.html', user_name=None)

@app.route('/login', methods=['POST'])
def login():
    unique_id = request.form['unique_id']
    password = request.form['password']
    db_conn, db_cursor = get_db()
    # Allow login with either unique_id or email
    db_cursor.execute('SELECT * FROM users WHERE unique_id = %s OR email = %s', (unique_id, unique_id))
    user = db_cursor.fetchone()
    db_cursor.close()
    db_conn.close()
    if user and check_password_hash(user['password_hash'], password):
        user_obj = User(user['user_id'], user['unique_id'], user['name'], user['email'], user['role'])
        login_user(user_obj)
        return redirect(url_for('home_page'))
    flash('Invalid credentials', 'danger')
    return redirect(url_for('home'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/create_group', methods=['GET', 'POST'])
@login_required
def create_group():
    if current_user.role != 'leader':
        return redirect(url_for('member_dashboard'))
    
    db_conn, db_cursor = get_db()
    # Check if leader has verified their identity
    db_cursor.execute('SELECT * FROM identity_verification WHERE user_id = %s', (current_user.id,))
    leader_verification = db_cursor.fetchone()
    if not leader_verification:
        db_cursor.close()
        db_conn.close()
        flash('You must verify your identity in your profile before creating a group.', 'danger')
        return redirect(url_for('leader_dashboard'))
    
    db_cursor.execute('SELECT * FROM `groups` WHERE leader_id = %s', (current_user.id,))
    group = db_cursor.fetchone()
    if group:
        db_cursor.close()
        db_conn.close()
        flash('You have already created a group.', 'info')
        return redirect(url_for('leader_dashboard'))
    
    if request.method == 'POST':
        member_ids = [request.form.get(f'member{i}') for i in range(1, 7)]
        # Validate all unique IDs and bank names
        valid_members = []
        unverified_members = []
        leader_bank = None
        db_cursor.execute('SELECT bank_name FROM users WHERE user_id = %s', (current_user.id,))
        leader_bank = db_cursor.fetchone()['bank_name']
        
        for uid in member_ids:
            db_cursor.execute('SELECT * FROM users WHERE unique_id = %s AND role = %s', (uid, 'member'))
            user = db_cursor.fetchone()
            if user:
                if user['bank_name'] != leader_bank:
                    db_cursor.close()
                    db_conn.close()
                    flash('All group members must belong to the same bank as the leader.', 'danger')
                    return render_template('create_group.html', role=current_user.role, user_name=current_user.name)
                
                # Check if member has verified their identity
                db_cursor.execute('SELECT * FROM identity_verification WHERE user_id = %s', (user['user_id'],))
                member_verification = db_cursor.fetchone()
                if not member_verification:
                    unverified_members.append(user['name'])
                else:
                    valid_members.append(user['user_id'])
        
        if len(valid_members) != 6:
            db_cursor.close()
            db_conn.close()
            if unverified_members:
                flash(f'The following members have not verified their identity: {", ".join(unverified_members)}. All members must verify their identity before joining a group.', 'danger')
            else:
                flash('All 6 member unique IDs must be valid and registered as members.', 'danger')
            return render_template('create_group.html', role=current_user.role, user_name=current_user.name)
        
        # Create group
        db_cursor.execute('INSERT INTO `groups` (leader_id) VALUES (%s)', (current_user.id,))
        db_conn.commit()
        group_id = db_cursor.lastrowid
        # Add leader and members to group_members
        db_cursor.execute('INSERT INTO group_members (group_id, user_id) VALUES (%s, %s)', (group_id, current_user.id))
        for member_id in valid_members:
            db_cursor.execute('INSERT INTO group_members (group_id, user_id) VALUES (%s, %s)', (group_id, member_id))
        db_conn.commit()
        db_cursor.close()
        db_conn.close()
        flash('Group created successfully! All members have verified their identity.', 'success')
        return redirect(url_for('leader_dashboard'))
    
    db_cursor.close()
    db_conn.close()
    return render_template('create_group.html', role=current_user.role, user_name=current_user.name)

@app.route('/leader_dashboard')
@login_required
def leader_dashboard():
    if current_user.role != 'leader':
        return redirect(url_for('member_dashboard'))
    # Show group status
    cursor.execute('SELECT * FROM `groups` WHERE leader_id = %s', (current_user.id,))
    group = cursor.fetchone()
    group_status = None
    group_payment_data = None
    progress = 0
    group_members = []
    if group:
        cursor.execute('SELECT u.name, u.email, u.user_id, u.unique_id FROM group_members gm JOIN users u ON gm.user_id = u.user_id WHERE gm.group_id = %s', (group['group_id'],))
        members = cursor.fetchall()
        if members:
            group_status = {
                'group_id': group['group_id'],
                'members': [m['name'] for m in members],
                'count': len(members)
            }
        cursor.execute('SELECT * FROM loans WHERE group_id = %s', (group['group_id'],))
        loan = cursor.fetchone()
        for m in members:
            member_record = {
                'user_id': m['user_id'],
                'name': m['name'],
                'email': m['email'],
                'unique_id': m['unique_id'],
                'paid_count': 0,
                'last_paid': None,
                'verification_status': 'Not Verified',
                'status': 'No Loan'
            }
            cursor.execute('SELECT verification_status FROM identity_verification WHERE user_id = %s', (m['user_id'],))
            verification = cursor.fetchone()
            if verification and verification.get('verification_status'):
                member_record['verification_status'] = verification['verification_status'].title()
            group_members.append(member_record)
        if loan:
            start_date = loan['start_date']
            months_passed = (datetime.now().year - start_date.year) * 12 + (datetime.now().month - start_date.month) + 1
            for m in group_members:
                cursor.execute('SELECT COUNT(*) as paid_count, MAX(paid_on) as last_paid FROM payments WHERE user_id = %s AND loan_id = %s AND status = %s',
                               (m['user_id'], loan['loan_id'], 'paid'))
                payment_summary = cursor.fetchone()
                paid_count = payment_summary['paid_count'] if payment_summary else 0
                m['paid_count'] = paid_count
                m['last_paid'] = payment_summary['last_paid'] if payment_summary else None
                m['status'] = 'Paid' if paid_count >= months_passed and months_passed <= 12 else 'Pending'
                if not m['last_paid']:
                    m['status'] = 'Pending'
                if m['user_id'] == current_user.id:
                    m['status'] = 'Leader'
                if not m['last_paid'] and months_passed > 0:
                    try:
                        send_email(m['email'], 'DWCRA Loan Payment Reminder', f'Dear {m["name"]},\nYour monthly loan payment for month {months_passed} is due. Please log in and pay as soon as possible.')
                    except Exception:
                        pass
            # Group payment completion data for chart
            group_payment_data = {'labels': [], 'datasets': []}
            for m in group_members:
                cursor.execute('SELECT month, year, status FROM payments WHERE user_id = %s AND loan_id = %s ORDER BY year, month', (m['user_id'], loan['loan_id']))
                payments = cursor.fetchall()
                paid_months = [0]*12
                for p in payments:
                    if p['status'] == 'paid' and 1 <= p['month'] <= 12:
                        paid_months[p['month']-1] = 1
                group_payment_data['datasets'].append({'label': m['name'], 'data': paid_months})
            group_payment_data['labels'] = [f'Month {i+1}' for i in range(12)]
            # Progress calculation
            cursor.execute('SELECT COUNT(*) as paid_count FROM payments WHERE group_id = %s AND loan_id = %s AND status = %s', (group['group_id'], loan['loan_id'], 'paid'))
            paid_count = cursor.fetchone()['paid_count']
            progress = int((paid_count / (7*12)) * 100)
    return render_template(
        'leader_dashboard.html',
        name=current_user.name,
        group_status=group_status,
        group_members=group_members,
        group_payment_data=json.dumps(group_payment_data) if group_payment_data else None,
        progress=progress,
        role=current_user.role,
        user_name=current_user.name
    )

@app.route('/leader/group_members_pdf')
@login_required
def leader_group_members_pdf():
    if current_user.role != 'leader':
        return redirect(url_for('member_dashboard'))

    db_conn, db_cursor = get_db()
    try:
        db_cursor.execute('SELECT * FROM `groups` WHERE leader_id = %s', (current_user.id,))
        group = db_cursor.fetchone()
        if not group:
            flash('You do not have an active group to export.', 'danger')
            return redirect(url_for('leader_dashboard'))

        db_cursor.execute('SELECT u.name, u.email, u.unique_id, u.user_id FROM group_members gm JOIN users u ON gm.user_id = u.user_id WHERE gm.group_id = %s', (group['group_id'],))
        members = db_cursor.fetchall()

        output = BytesIO()
        pdf = canvas.Canvas(output, pagesize=letter)
        pdf.setTitle(f'Group_{group["group_id"]}_Members')

        pdf.setFont('Helvetica-Bold', 16)
        pdf.drawString(50, 760, f'DWCRA Group Members Report - Group {group["group_id"]}')
        pdf.setFont('Helvetica', 11)
        pdf.drawString(50, 740, f'Generated by: {current_user.name}')
        pdf.drawString(50, 725, f'Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')

        y = 700
        pdf.setFont('Helvetica-Bold', 10)
        pdf.drawString(50, y, 'Name')
        pdf.drawString(220, y, 'Unique ID')
        pdf.drawString(340, y, 'Email')
        pdf.drawString(520, y, 'User ID')
        y -= 18
        pdf.setFont('Helvetica', 10)

        for member in members:
            if y < 80:
                pdf.showPage()
                y = 760
                pdf.setFont('Helvetica-Bold', 10)
                pdf.drawString(50, y, 'Name')
                pdf.drawString(220, y, 'Unique ID')
                pdf.drawString(340, y, 'Email')
                pdf.drawString(520, y, 'User ID')
                y -= 18
                pdf.setFont('Helvetica', 10)

            pdf.drawString(50, y, member['name'])
            pdf.drawString(220, y, member['unique_id'])
            pdf.drawString(340, y, member['email'])
            pdf.drawString(520, y, str(member['user_id']))
            y -= 16

        pdf.save()
        output.seek(0)
        return send_file(output, as_attachment=True, download_name=f'group_{group["group_id"]}_members.pdf', mimetype='application/pdf')
    finally:
        db_cursor.close()
        db_conn.close()

@app.route('/member_dashboard')
@login_required
def member_dashboard():
    if current_user.role != 'member':
        return redirect(url_for('leader_dashboard'))

    db_conn, db_cursor = get_db()
    try:
        db_cursor.execute('SELECT gm.group_id FROM group_members gm WHERE gm.user_id = %s', (current_user.id,))
        group = db_cursor.fetchone()

        payment_chart = [0] * 12
        progress = 0
        loan_schedule = []
        amount_due = None
        next_due_date = None
        current_month_paid = False
        loan_info = None
        paid_installments = 0
        unpaid_installments = 12
        total_paid_amount = Decimal('0.00')
        last_payment_date = None

        if group:
            group_id = group['group_id']
            db_cursor.execute('SELECT * FROM loans WHERE group_id = %s', (group_id,))
            loan = db_cursor.fetchone()
            if loan:
                loan_info = loan
                total_repayment = loan['amount'] * Decimal('1.07')
                monthly_payment = total_repayment / Decimal('12')
                member_share = (monthly_payment / Decimal('7')).quantize(Decimal('0.01'))

                start_date = loan['start_date']
                if start_date:
                    for idx in range(12):
                        schedule_month = (start_date.month - 1 + idx) % 12 + 1
                        schedule_year = start_date.year + (start_date.month - 1 + idx) // 12
                        db_cursor.execute(
                            'SELECT status, amount, paid_on FROM payments WHERE user_id = %s AND loan_id = %s AND month = %s AND year = %s',
                            (current_user.id, loan['loan_id'], schedule_month, schedule_year)
                        )
                        payment = db_cursor.fetchone()
                        status = payment['status'] if payment else 'pending'
                        if status == 'paid':
                            payment_chart[schedule_month - 1] = float(payment['amount'])
                            paid_installments += 1
                            unpaid_installments = max(12 - paid_installments, 0)
                            total_paid_amount += Decimal(str(payment['amount']))
                            if payment['paid_on']:
                                if last_payment_date is None or payment['paid_on'] > last_payment_date:
                                    last_payment_date = payment['paid_on']

                        due_label = datetime(schedule_year, schedule_month, 1).strftime('%b %Y')
                        loan_schedule.append({
                            'month': due_label,
                            'due_amount': member_share,
                            'status': status.title(),
                            'is_current': False
                        })

                    months_passed = (datetime.now().year - start_date.year) * 12 + (datetime.now().month - start_date.month) + 1
                    if months_passed < 1:
                        months_passed = 1
                    if months_passed > 12:
                        months_passed = 12

                    loan_schedule[months_passed - 1]['is_current'] = True
                    current_month_paid = loan_schedule[months_passed - 1]['status'].lower() == 'paid'
                    if not current_month_paid:
                        amount_due = loan_schedule[months_passed - 1]['due_amount']
                        next_due_date = loan_schedule[months_passed - 1]['month']

                    db_cursor.execute('SELECT COUNT(*) as paid_count FROM payments WHERE group_id = %s AND loan_id = %s AND status = %s',
                                      (group_id, loan['loan_id'], 'paid'))
                    group_paid_count = db_cursor.fetchone()['paid_count']
                    progress = int((group_paid_count / (7 * 12)) * 100)

        return render_template(
            'member_dashboard.html',
            name=current_user.name,
            payment_chart=payment_chart,
            payment_chart_json=json.dumps(payment_chart),
            progress=progress,
            role=current_user.role,
            user_name=current_user.name,
            loan_schedule=loan_schedule,
            amount_due=amount_due,
            next_due_date=next_due_date,
            current_month_paid=current_month_paid,
            loan_info=loan_info,
            paid_installments=paid_installments,
            unpaid_installments=unpaid_installments,
            total_paid_amount=total_paid_amount,
            last_payment_date=last_payment_date
        )
    finally:
        db_cursor.close()
        db_conn.close()

@app.route('/apply_loan', methods=['GET', 'POST'])
@login_required
def apply_loan():
    if current_user.role != 'leader':
        return redirect(url_for('member_dashboard'))

    db_conn, db_cursor = get_db()
    try:
        # Check if leader has a group
        db_cursor.execute('SELECT * FROM `groups` WHERE leader_id = %s', (current_user.id,))
        group = db_cursor.fetchone()
        if not group:
            flash('You must create a group first.', 'danger')
            return redirect(url_for('leader_dashboard'))
        group_id = group['group_id']

        # Check if group has 7 members
        db_cursor.execute('SELECT COUNT(*) as cnt FROM group_members WHERE group_id = %s', (group_id,))
        count = db_cursor.fetchone()['cnt']
        if count != 7:
            flash('Your group must have 7 members (including you) to apply for a loan.', 'danger')
            return redirect(url_for('leader_dashboard'))

        # Check if loan already exists
        db_cursor.execute('SELECT * FROM loans WHERE group_id = %s', (group_id,))
        loan = db_cursor.fetchone()
        if loan:
            flash('Loan already applied for this group.', 'info')
            return redirect(url_for('leader_dashboard'))

        # Check if leader has verified their identity
        db_cursor.execute('SELECT * FROM identity_verification WHERE user_id = %s', (current_user.id,))
        leader_verification = db_cursor.fetchone()
        if not leader_verification:
            flash('You must verify your identity in your profile before applying for a loan.', 'danger')
            return redirect(url_for('leader_dashboard'))

        if request.method == 'POST':
            # Get form data
            try:
                amount = float(request.form['amount'])
            except (ValueError, TypeError):
                flash('Please enter a valid loan amount.', 'danger')
                return render_template('apply_loan.html', role=current_user.role, user_name=current_user.name)

            # Validate loan amount
            if amount < 500000 or amount > 700000:
                flash('Loan amount must be between ₹5,00,000 and ₹7,00,000.', 'danger')
                return render_template('apply_loan.html', role=current_user.role, user_name=current_user.name)

            try:
                # Create loan application
                db_cursor.execute(
                    'INSERT INTO loans (group_id, amount, start_date, status) VALUES (%s, %s, CURDATE(), %s)',
                    (group_id, amount, 'approved')
                )
                db_conn.commit()
                flash('Loan application successful!', 'success')
                return redirect(url_for('leader_dashboard'))

            except mysql.connector.Error:
                db_conn.rollback()
                flash('An error occurred while processing your application. Please try again.', 'danger')
                return render_template('apply_loan.html', role=current_user.role, user_name=current_user.name)

        return render_template('apply_loan.html', role=current_user.role, user_name=current_user.name)
    finally:
        db_cursor.close()
        db_conn.close()

@app.route('/make_payment', methods=['GET', 'POST'])
@login_required
def make_payment():
    if current_user.role not in ['leader', 'member']:
        return redirect(url_for('home'))

    db_conn, db_cursor = get_db()
    try:
        # Find group and loan
        db_cursor.execute('SELECT gm.group_id FROM group_members gm WHERE gm.user_id = %s', (current_user.id,))
        group = db_cursor.fetchone()
        if not group:
            flash('You are not part of any group.', 'danger')
            return redirect(url_for('member_dashboard'))
        group_id = group['group_id']

        db_cursor.execute('SELECT * FROM loans WHERE group_id = %s', (group_id,))
        loan = db_cursor.fetchone()
        if not loan:
            flash('No loan found for your group.', 'danger')
            return redirect(url_for('member_dashboard'))

        # Equal repayment share across 7 members for 12 months
        total_repayment = loan['amount'] * Decimal('1.07')
        monthly_payment = total_repayment / Decimal('12')
        member_share = (monthly_payment / Decimal('7')).quantize(Decimal('0.01'))

        start_date = loan['start_date']
        today = datetime.now()
        months_passed = (today.year - start_date.year) * 12 + (today.month - start_date.month) + 1
        if months_passed > 12:
            flash('Loan term completed.', 'info')
            return redirect(url_for('member_dashboard'))

        schedule_month = today.month
        schedule_year = today.year

        # Check if already paid for this payment cycle
        db_cursor.execute(
            'SELECT * FROM payments WHERE user_id = %s AND loan_id = %s AND month = %s AND year = %s',
            (current_user.id, loan['loan_id'], schedule_month, schedule_year)
        )
        payment = db_cursor.fetchone()

        payment_methods = ['PhonePe', 'GPay', 'Paytm', 'Amazon Pay', 'BHIM', 'UPI', 'Debit Card', 'Credit Card']
        if request.method == 'POST':
            selected_method = request.form.get('payment_method')
            if not selected_method or selected_method not in payment_methods:
                flash('Please select a valid payment method.', 'danger')
            elif payment and payment['status'] == 'paid':
                flash('You have already paid for this month.', 'info')
            else:
                db_cursor.execute(
                    'INSERT INTO payments (user_id, group_id, loan_id, month, year, amount, paid_on, status) VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s) ON DUPLICATE KEY UPDATE amount=%s, status=%s, paid_on=NOW()',
                    (current_user.id, group_id, loan['loan_id'], schedule_month, schedule_year, member_share, 'paid', member_share, 'paid')
                )
                db_conn.commit()
                flash(f'Payment successful via {selected_method}!', 'success')
            return redirect(url_for('make_payment'))

        paid = payment['status'] == 'paid' if payment else False
        return render_template(
            'make_payment.html',
            member_share=member_share,
            month=months_passed,
            paid=paid,
            payment_methods=payment_methods,
            role=current_user.role,
            user_name=current_user.name
        )
    finally:
        db_cursor.close()
        db_conn.close()

@app.route('/receipt/<int:payment_id>')
@login_required
def receipt(payment_id):
    db_conn, db_cursor = get_db()
    try:
        db_cursor.execute('''
            SELECT p.*, u.name as user_name, u.email as user_email, u.unique_id as user_unique_id, l.amount as loan_amount, l.group_id
            FROM payments p
            JOIN users u ON p.user_id = u.user_id
            JOIN loans l ON p.loan_id = l.loan_id
            WHERE p.payment_id = %s
        ''', (payment_id,))
        payment = db_cursor.fetchone()
        if not payment:
            flash('Receipt not found.', 'danger')
            return redirect(url_for('payment_history'))
        if payment['user_id'] != current_user.id and not is_system_administrator():
            flash('You do not have permission to download this receipt.', 'danger')
            return redirect(url_for('payment_history'))

        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=letter)
        pdf.setTitle(f'Receipt_{payment_id}')

        pdf.setFont('Helvetica-Bold', 18)
        pdf.drawString(50, 750, 'DWCRA Payment Receipt')

        pdf.setFont('Helvetica', 11)
        pdf.drawString(50, 725, f'Receipt ID: {payment_id}')
        pdf.drawString(50, 710, f'Date: {datetime.now().strftime("%Y-%m-%d")}')
        pdf.drawString(50, 695, f'Payer: {payment["user_name"]} ({payment["user_unique_id"]})')
        pdf.drawString(50, 680, f'Email: {payment["user_email"]}')
        pdf.drawString(50, 665, f'Loan ID: {payment["loan_id"]}')
        pdf.drawString(50, 650, f'Group ID: {payment["group_id"]}')
        pdf.drawString(50, 635, f'Payment Month: {payment["month"]}/{payment["year"]}')
        pdf.drawString(50, 620, f'Amount Paid: ₹{payment["amount"]}')
        pdf.drawString(50, 605, f'Payment Status: {payment["status"].title()}')

        pdf.setFont('Helvetica-Bold', 12)
        pdf.drawString(50, 575, 'Loan Summary')
        pdf.setFont('Helvetica', 11)
        pdf.drawString(50, 560, f'Loan Amount: ₹{payment["loan_amount"]}')
        pdf.drawString(50, 545, f'Paid On: {payment["paid_on"].strftime("%Y-%m-%d %H:%M:%S") if payment["paid_on"] else "N/A"}')

        pdf.showPage()
        pdf.save()
        buffer.seek(0)

        return send_file(buffer, as_attachment=True, download_name=f'receipt_{payment_id}.pdf', mimetype='application/pdf')
    finally:
        db_cursor.close()
        db_conn.close()

@app.route('/payment_history')
@login_required
def payment_history():
    if current_user.role not in ['leader', 'member']:
        return redirect(url_for('home'))
    db_conn, db_cursor = get_db()
    try:
        db_cursor.execute('SELECT * FROM payments WHERE user_id = %s ORDER BY year, month', (current_user.id,))
        payments = db_cursor.fetchall()
        return render_template('payment_history.html', payments=payments, role=current_user.role, user_name=current_user.name)
    finally:
        db_cursor.close()
        db_conn.close()

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if not is_system_administrator():
        flash('Access denied. Only system administrator can access admin features.', 'danger')
        return redirect(url_for('home'))
    
    # Get analytics data
    cursor.execute('SELECT COUNT(*) as total FROM users WHERE is_active = TRUE')
    total_users = cursor.fetchone()['total']
    
    cursor.execute('SELECT COUNT(*) as total FROM `groups`')
    total_groups = cursor.fetchone()['total']
    
    cursor.execute('SELECT COUNT(*) as total FROM loans')
    total_loans = cursor.fetchone()['total']
    
    cursor.execute('SELECT COUNT(*) as total FROM loans WHERE status = "pending"')
    pending_applications = cursor.fetchone()['total']
    
    analytics = {
        'total_users': total_users,
        'total_groups': total_groups,
        'total_loans': total_loans,
        'pending_applications': pending_applications
    }
    
    # Get loan trends data (last 6 months)
    cursor.execute('''
        SELECT DATE_FORMAT(created_at, '%Y-%m') as month, 
               SUM(amount) as total_amount 
        FROM loans 
        WHERE created_at >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
        GROUP BY DATE_FORMAT(created_at, '%Y-%m')
        ORDER BY month
    ''')
    loan_trends = cursor.fetchall()
    
    loan_trends_labels = [item['month'] for item in loan_trends]
    loan_trends_data = [float(item['total_amount']) for item in loan_trends]
    
    # Get repayment data
    cursor.execute('''
        SELECT 
            SUM(CASE WHEN status = 'paid' THEN 1 ELSE 0 END) as paid_count,
            SUM(CASE WHEN status = 'unpaid' THEN 1 ELSE 0 END) as unpaid_count,
            SUM(CASE WHEN status = 'unpaid' AND CONCAT(year, '-', LPAD(month, 2, '0'), '-01') < CURDATE() THEN 1 ELSE 0 END) as overdue_count
        FROM payments
    ''')
    repayment_stats = cursor.fetchone()
    
    repayment_data = [
        repayment_stats['paid_count'] or 0,
        repayment_stats['unpaid_count'] or 0,
        repayment_stats['overdue_count'] or 0
    ]
    
    # Get recent activities (last 10)
    cursor.execute('''
        SELECT al.*, u.name as user_name 
        FROM audit_logs al 
        JOIN users u ON al.admin_id = u.user_id 
        ORDER BY al.created_at DESC 
        LIMIT 10
    ''')
    recent_activities = cursor.fetchall()
    
    # Get recent notifications (last 5)
    cursor.execute('''
        SELECT * FROM notifications 
        ORDER BY created_at DESC 
        LIMIT 5
    ''')
    recent_notifications = cursor.fetchall()
    
    # Get pending loans
    cursor.execute('''
        SELECT l.*, g.group_id, u.name as leader_name, 
               CONCAT('Group ', g.group_id, ' - ', u.name) as group_name
        FROM loans l 
        JOIN `groups` g ON l.group_id = g.group_id 
        JOIN users u ON g.leader_id = u.user_id 
        WHERE l.status = 'pending'
        ORDER BY l.created_at DESC
    ''')
    pending_loans = cursor.fetchall()
    
    # Get pending verifications
    cursor.execute('''
        SELECT iv.*, u.name as user_name 
        FROM identity_verification iv 
        JOIN users u ON iv.user_id = u.user_id 
        WHERE iv.verification_status = 'pending'
        ORDER BY iv.verified_at DESC
    ''')
    pending_verifications = cursor.fetchall()
    
    return render_template('admin_dashboard.html', 
                         analytics=analytics,
                         loan_trends_labels=loan_trends_labels,
                         loan_trends_data=loan_trends_data,
                         repayment_data=repayment_data,
                         recent_activities=recent_activities,
                         recent_notifications=recent_notifications,
                         pending_loans=pending_loans,
                         pending_verifications=pending_verifications,
                         role=current_user.role, 
                         user_name=current_user.name)

@app.route('/admin/approve_loan/<int:loan_id>')
@login_required
def approve_loan(loan_id):
    if not is_system_administrator():
        flash('Access denied. Only system administrator can access admin features.', 'danger')
        return redirect(url_for('home'))
    
    try:
        cursor.execute('UPDATE loans SET status = %s WHERE loan_id = %s', ('approved', loan_id))
        conn.commit()
        
        # Log admin action
        cursor.execute('''
            INSERT INTO audit_logs (admin_id, action_type, action_description, target_table, target_id, ip_address)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (current_user.id, 'APPROVE_LOAN', f'Approved loan ID: {loan_id}', 'loans', loan_id, request.remote_addr))
        conn.commit()
        
        flash('Loan approved successfully!', 'success')
    except mysql.connector.Error as e:
        flash('Loan approval failed.', 'danger')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/reject_loan/<int:loan_id>')
@login_required
def reject_loan(loan_id):
    if not is_system_administrator():
        flash('Access denied. Only system administrator can access admin features.', 'danger')
        return redirect(url_for('home'))
    
    try:
        cursor.execute('UPDATE loans SET status = %s WHERE loan_id = %s', ('rejected', loan_id))
        conn.commit()
        
        # Log admin action
        cursor.execute('''
            INSERT INTO audit_logs (admin_id, action_type, action_description, target_table, target_id, ip_address)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (current_user.id, 'REJECT_LOAN', f'Rejected loan ID: {loan_id}', 'loans', loan_id, request.remote_addr))
        conn.commit()
        
        flash('Loan rejected successfully!', 'warning')
    except mysql.connector.Error as e:
        flash('Loan rejection failed.', 'danger')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/identity_verifications')
@login_required
def admin_identity_verifications():
    if not is_system_administrator():
        flash('Access denied. Only system administrator can access admin features.', 'danger')
        return redirect(url_for('home'))
    db_conn, db_cursor = get_db()
    try:
        db_cursor.execute('''
            SELECT iv.*, u.name as user_name, u.unique_id, u.email, u.role 
            FROM identity_verification iv 
            JOIN users u ON iv.user_id = u.user_id 
            ORDER BY iv.verified_at DESC
        ''')
        verifications = db_cursor.fetchall()
        return render_template('admin_identity_verifications.html', verifications=verifications, role=current_user.role, user_name=current_user.name)
    finally:
        db_cursor.close()
        db_conn.close()

@app.route('/admin/reports/export/<format>')
@login_required
def admin_export_reports(format):
    if not is_system_administrator():
        flash('Access denied. Only system administrator can access admin features.', 'danger')
        return redirect(url_for('home'))

    db_conn, db_cursor = get_db()
    try:
        db_cursor.execute('''
            SELECT p.payment_id, p.user_id, u.unique_id as user_unique_id, u.name as user_name, p.group_id, p.loan_id,
                   p.month, p.year, p.amount, p.status, p.paid_on
            FROM payments p
            JOIN users u ON p.user_id = u.user_id
            ORDER BY p.year, p.month, p.user_id
        ''')
        payments = db_cursor.fetchall()

        if format == 'csv':
            output = BytesIO()
            writer = csv.writer(output)
            writer.writerow(['Payment ID', 'User ID', 'Unique ID', 'Name', 'Group ID', 'Loan ID', 'Month', 'Year', 'Amount', 'Status', 'Paid On'])
            for p in payments:
                writer.writerow([
                    p['payment_id'], p['user_id'], p['user_unique_id'], p['user_name'],
                    p['group_id'], p['loan_id'], p['month'], p['year'], p['amount'],
                    p['status'], p['paid_on'].strftime('%Y-%m-%d %H:%M:%S') if p['paid_on'] else ''
                ])
            output.seek(0)
            return send_file(output, as_attachment=True, download_name='dwcra_payments_report.csv', mimetype='text/csv')

        if format == 'pdf':
            output = BytesIO()
            pdf = canvas.Canvas(output, pagesize=letter)
            pdf.setTitle('DWCRA Payments Report')
            pdf.setFont('Helvetica-Bold', 14)
            pdf.drawString(50, 750, 'DWCRA Payments Report')
            pdf.setFont('Helvetica', 10)
            y = 725
            pdf.drawString(50, y, 'Export Date: ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            y -= 20
            pdf.setFont('Helvetica-Bold', 10)
            headers = ['Payment ID', 'User', 'Loan', 'Month/Year', 'Amount', 'Status']
            x_positions = [50, 100, 190, 270, 360, 430]
            for i, header in enumerate(headers):
                pdf.drawString(x_positions[i], y, header)
            y -= 16
            pdf.setFont('Helvetica', 9)

            for p in payments:
                if y < 80:
                    pdf.showPage()
                    y = 750
                    pdf.setFont('Helvetica-Bold', 10)
                    for i, header in enumerate(headers):
                        pdf.drawString(x_positions[i], y, header)
                    y -= 16
                    pdf.setFont('Helvetica', 9)
                pdf.drawString(x_positions[0], y, str(p['payment_id']))
                pdf.drawString(x_positions[1], y, str(p['user_name']))
                pdf.drawString(x_positions[2], y, str(p['loan_id']))
                pdf.drawString(x_positions[3], y, f"{p['month']}/{p['year']}")
                pdf.drawString(x_positions[4], y, str(p['amount']))
                pdf.drawString(x_positions[5], y, str(p['status']).title())
                y -= 14

            pdf.save()
            output.seek(0)
            return send_file(output, as_attachment=True, download_name='dwcra_payments_report.pdf', mimetype='application/pdf')

        flash('Unsupported export format.', 'danger')
        return redirect(url_for('admin_dashboard'))
    finally:
        db_cursor.close()
        db_conn.close()

@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if request.method == 'POST':
        email = request.form['email']
        db_conn, db_cursor = get_db()
        db_cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        user = db_cursor.fetchone()
        db_cursor.close()
        db_conn.close()
        if user:
            token = serializer.dumps(email, salt='reset-password')
            reset_url = url_for('reset_password', token=token, _external=True)
            try:
                send_email(email, 'DWCRA Password Reset', f'Click the link to reset your password: {reset_url}')
                flash('Password reset link sent to your email.', 'info')
            except Exception:
                flash('Failed to send email. Please contact admin.', 'danger')
        else:
            flash('If the email is registered, a reset link will be sent.', 'info')
    return render_template('reset_password_request.html', user_name=None)

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = serializer.loads(token, salt='reset-password', max_age=3600)
    except (SignatureExpired, BadSignature):
        flash('The reset link is invalid or has expired.', 'danger')
        return redirect(url_for('reset_password_request'))
    if request.method == 'POST':
        password = request.form['password']
        password_hash = generate_password_hash(password)
        db_conn, db_cursor = get_db()
        db_cursor.execute('UPDATE users SET password_hash = %s WHERE email = %s', (password_hash, email))
        db_conn.commit()
        db_cursor.close()
        db_conn.close()
        flash('Password reset successful! Please log in.', 'success')
        return redirect(url_for('home'))
    return render_template('reset_password.html', token=token, user_name=None)

@app.route('/home')
@login_required
def home_page():
    if is_system_administrator():
        # Get analytics data
        cursor.execute('SELECT COUNT(*) as total FROM users WHERE is_active = TRUE')
        total_users = cursor.fetchone()['total']
        cursor.execute('SELECT COUNT(*) as total FROM `groups`')
        total_groups = cursor.fetchone()['total']
        cursor.execute('SELECT COUNT(*) as total FROM loans')
        total_loans = cursor.fetchone()['total']
        cursor.execute('SELECT COUNT(*) as total FROM loans WHERE status = "pending"')
        pending_applications = cursor.fetchone()['total']
        analytics = {
            'total_users': total_users,
            'total_groups': total_groups,
            'total_loans': total_loans,
            'pending_applications': pending_applications
        }
        cursor.execute('''
            SELECT DATE_FORMAT(created_at, '%Y-%m') as month, 
                   SUM(amount) as total_amount 
            FROM loans 
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
            GROUP BY DATE_FORMAT(created_at, '%Y-%m')
            ORDER BY month
        ''')
        loan_trends = cursor.fetchall()
        loan_trends_labels = [item['month'] for item in loan_trends]
        loan_trends_data = [float(item['total_amount']) for item in loan_trends]
        cursor.execute('''
            SELECT 
                SUM(CASE WHEN status = 'paid' THEN 1 ELSE 0 END) as paid_count,
                SUM(CASE WHEN status = 'unpaid' THEN 1 ELSE 0 END) as unpaid_count,
                SUM(CASE WHEN status = 'unpaid' AND CONCAT(year, '-', LPAD(month, 2, '0'), '-01') < CURDATE() THEN 1 ELSE 0 END) as overdue_count
            FROM payments
        ''')
        repayment_stats = cursor.fetchone()
        repayment_data = [
            repayment_stats['paid_count'] or 0,
            repayment_stats['unpaid_count'] or 0,
            repayment_stats['overdue_count'] or 0
        ]
        cursor.execute('''
            SELECT al.*, u.name as user_name 
            FROM audit_logs al 
            JOIN users u ON al.admin_id = u.user_id 
            ORDER BY al.created_at DESC 
            LIMIT 10
        ''')
        recent_activities = cursor.fetchall()
        cursor.execute('''
            SELECT * FROM notifications 
            ORDER BY created_at DESC 
            LIMIT 5
        ''')
        recent_notifications = cursor.fetchall()
        cursor.execute('''
            SELECT l.*, g.group_id, u.name as leader_name, 
                   CONCAT('Group ', g.group_id, ' - ', u.name) as group_name
            FROM loans l 
            JOIN `groups` g ON l.group_id = g.group_id 
            JOIN users u ON g.leader_id = u.user_id 
            WHERE l.status = 'pending'
            ORDER BY l.created_at DESC
        ''')
        pending_loans = cursor.fetchall()
        cursor.execute('''
            SELECT iv.*, u.name as user_name 
            FROM identity_verification iv 
            JOIN users u ON iv.user_id = u.user_id 
            WHERE iv.verification_status = 'pending'
            ORDER BY iv.verified_at DESC
        ''')
        pending_verifications = cursor.fetchall()
        return render_template('admin_dashboard.html', 
                             analytics=analytics,
                             loan_trends_labels=loan_trends_labels,
                             loan_trends_data=loan_trends_data,
                             repayment_data=repayment_data,
                             recent_activities=recent_activities,
                             recent_notifications=recent_notifications,
                             pending_loans=pending_loans,
                             pending_verifications=pending_verifications,
                             role=current_user.role, 
                             user_name=current_user.name)
    else:
        return render_template(
            'home.html',
            name=current_user.name,
            role=current_user.role,
            user_name=current_user.name
        )

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    db_conn, db_cursor = get_db()
    try:
        if request.method == 'POST':
            # Check form type first
            form_type = request.form.get('form_type')
            
            if form_type == 'identity_verification':
                # Handle identity verification
                id_type = request.form.get('id_type')
                id_number = request.form.get('id_number', '').strip()
                
                if not id_type or not id_number:
                    flash('Please select ID type and enter ID number.', 'danger')
                    return redirect(url_for('profile'))
                
                # Validate ID format
                if id_type == 'aadhaar':
                    # Remove spaces from Aadhaar number for validation
                    id_number = id_number.replace(' ', '')
                    if not re.match(r'^\d{12}$', id_number):
                        flash('Invalid Aadhaar number format. Must be exactly 12 digits.', 'danger')
                        return redirect(url_for('profile'))
                elif id_type == 'pan':
                    if not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', id_number.upper()):
                        flash('Invalid PAN format. Must be in format: ABCDE1234F (5 letters, 4 numbers, 1 letter).', 'danger')
                        return redirect(url_for('profile'))
                    id_number = id_number.upper()  # Store PAN in uppercase
                else:
                    flash('Invalid ID type selected.', 'danger')
                    return redirect(url_for('profile'))
                
                try:
                    # Check if user already has a verification
                    db_cursor.execute('SELECT * FROM identity_verification WHERE user_id = %s', (current_user.id,))
                    existing_verification = db_cursor.fetchone()
                    
                    if existing_verification:
                        # Update existing verification
                        db_cursor.execute(
                            'UPDATE identity_verification SET id_type = %s, id_number = %s, verified_at = NOW() WHERE user_id = %s',
                            (id_type, id_number, current_user.id)
                        )
                    else:
                        # Create new verification
                        db_cursor.execute(
                            'INSERT INTO identity_verification (user_id, id_type, id_number) VALUES (%s, %s, %s)',
                            (current_user.id, id_type, id_number)
                        )
                    
                    db_conn.commit()
                    
                    # Small delay to show loading state (optional - for better UX)
                    time.sleep(1.5)
                    
                    flash('Identity verification completed successfully!', 'success')
                    return redirect(url_for('profile'))
                except mysql.connector.Error:
                    db_conn.rollback()
                    flash('An error occurred while verifying your identity. Please try again.', 'danger')
                    return redirect(url_for('profile'))
            
            elif form_type == 'profile_update' and 'name' in request.form and 'email' in request.form and 'bank_name' in request.form:
                # Handle profile update
                name = request.form['name']
                email = request.form['email']
                bank_name = request.form['bank_name']
                password = request.form.get('password')
                
                # Check if email is changing and not already taken
                if email != current_user.email:
                    db_cursor.execute('SELECT * FROM users WHERE email = %s AND user_id != %s', (email, current_user.id))
                    if db_cursor.fetchone():
                        flash('Email already in use.', 'danger')
                        return render_template('profile.html', name=name, email=email, bank_name=bank_name, role=current_user.role, user_name=current_user.name)
                
                if password:
                    password_hash = generate_password_hash(password)
                    db_cursor.execute(
                        'UPDATE users SET name = %s, email = %s, bank_name = %s, password_hash = %s WHERE user_id = %s',
                        (name, email, bank_name, password_hash, current_user.id)
                    )
                else:
                    db_cursor.execute(
                        'UPDATE users SET name = %s, email = %s, bank_name = %s WHERE user_id = %s',
                        (name, email, bank_name, current_user.id)
                    )
                db_conn.commit()
                flash('Profile updated successfully.', 'success')
                return redirect(url_for('profile'))
            
            else:
                # Neither identity verification nor profile update - invalid request
                flash('Invalid form submission. Please try again.', 'danger')
                return redirect(url_for('profile'))
        
        # GET request - display profile
        db_cursor.execute('SELECT * FROM users WHERE user_id = %s', (current_user.id,))
        user = db_cursor.fetchone()
        
        if not user:
            flash('User profile not found. Please log in again.', 'danger')
            return redirect(url_for('logout'))
        
        # Get verification status
        db_cursor.execute('SELECT * FROM identity_verification WHERE user_id = %s ORDER BY verified_at DESC LIMIT 1', (current_user.id,))
        verification_status = db_cursor.fetchone()
        
        return render_template('profile.html', 
                             name=user['name'], 
                             email=user['email'], 
                             bank_name=user['bank_name'], 
                             role=user['role'], 
                             user_name=user['name'],
                             verification_status=verification_status)
    finally:
        db_cursor.close()
        db_conn.close()

def send_email(to, subject, body):
    msg = Message(subject, recipients=[to], body=body, sender=app.config['MAIL_USERNAME'])
    mail.send(msg)

def is_user_verified(user_id):
    """Check if a user has verified their identity"""
    cursor.execute('SELECT * FROM identity_verification WHERE user_id = %s', (user_id,))
    return cursor.fetchone() is not None

# User Management Routes
@app.route('/admin/users')
@login_required
def admin_users():
    if not is_system_administrator():
        flash('Access denied. Only system administrator can access admin features.', 'danger')
        return redirect(url_for('home'))
    
    cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
    users = cursor.fetchall()
    return render_template('admin_users.html', users=users, role=current_user.role, user_name=current_user.name)

@app.route('/admin/users/create', methods=['GET', 'POST'])
@login_required
def admin_create_user():
    if not is_system_administrator():
        flash('Access denied. Only system administrator can access admin features.', 'danger')
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        unique_id = request.form.get('unique_id')
        name = request.form.get('name')
        email = request.form.get('email')
        bank_name = request.form.get('bank_name')
        password = request.form.get('password')
        role = request.form.get('role')
        
        if not all([unique_id, name, email, bank_name, password, role]):
            flash('All fields are required.', 'danger')
            return redirect(url_for('admin_create_user'))
        
        if role not in ['leader', 'member']:
            flash('Invalid role selected. Admin role is not allowed.', 'danger')
            return redirect(url_for('admin_create_user'))
        
        password_hash = generate_password_hash(password)
        
        try:
            db_conn, db_cursor = get_db()
            db_cursor.execute('''
                INSERT INTO users (unique_id, name, email, password_hash, role, bank_name) 
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (unique_id, name, email, password_hash, role, bank_name))
            db_conn.commit()
            last_id = db_cursor.lastrowid
            
            # Log admin action
            db_cursor.execute('''
                INSERT INTO audit_logs (admin_id, action_type, action_description, target_table, target_id, ip_address)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (current_user.id, 'CREATE_USER', f'Created user: {name}', 'users', last_id, request.remote_addr))
            db_conn.commit()
            db_cursor.close()
            db_conn.close()
            
            flash('User created successfully!', 'success')
            return redirect(url_for('admin_users'))
        except mysql.connector.Error as e:
            flash('User creation failed. Unique ID or email may already exist.', 'danger')
    
    return render_template('admin_create_user.html', role=current_user.role, user_name=current_user.name)

@app.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_user(user_id):
    if not is_system_administrator():
        flash('Access denied. Only system administrator can access admin features.', 'danger')
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        bank_name = request.form.get('bank_name')
        role = request.form.get('role')
        is_active = request.form.get('is_active') == 'on'
        
        if not all([name, email, bank_name, role]):
            flash('All fields are required.', 'danger')
            return redirect(url_for('admin_edit_user', user_id=user_id))
        
        if role not in ['leader', 'member']:
            flash('Invalid role selected. Admin role is not allowed.', 'danger')
            return redirect(url_for('admin_edit_user', user_id=user_id))
        
        try:
            cursor.execute('''
                UPDATE users SET name = %s, email = %s, bank_name = %s, role = %s, is_active = %s 
                WHERE user_id = %s
            ''', (name, email, bank_name, role, is_active, user_id))
            conn.commit()
            
            # Log admin action
            cursor.execute('''
                INSERT INTO audit_logs (admin_id, action_type, action_description, target_table, target_id, ip_address)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (current_user.id, 'UPDATE_USER', f'Updated user: {name}', 'users', user_id, request.remote_addr))
            conn.commit()
            
            flash('User updated successfully!', 'success')
            return redirect(url_for('admin_users'))
        except mysql.connector.Error as e:
            flash('User update failed.', 'danger')
    
    cursor.execute('SELECT * FROM users WHERE user_id = %s', (user_id,))
    user = cursor.fetchone()
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('admin_users'))
    
    return render_template('admin_edit_user.html', user=user, role=current_user.role, user_name=current_user.name)

@app.route('/admin/users/delete/<int:user_id>')
@login_required
def admin_delete_user(user_id):
    if not is_system_administrator():
        flash('Access denied. Only system administrator can access admin features.', 'danger')
        return redirect(url_for('home'))
    
    try:
        cursor.execute('SELECT name FROM users WHERE user_id = %s', (user_id,))
        user = cursor.fetchone()
        if not user:
            flash('User not found.', 'danger')
            return redirect(url_for('admin_users'))
        
        cursor.execute('DELETE FROM users WHERE user_id = %s', (user_id,))
        conn.commit()
        
        # Log admin action
        cursor.execute('''
            INSERT INTO audit_logs (admin_id, action_type, action_description, target_table, target_id, ip_address)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (current_user.id, 'DELETE_USER', f'Deleted user: {user["name"]}', 'users', user_id, request.remote_addr))
        conn.commit()
        
        flash('User deleted successfully!', 'success')
    except mysql.connector.Error as e:
        flash('User deletion failed.', 'danger')
    
    return redirect(url_for('admin_users'))

@app.route('/admin/users/reset_password/<int:user_id>', methods=['POST'])
@login_required
def admin_reset_user_password(user_id):
    if not is_system_administrator():
        flash('Access denied. Only system administrator can access admin features.', 'danger')
        return redirect(url_for('home'))
    
    try:
        new_password = request.form.get('new_password')
        if not new_password:
            flash('New password is required.', 'danger')
            return redirect(url_for('admin_users'))
        
        password_hash = generate_password_hash(new_password)
        cursor.execute('UPDATE users SET password_hash = %s WHERE user_id = %s', (password_hash, user_id))
        conn.commit()
        
        # Log admin action
        cursor.execute('''
            INSERT INTO audit_logs (admin_id, action_type, action_description, target_table, target_id, ip_address)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (current_user.id, 'RESET_PASSWORD', f'Reset password for user ID: {user_id}', 'users', user_id, request.remote_addr))
        conn.commit()
        
        flash('Password reset successfully!', 'success')
    except mysql.connector.Error as e:
        flash('Password reset failed.', 'danger')
    
    return redirect(url_for('admin_users'))

# Group Management Routes
@app.route('/admin/groups')
@login_required
def admin_groups():
    if not is_system_administrator():
        flash('Access denied. Only system administrator can access admin features.', 'danger')
        return redirect(url_for('home'))
    
    cursor.execute('''
        SELECT g.*, u.name as leader_name, 
               COUNT(gm.user_id) as member_count
        FROM `groups` g 
        JOIN users u ON g.leader_id = u.user_id 
        LEFT JOIN group_members gm ON g.group_id = gm.group_id
        GROUP BY g.group_id
        ORDER BY g.created_at DESC
    ''')
    groups = cursor.fetchall()
    return render_template('admin_groups.html', groups=groups, role=current_user.role, user_name=current_user.name)

@app.route('/admin/groups/create', methods=['GET', 'POST'])
@login_required
def admin_create_group():
    if not is_system_administrator():
        flash('Access denied. Only system administrator can access admin features.', 'danger')
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        leader_id = request.form.get('leader_id')
        member_ids = request.form.getlist('member_ids')
        
        if not leader_id:
            flash('Leader is required.', 'danger')
            return redirect(url_for('admin_create_group'))
        
        try:
            # Create group
            cursor.execute('INSERT INTO `groups` (leader_id) VALUES (%s)', (leader_id,))
            conn.commit()
            group_id = cursor.lastrowid
            
            # Add leader to group
            cursor.execute('INSERT INTO group_members (group_id, user_id) VALUES (%s, %s)', (group_id, leader_id))
            
            # Add members to group
            for member_id in member_ids:
                if member_id:
                    cursor.execute('INSERT INTO group_members (group_id, user_id) VALUES (%s, %s)', (group_id, member_id))
            
            conn.commit()
            
            # Log admin action
            cursor.execute('''
                INSERT INTO audit_logs (admin_id, action_type, action_description, target_table, target_id, ip_address)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (current_user.id, 'CREATE_GROUP', f'Created group ID: {group_id}', 'groups', group_id, request.remote_addr))
            conn.commit()
            
            flash('Group created successfully!', 'success')
            return redirect(url_for('admin_groups'))
        except mysql.connector.Error as e:
            flash('Group creation failed.', 'danger')
    
    # Get available leaders and members
    cursor.execute('SELECT * FROM users WHERE role = "leader" AND is_active = TRUE')
    leaders = cursor.fetchall()
    
    cursor.execute('SELECT * FROM users WHERE role = "member" AND is_active = TRUE')
    members = cursor.fetchall()
    
    return render_template('admin_create_group.html', leaders=leaders, members=members, role=current_user.role, user_name=current_user.name)

# Loan Management Routes
@app.route('/admin/loans')
@login_required
def admin_loans():
    if not is_system_administrator():
        flash('Access denied. Only system administrator can access admin features.', 'danger')
        return redirect(url_for('home'))
    
    status_filter = request.args.get('status', 'all')
    
    if status_filter == 'all':
        cursor.execute('''
            SELECT l.*, g.group_id, u.name as leader_name
            FROM loans l 
            JOIN `groups` g ON l.group_id = g.group_id 
            JOIN users u ON g.leader_id = u.user_id 
            ORDER BY l.created_at DESC
        ''')
    else:
        cursor.execute('''
            SELECT l.*, g.group_id, u.name as leader_name
            FROM loans l 
            JOIN `groups` g ON l.group_id = g.group_id 
            JOIN users u ON g.leader_id = u.user_id 
            WHERE l.status = %s
            ORDER BY l.created_at DESC
        ''', (status_filter,))
    
    loans = cursor.fetchall()
    return render_template('admin_loans.html', loans=loans, status_filter=status_filter, role=current_user.role, user_name=current_user.name)

@app.route('/admin/loans/edit/<int:loan_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_loan(loan_id):
    if not is_system_administrator():
        flash('Access denied. Only system administrator can access admin features.', 'danger')
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        amount = request.form.get('amount')
        status = request.form.get('status')
        
        try:
            cursor.execute('UPDATE loans SET amount = %s, status = %s WHERE loan_id = %s', (amount, status, loan_id))
            conn.commit()
            
            # Log admin action
            cursor.execute('''
                INSERT INTO audit_logs (admin_id, action_type, action_description, target_table, target_id, ip_address)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (current_user.id, 'UPDATE_LOAN', f'Updated loan ID: {loan_id}', 'loans', loan_id, request.remote_addr))
            conn.commit()
            
            flash('Loan updated successfully!', 'success')
            return redirect(url_for('admin_loans'))
        except mysql.connector.Error as e:
            flash('Loan update failed.', 'danger')
    
    cursor.execute('SELECT * FROM loans WHERE loan_id = %s', (loan_id,))
    loan = cursor.fetchone()
    if not loan:
        flash('Loan not found.', 'danger')
        return redirect(url_for('admin_loans'))
    
    return render_template('admin_edit_loan.html', loan=loan, role=current_user.role, user_name=current_user.name)

@app.route('/admin/reports')
@login_required
def admin_reports():
    if not is_system_administrator():
        flash('Access denied. Only system administrator can access admin features.', 'danger')
        return redirect(url_for('home'))
    
    cursor.execute('SELECT * FROM audit_logs WHERE action_type LIKE "%REPORT%" ORDER BY created_at DESC LIMIT 10')
    recent_reports = cursor.fetchall()
    return render_template('admin_reports.html', recent_reports=recent_reports, role=current_user.role, user_name=current_user.name)

@app.route('/admin/reports/generate', methods=['GET', 'POST'])
@login_required
def admin_generate_report():
    if not is_system_administrator():
        flash('Access denied. Only system administrator can access admin features.', 'danger')
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        report_type = request.form.get('report_type')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        
        if not all([report_type, start_date, end_date]):
            flash('All fields are required.', 'danger')
            return redirect(url_for('admin_generate_report'))
        
        try:
            # Generate report based on type
            if report_type == 'user_activity':
                cursor.execute('''
                    SELECT al.*, u.name as user_name 
                    FROM audit_logs al 
                    JOIN users u ON al.admin_id = u.user_id 
                    WHERE al.created_at BETWEEN %s AND %s
                    ORDER BY al.created_at DESC
                ''', (start_date, end_date))
            elif report_type == 'loan_summary':
                cursor.execute('''
                    SELECT l.*, g.group_id, u.name as leader_name
                    FROM loans l 
                    JOIN `groups` g ON l.group_id = g.group_id 
                    JOIN users u ON g.leader_id = u.user_id 
                    WHERE l.created_at BETWEEN %s AND %s
                    ORDER BY l.created_at DESC
                ''', (start_date, end_date))
            elif report_type == 'payment_summary':
                cursor.execute('''
                    SELECT p.*, u.name as user_name, l.amount as loan_amount
                    FROM payments p 
                    JOIN users u ON p.user_id = u.user_id 
                    JOIN loans l ON p.loan_id = l.loan_id 
                    WHERE p.created_at BETWEEN %s AND %s
                    ORDER BY p.created_at DESC
                ''', (start_date, end_date))
            
            report_data = cursor.fetchall()
            
            # Log admin action
            cursor.execute('''
                INSERT INTO audit_logs (admin_id, action_type, action_description, target_table, target_id, ip_address)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (current_user.id, 'GENERATE_REPORT', f'Generated {report_type} report', 'reports', cursor.lastrowid, request.remote_addr))
            conn.commit()
            
            flash(f'{report_type.replace("_", " ").title()} report generated successfully!', 'success')
            return redirect(url_for('admin_reports'))
        except mysql.connector.Error as e:
            flash('Report generation failed.', 'danger')
    
    return render_template('admin_generate_report.html', role=current_user.role, user_name=current_user.name)

@app.route('/admin/notifications')
@login_required
def admin_notifications():
    if not is_system_administrator():
        flash('Access denied. Only system administrator can access admin features.', 'danger')
        return redirect(url_for('home'))
    
    cursor.execute('SELECT * FROM notifications ORDER BY created_at DESC')
    notifications = cursor.fetchall()
    return render_template('admin_notifications.html', notifications=notifications, role=current_user.role, user_name=current_user.name)

@app.route('/admin/notifications/send', methods=['GET', 'POST'])
@login_required
def admin_send_notification():
    if not is_system_administrator():
        flash('Access denied. Only system administrator can access admin features.', 'danger')
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        subject = request.form.get('subject')
        message = request.form.get('message')
        recipient_type = request.form.get('recipient_type')
        recipient_ids = request.form.getlist('recipient_ids')
        
        if not all([subject, message, recipient_type]):
            flash('All fields are required.', 'danger')
            return redirect(url_for('admin_send_notification'))
        
        try:
            if recipient_type == 'all':
                cursor.execute('SELECT user_id FROM users WHERE is_active = TRUE')
                recipients = cursor.fetchall()
                recipient_ids = [r['user_id'] for r in recipients]
            elif recipient_type == 'specific':
                if not recipient_ids:
                    flash('Please select at least one recipient.', 'danger')
                    return redirect(url_for('admin_send_notification'))
            
            # Send notifications to selected users
            for user_id in recipient_ids:
                cursor.execute('''
                    INSERT INTO notifications (user_id, subject, message, is_read)
                    VALUES (%s, %s, %s, FALSE)
                ''', (user_id, subject, message))
            
            conn.commit()
            
            # Log admin action
            cursor.execute('''
                INSERT INTO audit_logs (admin_id, action_type, action_description, target_table, target_id, ip_address)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (current_user.id, 'SEND_NOTIFICATION', f'Sent notification: {subject}', 'notifications', cursor.lastrowid, request.remote_addr))
            conn.commit()
            
            flash('Notification sent successfully!', 'success')
            return redirect(url_for('admin_notifications'))
        except mysql.connector.Error as e:
            flash('Notification sending failed.', 'danger')
    
    # Get users for recipient selection
    cursor.execute('SELECT * FROM users WHERE is_active = TRUE')
    users = cursor.fetchall()
    
    return render_template('admin_send_notification.html', users=users, role=current_user.role, user_name=current_user.name)

@app.route('/admin/audit-logs')
@login_required
def admin_audit_logs():
    if not is_system_administrator():
        flash('Access denied. Only system administrator can access admin features.', 'danger')
        return redirect(url_for('home'))
    
    cursor.execute('''
        SELECT al.*, u.name as admin_name 
        FROM audit_logs al 
        JOIN users u ON al.admin_id = u.user_id 
        ORDER BY al.created_at DESC
    ''')
    audit_logs = cursor.fetchall()
    return render_template('admin_audit_logs.html', audit_logs=audit_logs, role=current_user.role, user_name=current_user.name)

@app.route('/admin/settings')
@login_required
def admin_settings():
    if not is_system_administrator():
        flash('Access denied. Only system administrator can access admin features.', 'danger')
        return redirect(url_for('home'))
    
    cursor.execute('SELECT * FROM system_settings ORDER BY setting_key')
    settings = cursor.fetchall()
    return render_template('admin_settings.html', settings=settings, role=current_user.role, user_name=current_user.name)

if __name__ == '__main__':
    app.run(debug=True) 