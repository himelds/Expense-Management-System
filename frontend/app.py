import streamlit as st
from home import home_tab
from add_update import add_update_tab
from budgets import budgets_tab
from analytics import analytics_tab

st.title("💸 Expense Tracking System")

tab1, tab2, tab3, tab4 = st.tabs([
    "🏠 Home", "💳 Transactions", "💰 Budgets", "📊 Analytics"
])

with tab1:
    home_tab()
with tab2:
    add_update_tab()
with tab3:
    budgets_tab()
with tab4:
    analytics_tab()