# app/routes.py
import matplotlib
matplotlib.use('Agg')
from flask import request, jsonify, render_template, render_template_string, session, redirect, url_for
from app import db, bcrypt
from app.models import User, Expense, Income, Budget, User
from datetime import datetime
from sqlalchemy import func

from app.visuals import plot_category_expenses
from collections import defaultdict


from io import BytesIO
import base64
import matplotlib.pyplot as plt

def register_routes(app):
    @app.route("/")
    def home():
        return "Budget Manager Backend Running!"
    
    # ----------------- User Auth -----------------
    @app.route('/register', methods=['POST'])
    def register():
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

        # Check if user exists
        if User.query.filter((User.username == username) | (User.email == email)).first():
            return jsonify({"error": "User already exists"}), 400

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(username=username, email=email, password_hash=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        return jsonify({"message": "User registered successfully!"}), 201

    @app.route('/login', methods=['POST'])
    def login():
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        user = User.query.filter_by(username=username).first()

        if user and bcrypt.check_password_hash(user.password_hash, password):
            return jsonify({"message": "Login successful!"}), 200
        else:
            return jsonify({"error": "Invalid credentials"}), 401
    
    # ----------------- Expenses CRUD -----------------
    @app.route('/expenses', methods=['POST'])
    def add_expense():
        data = request.get_json()
        user_id = data.get('user_id')
        category = data.get('category')
        amount = data.get('amount')
        notes = data.get('notes', '')

        expense = Expense(user_id=user_id, category=category, amount=amount, notes=notes)
        db.session.add(expense)
        db.session.commit()

        return jsonify({"message": "Expense added successfully!"}), 201

    @app.route('/expenses', methods=['GET'])
    def get_expenses():
        user_id = request.args.get('user_id')
        expenses = Expense.query.filter_by(user_id=user_id).all()
        return jsonify([{
            "id": e.id,
            "category": e.category,
            "amount": e.amount,
            "date": e.date,
            "notes": e.notes
        } for e in expenses]), 200

    @app.route('/expenses/<int:expense_id>', methods=['PUT'])
    def update_expense(expense_id):
        data = request.get_json()
        expense = Expense.query.get_or_404(expense_id)

        expense.category = data.get('category', expense.category)
        expense.amount = data.get('amount', expense.amount)
        expense.notes = data.get('notes', expense.notes)
        db.session.commit()

        return jsonify({"message": "Expense updated successfully!"}), 200

    @app.route('/expenses/<int:expense_id>', methods=['DELETE'])
    def delete_expense(expense_id):
        expense = Expense.query.get_or_404(expense_id)
        db.session.delete(expense)
        db.session.commit()
        return jsonify({"message": "Expense deleted successfully!"}), 200

    # ----------------- Income CRUD -----------------
    @app.route('/income', methods=['POST'])
    def add_income():
        data = request.get_json()
        user_id = data.get('user_id')
        source = data.get('source')
        amount = data.get('amount')

        income = Income(user_id=user_id, source=source, amount=amount)
        db.session.add(income)
        db.session.commit()

        return jsonify({"message": "Income added successfully!"}), 201

    @app.route('/income', methods=['GET'])
    def get_income():
        user_id = request.args.get('user_id')
        incomes = Income.query.filter_by(user_id=user_id).all()
        return jsonify([{
            "id": i.id,
            "source": i.source,
            "amount": i.amount,
            "date": i.date
        } for i in incomes]), 200

    @app.route('/income/<int:income_id>', methods=['PUT'])
    def update_income(income_id):
        data = request.get_json()
        income = Income.query.get_or_404(income_id)

        income.source = data.get('source', income.source)
        income.amount = data.get('amount', income.amount)
        db.session.commit()

        return jsonify({"message": "Income updated successfully!"}), 200

    @app.route('/income/<int:income_id>', methods=['DELETE'])
    def delete_income(income_id):
        income = Income.query.get_or_404(income_id)
        db.session.delete(income)
        db.session.commit()
        return jsonify({"message": "Income deleted successfully!"}), 200
    
    # ----------------- Summary Endpoint -----------------
    @app.route('/summary', methods=['GET'])
    def get_summary():
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400

        now = datetime.utcnow()
        start_of_month = datetime(now.year, now.month, 1)

        # Total Expenses
        total_expenses = db.session.query(func.sum(Expense.amount)) \
            .filter(Expense.user_id == user_id, Expense.date >= start_of_month).scalar() or 0

        # Total Income
        total_income = db.session.query(func.sum(Income.amount)) \
            .filter(Income.user_id == user_id, Income.date >= start_of_month).scalar() or 0

        balance = total_income - total_expenses

        return jsonify({
            "total_expenses": total_expenses,
            "total_income": total_income,
            "balance": balance
        }), 200
        
    # ----------------- Budget CRUD -----------------

    @app.route('/budgets', methods=['POST'])
    def add_budget():
        data = request.get_json()
        user_id = data.get('user_id')
        category = data.get('category')
        monthly_limit = data.get('monthly_limit')

        budget = Budget(user_id=user_id, category=category, monthly_limit=monthly_limit)
        db.session.add(budget)
        db.session.commit()

        return jsonify({"message": "Budget added successfully!"}), 201

    @app.route('/budgets', methods=['GET'])
    def get_budgets():
        user_id = request.args.get('user_id')
        budgets = Budget.query.filter_by(user_id=user_id).all()
        return jsonify([{
            "id": b.id,
            "category": b.category,
            "monthly_limit": b.monthly_limit
        } for b in budgets]), 200

    @app.route('/budgets/<int:budget_id>', methods=['PUT'])
    def update_budget(budget_id):
        data = request.get_json()
        budget = Budget.query.get_or_404(budget_id)

        budget.category = data.get('category', budget.category)
        budget.monthly_limit = data.get('monthly_limit', budget.monthly_limit)
        db.session.commit()

        return jsonify({"message": "Budget updated successfully!"}), 200

    @app.route('/budgets/<int:budget_id>', methods=['DELETE'])
    def delete_budget(budget_id):
        budget = Budget.query.get_or_404(budget_id)
        db.session.delete(budget)
        db.session.commit()
        return jsonify({"message": "Budget deleted successfully!"}), 200
    
    # ----------------- Remaining Budget -----------------
    @app.route('/budgets/remaining', methods=['GET'])
    def remaining_budget():
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400

        now = datetime.utcnow()
        start_of_month = datetime(now.year, now.month, 1)

        budgets = Budget.query.filter_by(user_id=user_id).all()
        result = []

        for b in budgets:
            spent = db.session.query(func.sum(Expense.amount)) \
                .filter(Expense.user_id == user_id,
                        Expense.category == b.category,
                        Expense.date >= start_of_month).scalar() or 0
            remaining = b.monthly_limit - spent
            result.append({
                "category": b.category,
                "monthly_limit": b.monthly_limit,
                "spent": spent,
                "remaining": remaining
            })

        return jsonify(result), 200
        
    # ----------------- Monthly Report -----------------
    @app.route('/reports/monthly', methods=['GET'])
    def monthly_report():
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400

        now = datetime.utcnow()
        start_of_month = datetime(now.year, now.month, 1)

        # Expenses per category
        budgets = Budget.query.filter_by(user_id=user_id).all()
        report = []
        overspending_alerts = []

        for b in budgets:
            spent = db.session.query(func.sum(Expense.amount)) \
                .filter(Expense.user_id == user_id,
                        Expense.category == b.category,
                        Expense.date >= start_of_month).scalar() or 0
            remaining = b.monthly_limit - spent

            if remaining < 0:
                alert_message = f"Overspending alert! {b.category}: Spent {spent}, Limit {b.monthly_limit}"
                print(f"[*************************************** ALERT *******************************] {alert_message}")  # log
                overspending_alerts.append(alert_message)

            report.append({
                "category": b.category,
                "monthly_limit": b.monthly_limit,
                "spent": spent,
                "remaining": remaining
            })


        # Total summary
        total_income = db.session.query(func.sum(Income.amount)) \
            .filter(Income.user_id == user_id, Income.date >= start_of_month).scalar() or 0
        total_expenses = db.session.query(func.sum(Expense.amount)) \
            .filter(Expense.user_id == user_id, Expense.date >= start_of_month).scalar() or 0
        balance = total_income - total_expenses
        
        

        return jsonify({
            "total_income": total_income,
            "total_expenses": total_expenses,
            "balance": balance,
            "categories": report,
            "overspending_alerts": overspending_alerts
        }), 200
    

    # ----------------- Reports with Charts -----------------
    @app.route('/reports/visual', methods=['GET'])
    def reports_visual():
        # ✅ Require login
        if 'user_id' not in session:
            return jsonify({"error": "Not logged in"}), 401

        user_id = session['user_id']  # ✅ Use session instead of URL

        now = datetime.utcnow()
        start_of_month = datetime(now.year, now.month, 1)

        # --------- 1. Spending by Category (Pie Chart) ---------
        category_data = db.session.query(
            Expense.category,
            func.sum(Expense.amount)
        ).filter(
            Expense.user_id == user_id,
            Expense.date >= start_of_month
        ).group_by(Expense.category).all()

        categories = [c[0] for c in category_data]
        amounts = [c[1] for c in category_data]

        pie_buf = BytesIO()
        plt.figure(figsize=(4,4))
        plt.pie(amounts, labels=categories, autopct='%1.1f%%')
        plt.title("Spending by Category")
        plt.tight_layout()
        plt.savefig(pie_buf, format="png")
        pie_buf.seek(0)
        pie_img = base64.b64encode(pie_buf.read()).decode('utf-8')
        plt.close()

        # --------- 2. Spending Trends (Line Chart) ---------
        daily_data = db.session.query(
            func.date(Expense.date),
            func.sum(Expense.amount)
        ).filter(
            Expense.user_id == user_id,
            Expense.date >= start_of_month
        ).group_by(func.date(Expense.date)).all()

        dates = [str(d[0]) for d in daily_data]
        daily_amounts = [d[1] for d in daily_data]

        line_buf = BytesIO()
        plt.figure(figsize=(5,3))
        plt.plot(dates, daily_amounts, marker="o")
        plt.title("Daily Spending Trend")
        plt.xlabel("Date")
        plt.ylabel("Amount")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(line_buf, format="png")
        line_buf.seek(0)
        line_img = base64.b64encode(line_buf.read()).decode('utf-8')
        plt.close()

        # --------- 3. Income vs Expenses (Bar Chart) ---------
        total_income = db.session.query(func.sum(Income.amount)).filter(
            Income.user_id == user_id,
            Income.date >= start_of_month
        ).scalar() or 0

        total_expenses = db.session.query(func.sum(Expense.amount)).filter(
            Expense.user_id == user_id,
            Expense.date >= start_of_month
        ).scalar() or 0

        bar_buf = BytesIO()
        plt.figure(figsize=(4,3))
        plt.bar(["Income", "Expenses"], [total_income, total_expenses], color=["green", "red"])
        plt.title("Income vs Expenses")
        plt.tight_layout()
        plt.savefig(bar_buf, format="png")
        bar_buf.seek(0)
        bar_img = base64.b64encode(bar_buf.read()).decode('utf-8')
        plt.close()

        # --------- Render in HTML ---------
        html_template = """
        <html>
        <head><title>Reports Dashboard</title></head>
        <body>
            <h1>Reports Dashboard - User {{ user_id }}</h1>
            <h2>Spending by Category</h2>
            <img src="data:image/png;base64,{{ pie_img }}" />

            <h2>Daily Spending Trend</h2>
            <img src="data:image/png;base64,{{ line_img }}" />

            <h2>Income vs Expenses</h2>
            <img src="data:image/png;base64,{{ bar_img }}" />
        </body>
        </html>
        """

        return render_template_string(
            html_template,
            user_id=user_id,
            pie_img=pie_img,
            line_img=line_img,
            bar_img=bar_img
        )