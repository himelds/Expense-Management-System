import mysql.connector
from contextlib import contextmanager
from .logging_setup import setup_logger

logger = setup_logger('db_helper')

@contextmanager
def get_db_cursor(commit=False):
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="12345",
        database="expense_manager"
    )
    cursor = connection.cursor(dictionary=True)
    try:
        yield cursor
        if commit:
            connection.commit()
    except Exception as e:
        connection.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        cursor.close()
        connection.close()

def fetch_expenses_for_date(expense_date):
    logger.info(f"fetch_expenses_for_date called with {expense_date}")
    with get_db_cursor() as cursor:
        cursor.execute("SELECT * FROM expenses WHERE expense_date = %s", (expense_date,))
        expenses = cursor.fetchall()
        for e in expenses:
            e["expense_date"] = str(e["expense_date"])
        return expenses

def delete_expenses_for_date(expense_date):
    logger.info(f"delete_expenses_for_date called with {expense_date}")
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("DELETE FROM expenses WHERE expense_date = %s", (expense_date,))

def insert_expense(expense_date, amount, category, notes):
    logger.info(f"insert_expense called with date: {expense_date}, amount: {amount}, category: {category}, notes: {notes}")
    with get_db_cursor(commit=True) as cursor:
        cursor.execute(
            "INSERT INTO expenses (expense_date, amount, category, notes) VALUES (%s, %s, %s, %s)",
            (expense_date, amount, category, notes)
        )

def fetch_expense_summary(start_date, end_date):
    logger.info(f"fetch_expense_summary called with start: {start_date} end: {end_date}")
    with get_db_cursor() as cursor:
        cursor.execute(
            '''SELECT category, SUM(amount) as total 
               FROM expenses WHERE expense_date
               BETWEEN %s and %s  
               GROUP BY category;''',
            (start_date, end_date)
        )
        return cursor.fetchall()

def fetch_monthly_expense_summary():
    logger.info("fetch_expense_summary_by_months")
    with get_db_cursor() as cursor:
        cursor.execute(
            '''SELECT 
                YEAR(expense_date) as expense_year,
                MONTH(expense_date) as expense_month,
                MONTHNAME(expense_date) as month_name,
                SUM(amount) as total,
                COUNT(*) as transactions
               FROM expenses
               GROUP BY expense_year, expense_month, month_name
               ORDER BY expense_year DESC, expense_month DESC;
            '''
        )
        return cursor.fetchall()

def fetch_current_month_summary():
    logger.info("fetch_current_month_summary called")
    with get_db_cursor() as cursor:
        cursor.execute(
            '''SELECT 
                COALESCE(SUM(amount), 0) as total_this_month,
                COALESCE(COUNT(*), 0) as total_transactions,
                COALESCE(MAX(amount), 0) as largest_expense
               FROM expenses 
               WHERE MONTH(expense_date) = MONTH(CURDATE())
               AND YEAR(expense_date) = YEAR(CURDATE());
            '''
        )
        return cursor.fetchone()

def fetch_today_summary():
    logger.info("fetch_today_summary called")
    with get_db_cursor() as cursor:
        cursor.execute(
            '''SELECT 
                COALESCE(SUM(amount), 0) as total_today,
                COALESCE(COUNT(*), 0) as transactions_today
               FROM expenses 
               WHERE expense_date = CURDATE();
            '''
        )
        today = cursor.fetchone()

        cursor.execute(
            '''SELECT category, SUM(amount) as total
               FROM expenses
               WHERE MONTH(expense_date) = MONTH(CURDATE())
               AND YEAR(expense_date) = YEAR(CURDATE())
               GROUP BY category
               ORDER BY total DESC
               LIMIT 1;
            '''
        )
        top_category = cursor.fetchone()

        cursor.execute(
            '''SELECT expense_date, SUM(amount) as daily_total
               FROM expenses
               WHERE MONTH(expense_date) = MONTH(CURDATE())
               AND YEAR(expense_date) = YEAR(CURDATE())
               GROUP BY expense_date
               ORDER BY daily_total DESC
               LIMIT 1;
            '''
        )
        busiest_day = cursor.fetchone()

        cursor.execute(
            '''SELECT expense_date, category, amount, notes
               FROM expenses
               ORDER BY expense_date DESC
               LIMIT 8;
            '''
        )
        recent = cursor.fetchall()
        for r in recent:
            r["expense_date"] = str(r["expense_date"])

        if busiest_day:
            busiest_day["expense_date"] = str(busiest_day["expense_date"])

        return {
            "total_today": today["total_today"],
            "transactions_today": today["transactions_today"],
            "top_category": top_category["category"] if top_category else "N/A",
            "top_category_amount": top_category["total"] if top_category else 0,
            "busiest_day": busiest_day["expense_date"] if busiest_day else "N/A",
            "busiest_day_amount": busiest_day["daily_total"] if busiest_day else 0,
            "recent_expenses": recent
        }
    
def fetch_all_budgets():
    logger.info("fetch_all_budgets called")
    with get_db_cursor() as cursor:
        cursor.execute("SELECT category, budget_limit FROM budgets ORDER BY category;")
        return cursor.fetchall()

def upsert_budget(category, budget_limit):
    logger.info(f"upsert_budget called with category: {category}, limit: {budget_limit}")
    with get_db_cursor(commit=True) as cursor:
        cursor.execute(
            '''INSERT INTO budgets (category, budget_limit) 
               VALUES (%s, %s)
               ON DUPLICATE KEY UPDATE budget_limit = %s;
            ''',
            (category, budget_limit, budget_limit)
        )

def fetch_budget_vs_actual():
    logger.info("fetch_budget_vs_actual called")
    with get_db_cursor() as cursor:
        cursor.execute(
            '''SELECT 
                b.category,
                b.budget_limit,
                COALESCE(SUM(e.amount), 0) as spent
               FROM budgets b
               LEFT JOIN expenses e 
                 ON b.category = e.category
                 AND MONTH(e.expense_date) = MONTH(CURDATE())
                 AND YEAR(e.expense_date) = YEAR(CURDATE())
               GROUP BY b.category, b.budget_limit
               ORDER BY b.category;
            '''
        )
        rows = cursor.fetchall()
        result = []
        for row in rows:
            spent = float(row["spent"])
            limit = float(row["budget_limit"])
            result.append({
                "category": row["category"],
                "budget_limit": limit,
                "spent": spent,
                "remaining": max(limit - spent, 0),
                "percentage": round((spent / limit) * 100, 1) if limit > 0 else 0,
                "over_budget": spent > limit
            })
        return result
    
def fetch_spending_trend(period="month"):
    logger.info(f"fetch_spending_trend called with period: {period}")
    with get_db_cursor() as cursor:
        from datetime import date, timedelta
        today = date.today()

        if period == "week":
            start_date = today - timedelta(days=6)
        elif period == "quarter":
            start_date = today - timedelta(days=89)
        else:
            start_date = today - timedelta(days=29)

        cursor.execute(
            '''SELECT 
                DATE(expense_date) as expense_date,
                SUM(amount) as daily_total
               FROM expenses
               WHERE DATE(expense_date) >= %s AND DATE(expense_date) <= %s
               GROUP BY DATE(expense_date)
               ORDER BY DATE(expense_date) ASC;
            ''', (str(start_date), str(today))
        )
        rows = cursor.fetchall()
        for row in rows:
            row["expense_date"] = str(row["expense_date"])
        return rows

def fetch_all_expenses(search="", category="", month="", week_start="", year=""):
    logger.info("fetch_all_expenses called")
    with get_db_cursor() as cursor:
        query = "SELECT id, expense_date, amount, category, notes FROM expenses WHERE 1=1"
        params = []
        if search:
            query += " AND notes LIKE %s"
            params.append(f"%{search}%")
        if category and category != "All":
            query += " AND category = %s"
            params.append(category)
        if week_start:
            query += " AND expense_date >= %s AND expense_date <= %s"
            from datetime import datetime, timedelta
            end_of_week = str((datetime.strptime(week_start, "%Y-%m-%d") + timedelta(days=6)).date())
            params.extend([week_start, end_of_week])
        elif month:
            query += " AND YEAR(expense_date) = %s AND MONTH(expense_date) = %s"
            params.append(month.split("-")[0])
            params.append(str(int(month.split("-")[1])))
        elif year:
            query += " AND YEAR(expense_date) = %s"
            params.append(year)
        query += " ORDER BY expense_date DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        for row in rows:
            row["expense_date"] = str(row["expense_date"])
        return rows

def delete_expense_by_id(expense_id):
    logger.info(f"delete_expense_by_id called with id: {expense_id}")
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("DELETE FROM expenses WHERE id = %s", (expense_id,))

def fetch_all_categories():
    logger.info("fetch_all_categories called")
    with get_db_cursor() as cursor:
        cursor.execute("SELECT name FROM categories ORDER BY name;")
        return [row["name"] for row in cursor.fetchall()]

def add_category(name):
    logger.info(f"add_category called with name: {name}")
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("INSERT IGNORE INTO categories (name) VALUES (%s);", (name,))