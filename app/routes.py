# app/routes.py
import matplotlib
matplotlib.use('Agg')
from flask import request, jsonify, render_template, render_template_string, session, redirect, url_for
from app import db, bcrypt
from app.models import User, Expense, Income, Budget, User
from datetime import datetime, timedelta
from sqlalchemy import func

from app.visuals import plot_category_expenses
from collections import defaultdict

from io import BytesIO
import base64
import matplotlib.pyplot as plt


from sklearn.linear_model import LinearRegression
import numpy as np


import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from flask import send_file, current_app
import os
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from reportlab.lib.utils import ImageReader

from flask_login import current_user


def register_routes(app):
    @app.context_processor
    def inject_user():
        return dict(current_user=current_user)
    
    @app.route("/test")
    def test_page():
        return render_template("base.html", title="Test Page")
    
    @app.route("/dashboard")
    def dashboard():
        return render_template("dashboard.html", title="Dashboard")
    
    @app.route("/")
    def home():
        return "Budget Manager Backend Runnigggggggng!"
    
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
    
    # ----------------- Threshold 80% crossed notification -----------------
    @app.route('/check-budgets', methods=['GET'])
    def check_budgets():
        check_budget_thresholds()
        return {"message": "Budget thresholds checked. Alerts printed to console."}, 200
    
    def check_budget_thresholds():
        users = User.query.all()
        now = datetime.utcnow()
        start_of_month = datetime(now.year, now.month, 1)

        for user in users:
            budgets = Budget.query.filter_by(user_id=user.id).all()
            for b in budgets:
                spent = db.session.query(db.func.sum(Expense.amount)) \
                    .filter(
                        Expense.user_id == user.id,
                        Expense.category == b.category,
                        Expense.date >= start_of_month
                    ).scalar() or 0

                threshold = 0.8 * b.monthly_limit
                if spent >= threshold:
                    print(f"[ALERT] {user.username} has reached 80% of their {b.category} budget: Spent {spent}, Limit {b.monthly_limit}")
                    
    # ----------------- For ML -----------------
    @app.route('/predict/<int:user_id>', methods=['GET'])
    def predict_expenses(user_id):
        now = datetime.utcnow()
        start_of_data = datetime(now.year, now.month - 3, 1)  # Use last 3 months

        # Fetch historical data
        expenses = db.session.query(Expense).filter(
            Expense.user_id == user_id,
            Expense.date >= start_of_data
        ).all()

        if not expenses:
            return jsonify({"error": "Not enough data to predict"}), 400

        # Prepare data
        data = {}
        for e in expenses:
            key = e.category
            if key not in data:
                data[key] = []
            day_of_month = e.date.day
            data[key].append((day_of_month, e.amount))

        predictions = {}
        for category, values in data.items():
            X = np.array([v[0] for v in values]).reshape(-1, 1)
            y = np.array([v[1] for v in values])
            model = LinearRegression()
            model.fit(X, y)
            # Predict for next month's 1st day
            next_month_day = 1
            predicted_amount = model.predict(np.array([[next_month_day]]))[0]
            predictions[category] = round(predicted_amount, 2)

        return jsonify({
            "user_id": user_id,
            "predicted_expenses": predictions
        })
    
    # ----------------- Export to Excel -----------------
    @app.route('/export/excel', methods=['GET'])
    def export_excel():
        # ✅ Require login
        if 'user_id' not in session:
            return jsonify({"error": "Not logged in"}), 401

        user_id = session['user_id']  # ✅ Use session instead of URL
        # Get data
        incomes = Income.query.filter_by(user_id=user_id).all()
        expenses = Expense.query.filter_by(user_id=user_id).all()
        budgets = Budget.query.filter_by(user_id=user_id).all()

        # Convert to DataFrames
        income_df = pd.DataFrame([{
            "amount": i.amount,
            "date": str(i.date),
            "source": i.source
        } for i in incomes])

        expense_df = pd.DataFrame([{
            "amount": e.amount,
            "date": str(e.date),
            "category": e.category
        } for e in expenses])

        budget_df = pd.DataFrame([{
            "category": b.category,
            "monthly_limit": b.monthly_limit
        } for b in budgets])

        # Totals
        total_income = sum(income_df["amount"]) if not income_df.empty else 0
        total_expenses = sum(expense_df["amount"]) if not expense_df.empty else 0

        # Absolute path
        file_path = os.path.join(current_app.root_path, "instance", f"user_{user_id}_report.xlsx")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Save with charts (xlsxwriter engine)
        with pd.ExcelWriter(file_path, engine="xlsxwriter") as writer:
            if not income_df.empty:
                income_df.to_excel(writer, sheet_name="Income", index=False)
            if not expense_df.empty:
                expense_df.to_excel(writer, sheet_name="Expenses", index=False)
            if not budget_df.empty:
                budget_df.to_excel(writer, sheet_name="Budgets", index=False)

            workbook  = writer.book
            worksheet = workbook.add_worksheet("Charts")

            # -------- Bar Chart: Total Income vs Expenses --------
            bar_chart = workbook.add_chart({'type': 'column'})

            bar_chart.add_series({
                'name': "Income",
                'categories': ['Charts', 1, 0, 1, 0],   # category label in worksheet
                'values':     ['Charts', 1, 1, 1, 1],   # values column
            })
            bar_chart.add_series({
                'name': "Expenses",
                'categories': ['Charts', 2, 0, 2, 0],
                'values':     ['Charts', 2, 1, 2, 1],
            })

            bar_chart.set_title({'name': "Total Income vs Expenses"})
            bar_chart.set_y_axis({'name': "Amount"})

            # Write data for bar chart in worksheet
            worksheet.write(0, 0, "Type")
            worksheet.write(0, 1, "Amount")
            worksheet.write(1, 0, "Income")
            worksheet.write(1, 1, total_income)
            worksheet.write(2, 0, "Expenses")
            worksheet.write(2, 1, total_expenses)

            worksheet.insert_chart("D2", bar_chart)

            # -------- Pie Chart: Spending by Category --------
            if not expense_df.empty:
                # Aggregate by category
                category_totals = expense_df.groupby("category")["amount"].sum().reset_index()

                # Write category data for pie chart
                worksheet.write(5, 0, "Category")
                worksheet.write(5, 1, "Amount")
                for idx, row in category_totals.iterrows():
                    worksheet.write(6 + idx, 0, row["category"])
                    worksheet.write(6 + idx, 1, row["amount"])

                pie_chart = workbook.add_chart({'type': 'pie'})
                pie_chart.add_series({
                    'name': "Spending by Category",
                    'categories': ['Charts', 6, 0, 6 + len(category_totals) - 1, 0],
                    'values':     ['Charts', 6, 1, 6 + len(category_totals) - 1, 1],
                })
                pie_chart.set_title({'name': "Spending by Category"})

                worksheet.insert_chart("D20", pie_chart)

        return send_file(file_path, as_attachment=True)


    # ----------------- Export to PDF -----------------
    @app.route('/export/pdf', methods=['GET'])
    def export_pdf():
        
        # ✅ Require login
        if 'user_id' not in session:
            return jsonify({"error": "Not logged in"}), 401
        
        # Get totals
        total_income = db.session.query(func.sum(Income.amount)).filter_by(user_id=user_id).scalar() or 0
        total_expenses = db.session.query(func.sum(Expense.amount)).filter_by(user_id=user_id).scalar() or 0
        balance = total_income - total_expenses

        # Absolute path
        file_path = os.path.join(current_app.root_path, "instance", f"user_{user_id}_report.pdf")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        c = canvas.Canvas(file_path, pagesize=letter)
        width, height = letter

        # Title
        c.setFont("Helvetica-Bold", 16)
        c.drawString(200, height - 50, f"User {user_id} - Financial Report")

        # Summary
        c.setFont("Helvetica", 12)
        c.drawString(50, height - 100, f"Total Income: {total_income}")
        c.drawString(50, height - 120, f"Total Expenses: {total_expenses}")
        c.drawString(50, height - 140, f"Balance: {balance}")

        # Budgets
        budgets = Budget.query.filter_by(user_id=user_id).all()
        c.drawString(50, height - 180, "Budgets:")
        y = height - 200
        for b in budgets:
            c.drawString(70, y, f"{b.category}: Limit {b.monthly_limit}")
            y -= 20

        # Expenses
        expenses = Expense.query.filter_by(user_id=user_id).limit(10).all()
        c.drawString(50, y - 20, "Recent Expenses:")
        y -= 40
        for e in expenses:
            c.drawString(70, y, f"{e.category} - {e.amount} on {e.date}")
            y -= 20

        # ----------------- Charts -----------------
        # 1. Pie chart: Spending by category
        category_data = db.session.query(
            Expense.category,
            func.sum(Expense.amount)
        ).filter(Expense.user_id==user_id).group_by(Expense.category).all()

        if category_data:
            categories = [c[0] for c in category_data]
            amounts = [c[1] for c in category_data]

            fig, ax = plt.subplots(figsize=(4,4))
            ax.pie(amounts, labels=categories, autopct='%1.1f%%')
            ax.set_title("Spending by Category")
            buf = BytesIO()
            plt.savefig(buf, format='png')
            plt.close(fig)
            buf.seek(0)
            pie_img = ImageReader(buf)
            c.drawImage(pie_img, 50, y - 250, width=300, height=200)  # adjust position

        # 2. Bar chart: Income vs Expenses
        fig2, ax2 = plt.subplots(figsize=(4,3))
        ax2.bar(["Income", "Expenses"], [total_income, total_expenses], color=["green", "red"])
        ax2.set_title("Income vs Expenses")
        buf2 = BytesIO()
        plt.savefig(buf2, format='png')
        plt.close(fig2)
        buf2.seek(0)
        bar_img = ImageReader(buf2)
        c.drawImage(bar_img, 50, y - 500, width=300, height=200)

        c.save()
        return send_file(file_path, as_attachment=True)