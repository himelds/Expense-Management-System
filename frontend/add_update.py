import streamlit as st
from datetime import date
import requests
import pandas as pd

API_URL = "http://localhost:8000"

CATEGORY_ICONS = {
    "Food": "🍔", "Rent": "🏠", "Shopping": "🛍️",
    "Entertainment": "🎬", "Other": "💡",
    "Transport": "🚗", "Healthcare": "💊",
    "Travel": "✈️", "Gym": "💪", "Groceries": "🛒"
}

def add_update_tab():
    st.title("💳 Transactions")

    # ── Load categories ───────────────────────────────────────
    try:
        cat_resp = requests.get(f"{API_URL}/categories/")
        categories = cat_resp.json() if cat_resp.status_code == 200 else ["Rent","Food","Shopping","Entertainment","Other"]
    except:
        st.error("⚠️ Cannot connect to backend.")
        return

    # ── Sub-tabs ──────────────────────────────────────────────
    subtab1, subtab2 = st.tabs(["📋 All Transactions", "➕ Add / Edit"])

    # ════════════════════════════════════════════════════════════
    # SUB-TAB 1: All Transactions (like the image)
    # ════════════════════════════════════════════════════════════
    with subtab1:
        # ── Filters row ───────────────────────────────────────
        col1, col2, col3 = st.columns([3, 2, 2])
        with col1:
            search = st.text_input("🔍 Search notes...", placeholder="Search...",
                                   label_visibility="collapsed")
        with col2:
            period = st.selectbox("Period",
                                  ["All Time", "This Week", "This Month", "This Year"],
                                  label_visibility="collapsed")
        with col3:
            cat_filter = st.selectbox("Category", ["All"] + categories,
                                      label_visibility="collapsed")

        from datetime import datetime, timedelta
        today = date.today()
        if period == "This Week":
            start_of_week = today - timedelta(days=today.weekday())
            month_param = f"week:{start_of_week}"
        elif period == "This Month":
            month_param = f"month:{today.strftime('%Y-%m')}"
        elif period == "This Year":
            month_param = f"year:{today.year}"
        else:
            month_param = ""

        # ── Fetch transactions ────────────────────────────────
        try:
            # Parse period param
            week_start = month_yr = year = ""
            if month_param.startswith("week:"):
                week_start = month_param.split(":")[1]
            elif month_param.startswith("month:"):
                month_yr = month_param.split(":")[1]
            elif month_param.startswith("year:"):
                year = month_param.split(":")[1]

            resp = requests.get(f"{API_URL}/all_expenses/",
                                params={"search": search,
                                        "category": cat_filter,
                                        "week_start": week_start,
                                        "month": month_yr,
                                        "year": year})
            expenses = resp.json() if resp.status_code == 200 else []
        except:
            expenses = []

        if not expenses:
            st.info("No transactions found.")
        else:
            # ── Summary strip ─────────────────────────────────
            total = sum(e["amount"] for e in expenses)
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Transactions", len(expenses))
            c2.metric("Total Spent", f"${total:,.2f}")
            c3.metric("Average", f"${total/len(expenses):,.2f}")

            st.markdown("---")

            # ── Transaction rows ──────────────────────────────
            # Header
            h1, h2, h3, h4, h5 = st.columns([2, 3, 2, 3, 1])
            h1.markdown("**Date**")
            h2.markdown("**Notes**")
            h3.markdown("**Category**")
            h4.markdown("**Amount**")
            h5.markdown("**Del**")

            st.markdown("---")

            # Pagination
            PAGE_SIZE = 10
            total_pages = max(1, (len(expenses) + PAGE_SIZE - 1) // PAGE_SIZE)

            if "txn_page" not in st.session_state:
                st.session_state.txn_page = 1

            start = (st.session_state.txn_page - 1) * PAGE_SIZE
            page_expenses = expenses[start:start + PAGE_SIZE]

            for exp in page_expenses:
                icon = CATEGORY_ICONS.get(exp["category"], "💰")
                c1, c2, c3, c4, c5 = st.columns([2, 3, 2, 3, 1])
                c1.markdown(f"{exp['expense_date']}")
                c2.markdown(f"{exp['notes'] or '—'}")
                c3.markdown(f"{icon} {exp['category']}")
                c4.markdown(f"**- ${exp['amount']:,.2f}**")
                if c5.button("🗑️", key=f"del_{exp['id']}"):
                    requests.delete(f"{API_URL}/expenses/{exp['id']}")
                    st.success("Deleted!")
                    st.rerun()

            st.markdown("---")

            # ── Pagination controls ───────────────────────────
            p1, p2, p3 = st.columns([2, 3, 2])
            with p1:
                if st.button("◀ Previous", disabled=st.session_state.txn_page <= 1):
                    st.session_state.txn_page -= 1
                    st.rerun()
            with p2:
                st.markdown(
                    f"<p style='text-align:center'>Page {st.session_state.txn_page} of {total_pages}</p>",
                    unsafe_allow_html=True
                )
            with p3:
                if st.button("Next ▶", disabled=st.session_state.txn_page >= total_pages):
                    st.session_state.txn_page += 1
                    st.rerun()

    # ════════════════════════════════════════════════════════════
    # SUB-TAB 2: Add / Edit (original form, improved)
    # ════════════════════════════════════════════════════════════
    with subtab2:
        # ── Add custom category ───────────────────────────────
        st.markdown("### 🏷️ Manage Categories")
        col1, col2 = st.columns([3, 1])
        with col1:
            new_cat = st.text_input("New category",
                                    placeholder="e.g. Healthcare, Travel, Gym...",
                                    label_visibility="collapsed")
        with col2:
            if st.button("➕ Add", use_container_width=True):
                if new_cat.strip() == "":
                    st.warning("Please enter a category name.")
                elif new_cat.strip() in categories:
                    st.warning(f"'{new_cat}' already exists.")
                else:
                    r = requests.post(f"{API_URL}/categories/",
                                      json={"name": new_cat.strip()})
                    if r.status_code == 200:
                        st.success(f"✅ '{new_cat}' added!")
                        st.rerun()

        st.markdown("**Categories:** " + " · ".join(
            f"{CATEGORY_ICONS.get(c,'💰')} `{c}`" for c in categories))

        st.divider()

        # ── Expense form ──────────────────────────────────────
        st.markdown("### 📝 Add / Update Expenses")
        selected_date = st.date_input("Select Date", date.today())

        try:
            resp = requests.get(f"{API_URL}/expenses/{selected_date}")
            existing = resp.json() if resp.status_code == 200 else []
        except:
            existing = []

        with st.form(key="expense_form"):
            c1, c2, c3 = st.columns(3)
            c1.markdown("**Amount ($)**")
            c2.markdown("**Category**")
            c3.markdown("**Notes**")

            expenses_input = []
            for i in range(5):
                amount   = existing[i]["amount"]   if i < len(existing) else 0.0
                category = existing[i]["category"] if i < len(existing) else categories[0]
                notes    = existing[i]["notes"]    if i < len(existing) else ""
                if category not in categories:
                    categories.append(category)

                col1, col2, col3 = st.columns(3)
                with col1:
                    amt = st.number_input("Amount", min_value=0.0, step=1.0,
                                          value=float(amount), key=f"amt_{i}",
                                          label_visibility="collapsed")
                with col2:
                    cat = st.selectbox("Category", options=categories,
                                       index=categories.index(category),
                                       key=f"cat_{i}",
                                       label_visibility="collapsed")
                with col3:
                    nt = st.text_input("Notes", value=notes, key=f"nt_{i}",
                                       label_visibility="collapsed")
                expenses_input.append({"amount": amt, "category": cat, "notes": nt})

            if st.form_submit_button("💾 Save", use_container_width=True):
                filtered = [e for e in expenses_input if e["amount"] > 0]
                r = requests.post(f"{API_URL}/expenses/{selected_date}", json=filtered)
                if r.status_code == 200:
                    st.success("✅ Saved successfully!")
                else:
                    st.error("❌ Failed to save.")