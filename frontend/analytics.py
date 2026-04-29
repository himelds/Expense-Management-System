import streamlit as st
from datetime import datetime, date
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

API_URL = "http://localhost:8000"

def analytics_tab():
    st.markdown("## 📊 Analytics")

    subtab1, subtab2 = st.tabs(["📂 By Category", "📅 By Month"])

    # ════════════════════════════════════════════════════════
    # SUB-TAB 1: By Category
    # ════════════════════════════════════════════════════════
    with subtab1:
        st.markdown("### 📂 Expense Breakdown by Category")

        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            start_date = st.date_input("Start Date", date(2024, 8, 1), key="cat_start")
        with col2:
            end_date = st.date_input("End Date", date.today(), key="cat_end")
        with col3:
            st.markdown("<br>", unsafe_allow_html=True)
            analyse = st.button("Analyse", use_container_width=True, key="cat_btn")

        if analyse:
            payload = {
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date":   end_date.strftime("%Y-%m-%d")
            }
            resp = requests.post(f"{API_URL}/analytics/", json=payload)
            if resp.status_code != 200:
                st.error("Failed to load analytics.")
                return

            response = resp.json()
            if not response:
                st.info("No data found for the selected date range.")
                return

            data = {
                "Category":   list(response.keys()),
                "Total":      [response[c]["total"] for c in response],
                "Percentage": [response[c]["percentage"] for c in response]
            }
            df = pd.DataFrame(data).sort_values("Total", ascending=False)

            # ── Summary metrics ───────────────────────────
            total_spent = df["Total"].sum()
            top_cat     = df.iloc[0]["Category"]
            top_pct     = df.iloc[0]["Percentage"]

            m1, m2, m3 = st.columns(3)
            m1.metric("💰 Total Spent",    f"${total_spent:,.2f}")
            m2.metric("🏆 Top Category",   top_cat)
            m3.metric("📊 Top %",          f"{top_pct:.1f}%")

            st.divider()

            # ── Charts side by side ───────────────────────
            chart1, chart2 = st.columns([3, 2])

            with chart1:
                st.markdown("**Spending by Category**")
                fig_bar = px.bar(
                    df, x="Category", y="Total",
                    color="Category",
                    color_discrete_sequence=px.colors.qualitative.Set2,
                    text=df["Total"].map("${:,.0f}".format)
                )
                fig_bar.update_layout(
                    margin=dict(l=0,r=0,t=10,b=0), height=300,
                    showlegend=False,
                    plot_bgcolor="white", paper_bgcolor="white",
                    xaxis=dict(title=""), yaxis=dict(title="Amount ($)", showgrid=True, gridcolor="#f0f2f5")
                )
                fig_bar.update_traces(textposition="outside")
                st.plotly_chart(fig_bar, use_container_width=True)

            with chart2:
                st.markdown("**Category Share**")
                fig_pie = go.Figure(go.Pie(
                    labels=df["Category"], values=df["Total"],
                    hole=0.5, textinfo="percent",
                    hovertemplate="<b>%{label}</b><br>$%{value:,.2f}<extra></extra>",
                    marker=dict(line=dict(color="white", width=2))
                ))
                fig_pie.update_layout(
                    margin=dict(l=0,r=0,t=10,b=0), height=300,
                    showlegend=True,
                    legend=dict(orientation="v", font=dict(size=11)),
                    plot_bgcolor="white", paper_bgcolor="white"
                )
                st.plotly_chart(fig_pie, use_container_width=True)

            st.divider()

            # ── Table ─────────────────────────────────────
            st.markdown("**Detailed Breakdown**")
            df_display = df.copy()
            df_display["Total"]      = df_display["Total"].map("${:,.2f}".format)
            df_display["Percentage"] = df_display["Percentage"].map("{:.1f}%".format)
            df_display = df_display.reset_index(drop=True)
            df_display.index += 1
            st.dataframe(df_display, use_container_width=True)

    # ════════════════════════════════════════════════════════
    # SUB-TAB 2: By Month
    # ════════════════════════════════════════════════════════
    with subtab2:
        st.markdown("### 📅 Expense Breakdown by Month")

        try:
            resp = requests.get(f"{API_URL}/monthly_summary/")
            monthly = resp.json()
        except:
            st.error("Failed to load monthly summary.")
            return

        if not monthly:
            st.info("No monthly data available.")
            return

        df_m = pd.DataFrame(monthly)

        # ── Year filter ───────────────────────────────────────
        # শুধু যে বছরের ডাটা আছে সেই বছরগুলো দেখাবে
        years = sorted(df_m["expense_year"].unique().tolist(), reverse=True)
        selected_year = st.selectbox("📅 Select Year", years)

        # Filter by selected year
        df_filtered = df_m[df_m["expense_year"] == selected_year].copy()
        df_filtered = df_filtered.sort_values("expense_month")

        # ── Summary metrics ───────────────────────────────────
        total_all  = df_filtered["total"].sum()
        avg_month  = df_filtered["total"].mean()
        best_row   = df_filtered.loc[df_filtered["total"].idxmax()]
        worst_row  = df_filtered.loc[df_filtered["total"].idxmin()]

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("💰 Total",           f"${total_all:,.2f}")
        m2.metric("📊 Monthly Average",  f"${avg_month:,.2f}")
        m3.metric("🏆 Highest Month",    best_row["month_name"],  f"${best_row['total']:,.2f}")
        m4.metric("📉 Lowest Month",     worst_row["month_name"], f"${worst_row['total']:,.2f}")

        st.divider()

        # ── Charts ────────────────────────────────────────────
        chart1, chart2 = st.columns([3, 2])

        with chart1:
            st.markdown("**Monthly Spending**")
            fig_bar = go.Figure()
            fig_bar.add_trace(go.Bar(
                x=df_filtered["month_name"],
                y=df_filtered["total"],
                marker_color="#1a73e8",
                text=df_filtered["total"].map("${:,.0f}".format),
                textposition="outside",
                hovertemplate="<b>%{x}</b><br>$%{y:,.2f}<extra></extra>"
            ))
            fig_bar.update_layout(
                margin=dict(l=0,r=0,t=30,b=0), height=320,
                plot_bgcolor="white", paper_bgcolor="white",
                xaxis=dict(title="", tickangle=0),
                yaxis=dict(
                    title="Amount ($)", showgrid=True,
                    gridcolor="#f0f2f5",
                    range=[0, df_filtered["total"].max() * 1.2]
                )
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        with chart2:
            st.markdown("**Month Share**")
            fig_pie = go.Figure(go.Pie(
                labels=df_filtered["month_name"],
                values=df_filtered["total"],
                hole=0.5, textinfo="percent",
                hovertemplate="<b>%{label}</b><br>$%{value:,.2f}<extra></extra>",
                marker=dict(line=dict(color="white", width=2))
            ))
            fig_pie.update_layout(
                margin=dict(l=0,r=0,t=10,b=0), height=320,
                showlegend=True,
                legend=dict(orientation="v", font=dict(size=11)),
                plot_bgcolor="white", paper_bgcolor="white"
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        st.divider()

        # ── Table ─────────────────────────────────────────────
        st.markdown(f"**{selected_year} — Monthly Summary**")
        df_table = df_filtered[["month_name", "total", "transactions"]].copy()
        df_table.columns = ["Month", "Total Spent", "Transactions"]
        df_table = df_filtered[["expense_month", "month_name", "total", "transactions"]].copy()
        df_table.columns = ["Month Number", "Month", "Total Spent", "Transactions"]
        df_table = df_table.sort_values("Month Number").reset_index(drop=True)
        df_table = df_table.drop(columns=["Month Number"])
        df_table.index += 1

        # Format AFTER calculating totals
        df_table["Total Spent"] = df_table["Total Spent"].map("${:,.2f}".format)
        st.dataframe(df_table, use_container_width=True)

        # Footer
        t1, t2, _ = st.columns([2, 2, 3])
        t1.markdown(f"**Total: ${total_all:,.2f}**")
        t2.markdown(f"**Transactions: {int(df_filtered['transactions'].sum())}**")