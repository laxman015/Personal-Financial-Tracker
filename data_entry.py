from datetime import datetime

def get_date(prompt="Enter date (dd-mm-yyyy): ", allow_default=False):
    while True:
        user_input = input(prompt).strip()
        if allow_default and user_input == "":
            return datetime.today().strftime("%d-%m-%Y")
        try:
            datetime.strptime(user_input, "%d-%m-%Y")
            return user_input
        except ValueError:
            print("Invalid date format. Please use dd-mm-yyyy.")

def get_amount():
    while True:
        try:
            amount = float(input("Enter the amount: "))
            if amount < 0:
                raise ValueError
            return amount
        except ValueError:
            print("Invalid amount. Please enter a positive number.")

def get_category():
    while True:
        category = input("Enter category (Income/Expense): ").strip().capitalize()
        if category in ["Income", "Expense"]:
            return category
        print("Invalid category. Please enter either 'Income' or 'Expense'.")

def get_description():
    return input("Enter a short description: ").strip()
