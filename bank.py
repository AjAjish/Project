import json
from flask import Flask, render_template, request, redirect, url_for, flash, session
from datetime import datetime

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Needed for flash msgs

# File paths for JSON data
USERS_FILE = 'users.json'
ACCOUNTS_FILE = 'accounts.json'
TRANSACTIONS_FILE = 'transactions.json'

# Function to load JSON data
def load_json_data(file_path):
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

# Function to save JSON data
def save_json_data(file_path, data):
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)

# Routes and logic

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        password = request.form['password']
        phone = request.form['phone']
        address = request.form['address']
        aadhar_number = request.form['aadhar_number']
        pan_card = request.form['pan_card']

        # Load users from JSON file
        users = load_json_data(USERS_FILE)

        # Check if the user already exists
        if any(user['email'] == email for user in users):
            flash("Email already exists! Please log in.")
            return redirect(url_for('login'))

        # Validate phone number and Aadhar number
        if len(phone) != 10:
            flash("Phone number must be 10 digits")
            return render_template("register.html")
        if len(aadhar_number) != 12:
            flash("Aadhar number must be 12 digits")
            return render_template("register.html")

        # Add new user to JSON
        new_user = {
            'full_name': full_name,
            'email': email,
            'password': password,
            'phone': phone,
            'address': address,
            'aadhar_number': aadhar_number,
            'pan_card': pan_card
        }
        users.append(new_user)
        save_json_data(USERS_FILE, users)

        session['user'] = {'full_name': full_name, 'email': email}
        flash("Registration successful! Please log in.")
        return redirect(url_for('confirm'))

    return render_template("register.html")

@app.route("/confirm")
def confirm():
    user = session.get('user')
    if user:
        return render_template("confirm.html", user=user)
    else:
        return redirect(url_for('login'))

@app.route("/login", methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Load users from JSON file
        users = load_json_data(USERS_FILE)

        # Verify login credentials
        user = next((u for u in users if u['email'] == email and u['password'] == password), None)

        if user:
            session['user'] = {'full_name': user['full_name'], 'email': user['email']}
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid login credentials!")
            return redirect(url_for('login'))

    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    user_data = session.get('user')
    if user_data:
        return render_template("dashboard.html", user=user_data)
    else:
        return redirect(url_for('login'))

@app.route("/deposit", methods=['POST', 'GET'])
def deposit():
    user_data = session.get('user')
    if user_data:
        if request.method == 'POST':
            amount = float(request.form['deposit_amount'])
            account_type = request.form['account_type']

            # Load accounts from JSON file
            accounts = load_json_data(ACCOUNTS_FILE)

            # Check if user has an account, if not, create one
            account = next((acc for acc in accounts if acc['email'] == user_data['email']), None)

            if not account:
                account = {
                    'email': user_data['email'],
                    'balance': amount,
                    'account_type': account_type
                }
                accounts.append(account)
            else:
                account['balance'] += amount

            # Save updated account data
            save_json_data(ACCOUNTS_FILE, accounts)

            # Log the transaction
            transactions = load_json_data(TRANSACTIONS_FILE)
            transaction = {
                'email': user_data['email'],
                'transaction_type': 'Credit',
                'transaction_amount': amount,
                'transaction_date': str(datetime.now())
            }
            transactions.append(transaction)
            save_json_data(TRANSACTIONS_FILE, transactions)

            flash("Funds deposited successfully!")
            return redirect(url_for('dashboard'))

        return render_template("deposit.html")
    else:
        return redirect(url_for('login'))

@app.route("/balance", methods=['GET'])
def check_balance():
    user_data = session.get('user')
    if user_data:
        accounts = load_json_data(ACCOUNTS_FILE)
        account = next((acc for acc in accounts if acc['email'] == user_data['email']), None)

        if account:
            return render_template("balance.html", balance=account['balance'])
        else:
            flash("No account found!")
            return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))

@app.route("/account-statement", methods=['GET'])
def account_statement():
    user_data = session.get('user')
    if user_data:
        transactions = load_json_data(TRANSACTIONS_FILE)
        user_transactions = [txn for txn in transactions if txn['email'] == user_data['email']]
        return render_template("account_statement.html", transactions=user_transactions)
    else:
        return redirect(url_for('login'))

@app.route("/transfer", methods=['POST', 'GET'])
def transfer():
    user_data = session.get('user')
    if user_data:
        if request.method == 'POST':
            recipient_email = request.form.get('recipient_email')
            amount = float(request.form.get('amount'))

            if recipient_email and amount:
                # Load accounts and users
                accounts = load_json_data(ACCOUNTS_FILE)
                users = load_json_data(USERS_FILE)

                # Find recipient account
                recipient_account = next((acc for acc in accounts if acc['email'] == recipient_email), None)
                if not recipient_account:
                    flash("Recipient account not found!")
                    return redirect(url_for('transfer'))

                # Find sender's account
                sender_account = next((acc for acc in accounts if acc['email'] == user_data['email']), None)
                if not sender_account:
                    flash("Sender account not found!")
                    return redirect(url_for('transfer'))

                if sender_account['balance'] >= amount:
                    # Process transfer
                    sender_account['balance'] -= amount
                    recipient_account['balance'] += amount

                    # Save updated account data
                    save_json_data(ACCOUNTS_FILE, accounts)

                    # Log the transactions
                    transactions = load_json_data(TRANSACTIONS_FILE)
                    transactions.append({
                        'email': user_data['email'],
                        'transaction_type': 'Debit',
                        'transaction_amount': amount,
                        'transaction_date': str(datetime.now())
                    })
                    transactions.append({
                        'email': recipient_email,
                        'transaction_type': 'Credit',
                        'transaction_amount': amount,
                        'transaction_date': str(datetime.now())
                    })
                    save_json_data(TRANSACTIONS_FILE, transactions)

                    flash("Funds transferred successfully!")
                    return redirect(url_for('dashboard'))
                else:
                    flash("Insufficient balance!")
                    return redirect(url_for('transfer'))

            else:
                flash("Please fill in all fields!")
                return redirect(url_for('transfer'))

        return render_template("transfer.html")
    else:
        return redirect(url_for('login'))

@app.route("/customer-support")
def customer_support():
    return render_template("customer_support.html")

@app.route("/services")
def services():
    return render_template("services.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
