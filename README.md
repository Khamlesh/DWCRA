# DWCRA Portal

DWCRA Portal is a simple, intuitive web application for managing community loan groups. It supports role-based access, group creation, loan applications, identity verification, and payment tracking.

## What this app does

This website helps a group leader and members manage a shared loan in a small community.

- Leaders can create a group with 6 verified members.
- Leaders can apply for a loan for the group once the group is complete.
- Members can see their payment schedule and pay their portion every month.
- Everyone has a profile area to update details and verify identity.

## Unique features

- **Role-based access**: separate areas for leaders, members, and admin.
- **Group loan workflow**: leader creates a group, applies for a loan, and members pay their equal share.
- **Identity verification**: users must verify Aadhaar or PAN before important actions.
- **Payment tracking**: every member can follow the payment history and current month status.
- **Simple navigation**: clear buttons for loan, payments, profile, and dashboard.
- **Localization support**: supports multiple languages through translation files.

## Step-by-step setup (for non-technical users)

### 1. Install Python

If you do not have Python installed, download it from the official site:
- https://www.python.org/downloads/

Make sure you choose a recent version and allow the installer to add Python to your system path.

### 2. Open the project folder

Open the folder `DWCRA 3` in your code editor or file manager.

### 3. Install required packages

Open a terminal or command prompt in the project folder and run:

```bash
pip install -r requirements.txt
```

This installs the pieces the app needs to run.

### 4. Set up the database

The app uses MySQL. Make sure MySQL is installed and running.

Then create a database named `dwcra` and run the SQL schema in `schema.sql`.

If you need to create the tables automatically, use the provided scripts or run the SQL commands directly in MySQL.

### 5. Configure database credentials

Open `app.py` and check the `DB_CONFIG` section:

```python
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Khamlesh@1234',
    'database': 'dwcra',
    'ssl_disabled': True
}
```

If your MySQL username or password is different, update those values.

### 6. Start the app

In the terminal, run:

```bash
python app.py
```

Then open your browser at:

```text
http://localhost:5000
```

### 7. Use the app

- Go to **Register** to create a new user.
- If you are a leader, verify your identity in the profile first.
- Create a group with 6 other verified members.
- After group creation, apply for a loan.
- Group members can then go to **Make Payment** and pay their share.

## Notes for non-technical users

- Use your **Unique ID** or **email** to log in.
- The leader must verify identity before creating a group or applying for a loan.
- Each member pays an equal share of the loan repayment.
- If something does not work, first check that all members are verified and the group has exactly 7 people.

## Helpful files

- `app.py` – main application logic
- `templates/` – web pages shown in the browser
- `schema.sql` – database structure
- `requirements.txt` – Python packages the app needs

## Deploying to GitHub

This repository has been prepared for GitHub. You can push changes with standard git commands.

---

### Contact

If you need help, ask someone familiar with Python and MySQL to assist with the database and server setup.
