import streamlit as st
import requests

API_URL = "http://localhost:8000"

def budgets_tab():
    st.title("💰 Budget Manager")

    try:
        response = requests.get(f"{API_URL}/budgets/vs_actual/")
        if response.status_code != 200:
            st.error("Failed to load budget data.")
            return
        data = response.json()
    except requests.exceptions.ConnectionError:
        st.error("⚠️ Cannot connect to backend server.")
        return

    # ── Budget vs Actual ──────────────────────────────────────
    st.markdown("### 📊 This Month's Budget vs Actual")

    for item in data:
        col1, col2 = st.columns([3, 1])
        with col1:
            label = f"{item['category']}"
            if item['over_budget']:
                label += " 🚨 Over budget!"
            st.markdown(f"**{label}**")
            progress = min(item['percentage'] / 100, 1.0)
            st.progress(progress)
        with col2:
            st.markdown(f"${item['spent']:,.2f} / ${item['budget_limit']:,.2f}")
            color = "red" if item['over_budget'] else "gray"
            st.markdown(f"<span style='color:{color}; font-size:13px'>{item['percentage']}% used</span>",
                       unsafe_allow_html=True)
        st.markdown("")

    st.divider()

    # ── Set / Update Budget ───────────────────────────────────
    st.markdown("### ✏️ Set Budget Limit")

    categories = ["Food", "Rent", "Shopping", "Entertainment", "Other"]
    existing = {item["category"]: item["budget_limit"] for item in data}

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        selected_cat = st.selectbox("Category", categories)
    with col2:
        current_limit = existing.get(selected_cat, 0.0)
        new_limit = st.number_input("Budget Limit ($)", min_value=0.0,
                                    value=float(current_limit), step=50.0)
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Save", use_container_width=True):
            payload = {"category": selected_cat, "budget_limit": new_limit}
            r = requests.post(f"{API_URL}/budgets/", json=payload)
            if r.status_code == 200:
                st.success(f"Budget for {selected_cat} updated!")
                st.rerun()
            else:
                st.error("Failed to update budget.")