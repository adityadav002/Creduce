import os
from flask import Flask, render_template, request, redirect, url_for
import mysql.connector
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression
import joblib
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import bcrypt
from dotenv import load_dotenv
from urllib.parse import urlparse
import calendar

# ---------------- SETUP ---------------- #
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev_key")
print("🚀 Flask app starting...")

# Load ML model
model = joblib.load("trained_model.pkl")

# ---------------- DATABASE CONNECTION ---------------- #

def get_db_connection():
    """Create and return a new database connection"""
    try:
        db_url = os.environ.get("MYSQL_URL")

        if db_url:
            # Production (Render with MYSQL_URL)
            url = urlparse(db_url)
            db = mysql.connector.connect(
                host=url.hostname,
                port=url.port or 3306,
                user=url.username,
                password=url.password,
                database=url.path[1:] if url.path else None
            )
        else:
            # Local development
            db = mysql.connector.connect(
                host=os.environ.get("DB_HOST", "localhost"),
                user=os.environ.get("DB_USER", "root"),
                password=os.environ.get("DB_PASS", ""),
                database=os.environ.get("DB_NAME", "expense_tracker"),
                port=int(os.environ.get("DB_PORT", 3306))
            )
        
        print("✅ Database connected successfully")
        return db

    except Exception as e:
        print(f"❌ DB CONNECTION ERROR: {e}")
        return None


def get_cursor():
    """Get a cursor and connection - creates new connection each time"""
    db = get_db_connection()
    if db is None:
        return None, None
    return db.cursor(), db


# ---------------- AUTH ---------------- #

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


class User(UserMixin):
    def __init__(self, id):
        self.id = id


@login_manager.user_loader
def load_user(user_id):
    return User(user_id)


# ---------------- HELPERS ---------------- #

def fetch_df(query, params=None):
    """Execute query and return DataFrame"""
    cursor, db = get_cursor()
    if cursor is None:
        return pd.DataFrame()
    
    try:
        cursor.execute(query, params or ())
        data = cursor.fetchall()
        columns = [col[0] for col in cursor.description]
        return pd.DataFrame(data, columns=columns)
    finally:
        cursor.close()
        db.close()


# ---------------- AUTH ROUTES ---------------- #

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        cursor, db = get_cursor()
        if cursor is None:
            return "Database connection failed"
        
        try:
            name = request.form["name"]
            email = request.form["email"]
            password = request.form["password"]

            hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

            cursor.execute(
                "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
                (name, email, hashed_pw)
            )
            db.commit()
            return redirect("/login")
        
        except Exception as e:
            print(f"Registration error: {e}")
            db.rollback()
            return f"Registration failed: {e}"
        
        finally:
            cursor.close()
            db.close()
    
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        cursor, db = get_cursor()
        if cursor is None:
            return "Database not connected"
        
        try:
            email = request.form["email"]
            password = request.form["password"]

            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()

            if user is None:
                return "User not found"

            stored_password = user[3]

            if bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):
                login_user(User(user[0]))
                print(f"✅ User logged in: {user[1]}")
                return redirect("/")

            return redirect(url_for("login"))
        
        finally:
            cursor.close()
            db.close()
    
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/login")


# ---------------- MAIN DASHBOARD & PROFILE ---------------- #

@app.route("/")
@login_required
def main():
    print("🏠 HOME ROUTE HIT")
    
    user_id = current_user.id
    now = datetime.now()

    try:
        df = fetch_df(
            "SELECT * FROM expenses WHERE user_id = %s",
            (user_id,)
        )
    except Exception as e:
        print(f"FETCH ERROR: {e}")
        return "Error fetching data"
    
    # Initialize all variables
    total = avg = count = 0
    max_amount, max_note = 0, "N/A"
    top_category = top_amount = low_category = low_amount = None
    monthly_budget = 0
    remaining_spending = 0
    over_spending = 0
    predicted_expense = 0
    today_total = week_total = month_total = year_total = 0
    
    # Get labels
    today_label = now.strftime("%b %d, %Y")
    current_month_name = now.strftime("%B")
    start_of_week = now - timedelta(days=now.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    week_range = f"{start_of_week.strftime('%b %d')} – {end_of_week.strftime('%b %d')}"
    month_range = now.strftime("%b 1") + " – " + now.strftime("%b %d")
    year_label = now.year
    
    # Get Budget
    cursor, db = get_cursor()
    if cursor:
        try:
            cursor.execute(
                "SELECT budget_amount FROM budget WHERE user_id = %s LIMIT 1",
                (user_id,)
            )
            row = cursor.fetchone()
            monthly_budget = row[0] if row else 0
        except Exception as e:
            print(f"BUDGET ERROR: {e}")
            monthly_budget = 0
        finally:
            cursor.close()
            db.close()

    if not df.empty:
        df["exp_date"] = pd.to_datetime(df["exp_date"])
        
        # Today
        today_df = df[df["exp_date"].dt.date == now.date()]
        today_total = float(today_df["amount"].sum()) if not today_df.empty else 0

        # This Week (Mon–Sun)
        week_df = df[
            (df["exp_date"] >= start_of_week) &
            (df["exp_date"] <= end_of_week)
        ]
        week_total = float(week_df["amount"].sum()) if not week_df.empty else 0

        # This Month
        month_df = df[
            (df["exp_date"].dt.month == now.month) &
            (df["exp_date"].dt.year == now.year)
        ]
        month_total = float(month_df["amount"].sum()) if not month_df.empty else 0

        # This Year
        year_df = df[df["exp_date"].dt.year == now.year]
        year_total = float(year_df["amount"].sum()) if not year_df.empty else 0

        # Monthly calculations
        monthly_df = df[
            (df["exp_date"].dt.month == now.month) &
            (df["exp_date"].dt.year == now.year)
        ]

        if not monthly_df.empty:
            total = float(monthly_df["amount"].sum())
            avg = float(round(monthly_df["amount"].mean(), 2))
            count = int(monthly_df["amount"].count())

            # Max expense
            try:
                max_row = monthly_df.loc[monthly_df["amount"].idxmax()]
                max_amount = float(max_row["amount"])
                max_note = max_row["note"]
            except:
                max_amount, max_note = 0, "N/A"

            # Category analysis
            category_totals = monthly_df.groupby("category")["amount"].sum()

            if not category_totals.empty:
                top_category, top_amount = category_totals.idxmax(), float(category_totals.max())
                low_category, low_amount = category_totals.idxmin(), float(category_totals.min())

        # Budget calculations
        remaining_spending = monthly_budget - total
        over_spending = total - monthly_budget

        # Prediction
        pred_df = df.copy()
        pred_df["exp_date"] = pd.to_datetime(pred_df["exp_date"])

        pred_df["amount"] = (pred_df["amount"]
                            .astype(str)
                            .str.replace("₹", "", regex=False)
                            .str.replace(",", "", regex=False)
                            .astype(float)
                            )    

        monthly_pred = pred_df.resample("ME", on="exp_date")["amount"].sum().reset_index()

        current_month = pd.Timestamp.now().month
        current_year = pd.Timestamp.now().year

        monthly_pred = monthly_pred[
            ~(
                (monthly_pred["exp_date"].dt.month == current_month) &
                (monthly_pred["exp_date"].dt.year == current_year)
            )
        ]

        monthly_pred["t"] = range(len(monthly_pred))

        if len(monthly_pred) >= 2:
            model = LinearRegression()
            model.fit(monthly_pred[["t"]], monthly_pred["amount"])

            next_t = np.array([[monthly_pred["t"].max() + 1]])
            predicted_expense = int(model.predict(next_t)[0])

            print("MONTHLY PRED DATA:")
            print(monthly_pred)
        else:
            predicted_expense = 0

    return render_template(
        "dashboard.html",
        total=total,
        average=avg,
        count=count,
        max_amount=max_amount,
        max_note=max_note,
        top_category=top_category,
        top_amount=top_amount,
        low_category=low_category,
        low_amount=low_amount,
        monthly_budget=monthly_budget,
        remaining_spending=remaining_spending,
        over_spending=over_spending,
        predicted_expense=predicted_expense,
        today_total=today_total,
        week_total=week_total,
        month_total=month_total,
        year_total=year_total,
        today_label=today_label,
        week_range=week_range,
        month_range=month_range,
        year_label=year_label,
        current_month_name=current_month_name
    )


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user_id = current_user.id
    cursor, db = get_cursor()
    
    if cursor is None:
        return "Database connection failed"
    
    try:
        cursor.execute("SELECT name, email FROM users WHERE id = %s", (user_id,))
        row = cursor.fetchone()

        if request.method == "POST":
            monthly_budget = request.form.get("monthly_budget")
            current_month = datetime.now().strftime("%Y-%m")

            cursor.execute("""
                SELECT id FROM budget 
                WHERE user_id = %s AND month = %s
            """, (user_id, current_month))

            existing = cursor.fetchone()

            if existing:
                cursor.execute("""
                    UPDATE budget 
                    SET budget_amount = %s
                    WHERE user_id = %s AND month = %s
                """, (monthly_budget, user_id, current_month))
            else:
                cursor.execute("""
                    INSERT INTO budget (month, budget_amount, user_id)
                    VALUES (%s, %s, %s)
                """, (current_month, monthly_budget, user_id))

            db.commit()

        user = {
            "name": row[0],
            "email": row[1]
        }
        return render_template("profile.html", user=user)
    
    finally:
        cursor.close()
        db.close()


# ---------------- CRUD (SECURE) ---------------- #

@app.route("/addExpense", methods=["GET", "POST"])
@login_required
def add_expense():
    if request.method == "POST":
        cursor, db = get_cursor()
        if cursor is None:
            return "Database connection failed"
        
        try:
            date = request.form["exp_date"]
            amount = float(request.form["amount"])
            note = request.form.get("note", "").lower()
            payment = request.form["payment"]
            category = request.form.get("category") or (model.predict([note])[0] if note else "other")

            cursor.execute("""
                INSERT INTO expenses 
                (exp_date, category, amount, note, pay_method, user_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (date, category, amount, note, payment, current_user.id))

            db.commit()
            return redirect("/")
        
        finally:
            cursor.close()
            db.close()

    return render_template("addExpense.html")


@app.route("/deleteExpense", methods=["POST"])
@login_required
def delete_expense():
    cursor, db = get_cursor()
    if cursor is None:
        return "Database connection failed"
    
    try:
        cursor.execute(
            "DELETE FROM expenses WHERE id=%s AND user_id=%s",
            (request.form["id"], current_user.id)
        )
        db.commit()
        return redirect("/")
    
    finally:
        cursor.close()
        db.close()


@app.route("/editExpense/<int:id>")
@login_required
def edit_expense(id):
    cursor, db = get_cursor()
    if cursor is None:
        return "Database connection failed"
    
    try:
        cursor.execute(
            "SELECT * FROM expenses WHERE id=%s AND user_id=%s",
            (id, current_user.id)
        )
        data = cursor.fetchone()
        return render_template("editExpense.html", expense=data)
    
    finally:
        cursor.close()
        db.close()


@app.route("/updateExpense", methods=["POST"])
@login_required
def update_expense():
    cursor, db = get_cursor()
    if cursor is None:
        return "Database connection failed"
    
    try:
        cursor.execute("""
            UPDATE expenses
            SET exp_date=%s, category=%s, amount=%s, note=%s, pay_method=%s
            WHERE id=%s AND user_id=%s
        """, (
            request.form["exp_date"],
            request.form["category"],
            request.form["amount"],
            request.form["note"],
            request.form["payment"],
            request.form["id"],
            current_user.id
        ))
        db.commit()
        return redirect("/")
    
    finally:
        cursor.close()
        db.close()


# ---------------- PAGES ---------------- #

@app.route("/transaction_detail")
@login_required
def history():
    cursor, db = get_cursor()
    if cursor is None:
        return "Database connection failed"
    
    try:
        cursor.execute(
            "SELECT * FROM expenses WHERE user_id = %s ORDER BY exp_date DESC",
            (current_user.id,)
        )
        data = cursor.fetchall()
        return render_template("transaction_detail.html", data=data)
    
    finally:
        cursor.close()
        db.close()


@app.route('/monthly_transaction')
@login_required
def monthly_transaction():
    user_id = current_user.id
    now = datetime.now()
    df = fetch_df(
        "SELECT * FROM expenses WHERE user_id = %s",
        (user_id,)
    )

    category_details = {}
    if not df.empty:
        df["exp_date"] = pd.to_datetime(df["exp_date"])
        monthly_df = df[
            (df["exp_date"].dt.month == now.month) &
            (df["exp_date"].dt.year == now.year)
        ]
        category_details = (
            monthly_df.groupby("category")
            .apply(lambda x: x[["amount", "note", "pay_method", "exp_date"]].to_dict("records"))
            .to_dict()
        )
    
    return render_template("monthly_transaction.html", category_details=category_details)


@app.route("/filter_transaction", methods=["GET"])
@login_required
def filter_transaction():
    user_id = current_user.id
    category = request.args.get("category")
    month = request.args.get("month")
    payment = request.args.get("payment")

    cursor, db = get_cursor()
    if cursor is None:
        return "Database connection failed"

    try:
        # If no filters → show empty state
        if not category and not month and not payment:
            return render_template("filter_transaction.html", data=[])

        query = "SELECT * FROM expenses WHERE user_id = %s"
        params = [user_id]

        # Only add category filter if it's NOT "all"
        if category and category != "all":
            query += " AND category = %s"
            params.append(category)

        # Only add payment filter if it's NOT "all"
        if payment and payment != "all":
            query += " AND pay_method = %s"
            params.append(payment)

        # Only add month filter if it's NOT "all"
        if month and month != "all":
            query += " AND MONTH(exp_date) = %s"
            params.append(int(month))

        query += " ORDER BY exp_date DESC"

        cursor.execute(query, tuple(params))
        data = cursor.fetchall()

        return render_template("filter_transaction.html", data=data)

    finally:
        cursor.close()
        db.close()


@app.route("/transaction_analysis")
@login_required
def transaction_analysis():
    user_id = current_user.id
    now = datetime.now()

    # Fetch current month data
    df = fetch_df(
        """
        SELECT exp_date, category, amount 
        FROM expenses 
        WHERE user_id = %s 
        AND MONTH(exp_date) = %s 
        AND YEAR(exp_date) = %s
        """,
        (user_id, now.month, now.year)
    )

    category_totals_dict = {}
    month_amounts = {}

    if not df.empty:
        df["exp_date"] = pd.to_datetime(df["exp_date"])

        # Category totals (current month)
        category_totals = df.groupby("category")["amount"].sum()
        category_totals_dict = category_totals.to_dict()

    # Fetch all data for monthly trend
    df_all = fetch_df(
        "SELECT exp_date, amount FROM expenses WHERE user_id = %s",
        (user_id,)
    )

    if not df_all.empty:
        df_all["exp_date"] = pd.to_datetime(df_all["exp_date"])

        month_amounts = (
            df_all.groupby(df_all["exp_date"].dt.month)["amount"]
            .sum()
            .sort_index()
            .to_dict()
        )

        month_amounts = {
            calendar.month_name[k]: v for k, v in month_amounts.items()
        }

    return render_template(
        "transaction_analysis.html",
        category_totals_dict=category_totals_dict,
        month_amounts=month_amounts
    )


@app.route("/compare_months", methods=["GET"])
@login_required
def compare_months():
    user_id = current_user.id
    month1 = request.args.get("month1")
    month2 = request.args.get("month2")
    year1 = request.args.get("year1")
    year2 = request.args.get("year2")
    
    df = fetch_df(
        """
        SELECT * FROM expenses 
        WHERE user_id = %s 
        AND (
            (MONTH(exp_date) = %s AND YEAR(exp_date) = %s)
            OR
            (MONTH(exp_date) = %s AND YEAR(exp_date) = %s)
        )
        """,
        (user_id, month1, year1, month2, year2)
    )
    
    labels = []
    m1_data = []
    m2_data = []

    if not df.empty and month1 and month2 and year1 and year2:
        df["exp_date"] = pd.to_datetime(df["exp_date"])
        
        # Filter by BOTH month and year
        m1_df = df[
            (df["exp_date"].dt.month == int(month1)) &
            (df["exp_date"].dt.year == int(year1))
        ]
        
        m2_df = df[
            (df["exp_date"].dt.month == int(month2)) &
            (df["exp_date"].dt.year == int(year2))
        ]
        
        # Group by DAY
        m1_group = m1_df.groupby(m1_df["exp_date"].dt.day)["amount"].sum()
        m2_group = m2_df.groupby(m2_df["exp_date"].dt.day)["amount"].sum()
        
        labels = list(range(1, 32))
        
        m1_data = [float(m1_group.get(day, 0)) for day in labels]
        m2_data = [float(m2_group.get(day, 0)) for day in labels]

    return render_template(
        "compare_months.html",
        labels=labels,
        m1_data=m1_data,
        m2_data=m2_data,
        month1=month1,
        month2=month2,
        year1=year1,
        year2=year2
    )

@app.route("/calculator", methods=["POST", "GET"])
@login_required
def calculator():
    return render_template("calculator.html")


# ---------------- RUN ---------------- #

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
