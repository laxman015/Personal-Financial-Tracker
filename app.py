from flask import Flask, render_template, request, redirect, url_for, flash
import csv
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for flash messages

# Ensure the CSV file exists
CSV_FILE = 'finance_data.csv'
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['date', 'amount', 'category', 'description'])

def get_transactions():
    transactions = []
    with open(CSV_FILE, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            transactions.append(row)
    return transactions

@app.route('/')
def index():
    transactions = get_transactions()
    return render_template('index.html', transactions=transactions)

@app.route('/add_transaction', methods=['GET', 'POST'])
def add_transaction():
    if request.method == 'POST':
        date = request.form['date']
        amount = request.form['amount']
        category = request.form['category']
        description = request.form['description']
        
        with open(CSV_FILE, 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([date, amount, category, description])
        
        flash('Transaction added successfully!', 'success')
        return redirect(url_for('index'))
    
    return render_template('add_transaction.html')

@app.route('/view_transactions', methods=['GET', 'POST'])
def view_transactions():
    if request.method == 'POST':
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        
        # Convert input dates from YYYY-MM-DD to datetime objects
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
        
        transactions = get_transactions()
        filtered_transactions = []
        
        for transaction in transactions:
            # Try both date formats
            try:
                trans_date = datetime.strptime(transaction['date'], '%d-%m-%Y')
            except ValueError:
                try:
                    trans_date = datetime.strptime(transaction['date'], '%Y-%m-%d')
                except ValueError:
                    continue  # Skip invalid date formats
            
            if start_date_obj <= trans_date <= end_date_obj:
                filtered_transactions.append(transaction)
        
        return render_template('view_transactions.html', 
                             transactions=filtered_transactions,
                             start_date=start_date,
                             end_date=end_date)
    
    return render_template('view_transactions.html')

@app.route('/view_balance')
def view_balance():
    transactions = get_transactions()
    total_income = 72000  # Default monthly income
    total_expense = 0
    
    for transaction in transactions:
        amount = float(transaction['amount'])
        if transaction['category'] == 'Income':
            total_income += amount
        else:
            total_expense += amount
    
    balance = total_income - total_expense
    return render_template('view_balance.html',
                         total_income=total_income,
                         total_expense=total_expense,
                         balance=balance)

if __name__ == '__main__':
    app.run(debug=True) 