import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

API_URL = "http://localhost:8000"

ICONS = {
    "Food":"🍔","Rent":"🏠","Shopping":"🛍️","Entertainment":"🎬",
    "Other":"💡","Transport":"🚗","Healthcare":"💊",
    "Travel":"✈️","Gym":"💪","Groceries":"🛒"
}

def home_tab():

    # ── Fetch data ────────────────────────────────────────────
    try:
        summary_resp  = requests.get(f"{API_URL}/home_summary/")
        budget_resp   = requests.get(f"{API_URL}/budgets/vs_actual/")
        category_resp = requests.post(f"{API_URL}/analytics/", json={
            "start_date": pd.Timestamp.now().replace(day=1).strftime("%Y-%m-%d"),
            "end_date":   pd.Timestamp.now().strftime("%Y-%m-%d")
        })
        if any(r.status_code != 200 for r in [summary_resp, budget_resp]):
            st.error("Failed to load dashboard data.")
            return
        summary       = summary_resp.json()
        budgets       = budget_resp.json()
        category_data = category_resp.json() if category_resp.status_code == 200 else {}
    except requests.exceptions.ConnectionError:
        st.error("⚠️ Cannot connect to backend server.")
        return

    st.markdown("## 🏠 Dashboard")

    # ── ROW 1: Metrics ────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Total Spent",     f"${summary['total_this_month']:,.2f}", "Latest month")
    c2.metric("🧾 Transactions",    str(summary['total_transactions']),     "Latest month")
    c3.metric("💸 Largest Expense", f"${summary['largest_expense']:,.2f}",  "Single transaction")
    c4.metric("🏆 Top Category",    summary['top_category'],
                                     f"${summary['top_category_amount']:,.2f} spent")

    st.divider()

    # ── ROW 2: Trend + Donut ──────────────────────────────────
    col_l, col_r = st.columns([3, 2])

    with col_l:
        st.markdown("#### 📈 Spending Trend")

        if "trend_period" not in st.session_state:
            st.session_state.trend_period = "month"

        b1, b2, b3 = st.columns(3)
        if b1.button("Week",    use_container_width=True,
                     type="primary" if st.session_state.trend_period=="week" else "secondary"):
            st.session_state.trend_period = "week"; st.rerun()
        if b2.button("Month",   use_container_width=True,
                     type="primary" if st.session_state.trend_period=="month" else "secondary"):
            st.session_state.trend_period = "month"; st.rerun()
        if b3.button("Quarter", use_container_width=True,
                     type="primary" if st.session_state.trend_period=="quarter" else "secondary"):
            st.session_state.trend_period = "quarter"; st.rerun()

        try:
            tr = requests.get(f"{API_URL}/spending_trend/",
                              params={"period": st.session_state.trend_period})
            trend = tr.json() if tr.status_code == 200 else []
        except:
            trend = []

        period_labels = {"week":"Last 7 Days","month":"Last 30 Days","quarter":"Last 90 Days"}

        if trend:
            df = pd.DataFrame(trend)
            df["expense_date"] = pd.to_datetime(df["expense_date"]).dt.normalize()
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df["expense_date"], y=df["daily_total"],
                mode="lines+markers",
                line=dict(color="#1a73e8", width=2.5),
                marker=dict(size=7, color="#1a73e8", line=dict(color="white", width=2)),
                fill="tozeroy", fillcolor="rgba(26,115,232,0.07)",
                hovertemplate="<b>%{x|%b %d}</b><br>$%{y:,.2f}<extra></extra>"
            ))
            fig.update_layout(
                margin=dict(l=0,r=0,t=5,b=0), height=250,
                xaxis=dict(showgrid=False, title="", type="date", tickformat="%b %d", nticks=7),
                yaxis=dict(showgrid=True, gridcolor="#f0f2f5", tickprefix="$", title=""),
                plot_bgcolor="white", paper_bgcolor="white", hovermode="x unified"
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption(f"📅 {period_labels[st.session_state.trend_period]}")
        else:
            st.info(f"No data for {period_labels[st.session_state.trend_period]}.")

    with col_r:
        st.markdown("#### 🍩 Key Categories")
        if category_data:
            labels_list = list(category_data.keys())
            values_list = [category_data[c]["total"] for c in labels_list]
            colors = ["#1a73e8","#34a853","#fbbc04","#ea4335","#9c27b0","#00acc1","#f57c00"]
            fig2 = go.Figure(go.Pie(
                labels=labels_list, values=values_list, hole=0.52,
                textinfo="percent",
                hovertemplate="<b>%{label}</b><br>$%{value:,.2f}<extra></extra>",
                marker=dict(colors=colors[:len(labels_list)], line=dict(color="white", width=2))
            ))
            fig2.update_layout(
                margin=dict(l=0,r=0,t=10,b=0), height=310,
                showlegend=True,
                legend=dict(orientation="v", x=1.02, y=0.5, font=dict(size=11)),
                plot_bgcolor="white", paper_bgcolor="white"
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No category data for this month.")

    st.divider()

    # ── ROW 3: Recent Transactions + Budgets ──────────────────
    col_bl, col_br = st.columns([3, 2])

    with col_bl:
        st.markdown("#### 🕐 Recent Transactions")
        recent = summary.get("recent_expenses", [])[:5]
        if recent:
            for exp in recent:
                icon = ICONS.get(exp["category"], "💰")
                c_left, c_right = st.columns([4, 1])
                with c_left:
                    st.markdown(f"**{icon} {exp['notes'] or exp['category']}**")
                    st.caption(f"{exp['category']} · {exp['expense_date']}")
                with c_right:
                    st.markdown(f"**:red[-${exp['amount']:,.2f}]**")
                st.divider()
        else:
            st.info("No recent transactions.")

    with col_br:
        st.markdown("#### 💰 Budgets at a Glance")
        if budgets:
            for item in budgets:
                pct = item["percentage"]
                if item["over_budget"]:
                    label = f"🔴 {item['category']} — Over budget!"
                elif pct >= 80:
                    label = f"🟡 {item['category']} — {pct:.0f}% used"
                else:
                    label = f"🟢 {item['category']} — {pct:.0f}% used"
                st.markdown(f"**{label}**")
                st.caption(f"${item['spent']:,.0f} spent of ${item['budget_limit']:,.0f}")
                st.progress(min(pct / 100, 1.0))
        else:
            st.info("No budgets configured.")