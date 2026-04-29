from fastapi import FastAPI, HTTPException
from datetime import date
from . import db_helper
from typing import List
from pydantic import BaseModel

app = FastAPI()


class Expense(BaseModel):
    amount: float
    category: str
    notes: str


class DateRange(BaseModel):
    start_date: date
    end_date: date


@app.get("/expenses/{expense_date}", response_model=List[Expense])
def get_expenses(expense_date: date):
    expenses = db_helper.fetch_expenses_for_date(expense_date)
    if expenses is None:
        raise HTTPException(status_code=500, detail="Failed to retrieve expenses from the database.")

    return expenses


@app.post("/expenses/{expense_date}")
def add_or_update_expense(expense_date: date, expenses:List[Expense]):
    db_helper.delete_expenses_for_date(expense_date)
    for expense in expenses:
        db_helper.insert_expense(expense_date, expense.amount, expense.category, expense.notes)

    return {"message": "Expenses updated successfully"}


@app.post("/analytics/")
def get_analytics(date_range: DateRange):
    data = db_helper.fetch_expense_summary(date_range.start_date, date_range.end_date)
    if data is None:
        raise HTTPException(status_code=500, detail="Failed to retrieve expense summary from the database.")

    total = sum([row['total'] for row in data])

    breakdown = {}
    for row in data:
        percentage = (row['total']/total)*100 if total != 0 else 0
        breakdown[row['category']] = {
            "total": row['total'],
            "percentage": percentage
        }

    return breakdown


@app.get("/monthly_summary/")
def get_analytics():
    monthly_summary = db_helper.fetch_monthly_expense_summary()
    if monthly_summary is None:
        raise HTTPException(status_code=500, detail="Failed to retrieve monthly expense summary from the database.")

    return monthly_summary

@app.get("/home_summary/")
def get_home_summary():
    month_data = db_helper.fetch_current_month_summary()
    today_data = db_helper.fetch_today_summary()
    if month_data is None or today_data is None:
        raise HTTPException(status_code=500, detail="Failed to retrieve home summary.")
    return {
        "total_this_month": month_data["total_this_month"],
        "total_transactions": month_data["total_transactions"],
        "largest_expense": month_data["largest_expense"],
        "total_today": today_data["total_today"],
        "transactions_today": today_data["transactions_today"],
        "top_category": today_data["top_category"],
        "top_category_amount": today_data["top_category_amount"],
        "busiest_day": today_data["busiest_day"],
        "busiest_day_amount": today_data["busiest_day_amount"],
        "recent_expenses": today_data["recent_expenses"]
    }

class Budget(BaseModel):
    category: str
    budget_limit: float

@app.get("/budgets/")
def get_budgets():
    budgets = db_helper.fetch_all_budgets()
    if budgets is None:
        raise HTTPException(status_code=500, detail="Failed to retrieve budgets.")
    return budgets

@app.post("/budgets/")
def set_budget(budget: Budget):
    db_helper.upsert_budget(budget.category, budget.budget_limit)
    return {"message": f"Budget for {budget.category} set successfully"}

@app.get("/budgets/vs_actual/")
def get_budget_vs_actual():
    data = db_helper.fetch_budget_vs_actual()
    if data is None:
        raise HTTPException(status_code=500, detail="Failed to retrieve budget comparison.")
    return data

@app.get("/spending_trend/")
def get_spending_trend(period: str = "month"):
    data = db_helper.fetch_spending_trend(period)
    if data is None:
        raise HTTPException(status_code=500, detail="Failed to retrieve spending trend.")
    return data

class Category(BaseModel):
    name: str

@app.get("/all_expenses/")
def get_all_expenses(search: str = "", category: str = "",
                     month: str = "", week_start: str = "", year: str = ""):
    data = db_helper.fetch_all_expenses(search, category, month, week_start, year)
    if data is None:
        raise HTTPException(status_code=500, detail="Failed to retrieve expenses.")
    return data

@app.delete("/expenses/{expense_id}")
def delete_expense(expense_id: int):
    db_helper.delete_expense_by_id(expense_id)
    return {"message": "Expense deleted successfully"}

@app.get("/categories/")
def get_categories():
    return db_helper.fetch_all_categories()

@app.post("/categories/")
def add_category(category: Category):
    db_helper.add_category(category.name)
    return {"message": f"Category '{category.name}' added successfully"}