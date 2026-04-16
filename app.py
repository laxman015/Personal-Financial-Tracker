from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session
from datetime import datetime
import sqlite3
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for flash messages
DATABASE_FILE = 'finance_data.db'


def get_db_connection():
    connection = sqlite3.connect(DATABASE_FILE)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute('PRAGMA foreign_keys = ON')
    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        )
        '''
    )
    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            user_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        '''
    )
    columns = {
        column['name'] for column in cursor.execute('PRAGMA table_info(transactions)').fetchall()
    }
    if 'user_id' not in columns:
        cursor.execute('ALTER TABLE transactions ADD COLUMN user_id INTEGER')
    connection.commit()
    connection.close()


def get_user_by_username(username):
    connection = get_db_connection()
    user = connection.execute(
        'SELECT id, username, password_hash FROM users WHERE username = ?',
        (username,)
    ).fetchone()
    connection.close()
    return dict(user) if user else None


def get_user_by_id(user_id):
    connection = get_db_connection()
    user = connection.execute(
        'SELECT id, username FROM users WHERE id = ?',
        (user_id,)
    ).fetchone()
    connection.close()
    return dict(user) if user else None


def create_user(username, password):
    connection = get_db_connection()
    cursor = connection.execute(
        'INSERT INTO users (username, password_hash) VALUES (?, ?)',
        (username, generate_password_hash(password))
    )
    connection.commit()
    user_id = cursor.lastrowid
    connection.close()
    return user_id


def get_current_user():
    user_id = session.get('user_id')
    if not user_id:
        return None
    return get_user_by_id(user_id)


def login_required(view_function):
    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if not session.get('user_id'):
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('login'))
        return view_function(*args, **kwargs)

    return wrapped_view


@app.context_processor
def inject_current_user():
    return {'current_user': get_current_user()}


@app.template_filter('format_rs')
def format_rs(value):
    try:
        amount = int(float(value))
    except (TypeError, ValueError):
        amount = 0
    return f'Rs {amount}'


def get_transactions(user_id):
    connection = get_db_connection()
    rows = connection.execute(
        '''
        SELECT date, amount, category, description
        FROM transactions
        WHERE user_id = ?
        ORDER BY date ASC, id ASC
        ''',
        (user_id,)
    ).fetchall()
    connection.close()
    return [dict(row) for row in rows]


def parse_amount(amount_value):
    try:
        amount = int(amount_value)
    except (TypeError, ValueError):
        return None

    if str(amount) != str(amount_value).strip():
        return None

    return amount


initialize_database()


@app.route('/')
@login_required
def index():
    current_user = get_current_user()
    transactions = get_transactions(current_user['id'])
    return render_template('index.html', transactions=transactions, current_user=current_user)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if session.get('user_id'):
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if not username or not password:
            flash('Username and password are required.', 'danger')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')

        if get_user_by_username(username):
            flash('Username already exists. Please choose another one.', 'danger')
            return render_template('register.html')

        user_id = create_user(username, password)
        session['user_id'] = user_id
        flash('Account created successfully.', 'success')
        return redirect(url_for('index'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        user = get_user_by_username(username)

        if not user or not check_password_hash(user['password_hash'], password):
            flash('Invalid username or password.', 'danger')
            return render_template('login.html')

        session['user_id'] = user['id']
        flash('Logged in successfully.', 'success')
        return redirect(url_for('index'))

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))


@app.route('/add_transaction', methods=['GET', 'POST'])
@login_required
def add_transaction():
    current_user = get_current_user()

    if request.method == 'POST':
        date = request.form['date']
        amount = request.form['amount']
        category = request.form['category']
        description = request.form['description']
        parsed_amount = parse_amount(amount)

        if parsed_amount is None:
            flash('Amount must be a whole number.', 'danger')
            return render_template('add_transaction.html', current_user=current_user)

        connection = get_db_connection()
        connection.execute(
            '''
            INSERT INTO transactions (date, amount, category, description, user_id)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (date, parsed_amount, category, description, current_user['id'])
        )
        connection.commit()
        connection.close()

        flash('Transaction added successfully!', 'success')
        return redirect(url_for('index'))

    return render_template('add_transaction.html', current_user=current_user)


@app.route('/view_transactions', methods=['GET', 'POST'])
@login_required
def view_transactions():
    current_user = get_current_user()

    if request.method == 'POST':
        start_date = request.form['start_date']
        end_date = request.form['end_date']

        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')

        transactions = get_transactions(current_user['id'])
        filtered_transactions = []

        for transaction in transactions:
            try:
                trans_date = datetime.strptime(transaction['date'], '%d-%m-%Y')
            except ValueError:
                try:
                    trans_date = datetime.strptime(transaction['date'], '%Y-%m-%d')
                except ValueError:
                    continue

            if start_date_obj <= trans_date <= end_date_obj:
                filtered_transactions.append(transaction)

        return render_template(
            'view_transactions.html',
            transactions=filtered_transactions,
            start_date=start_date,
            end_date=end_date,
            current_user=current_user
        )

    return render_template('view_transactions.html', current_user=current_user)


@app.route('/view_balance')
@login_required
def view_balance():
    current_user = get_current_user()
    transactions = get_transactions(current_user['id'])
    total_income = 0
    total_expense = 0

    for transaction in transactions:
        amount = float(transaction['amount'])
        if transaction['category'] == 'Income':
            total_income += amount
        else:
            total_expense += amount

    balance = total_income - total_expense
    return render_template(
        'view_balance.html',
        total_income=total_income,
        total_expense=total_expense,
        balance=balance,
        current_user=current_user
    )
if __name__ == '__main__':
    app.run(debug=True)
