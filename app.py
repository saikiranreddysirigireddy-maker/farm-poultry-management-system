import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, timedelta
from database import (
    init_db, add_batch, get_batches, record_mortality,
    add_feed_purchase, record_feed_usage, get_feed_stock,
    record_eggs, get_egg_records, add_vaccination, get_vaccinations,
    record_sale, get_sales, get_summary, get_expenses, add_expense,
    get_mortality_records
)

st.set_page_config(page_title="Farm Poultry Management", page_icon="🐔", layout="wide")
init_db()

st.title("🐔 Farm Poultry Management System")
st.caption("Manage poultry batches, mortality, feed, egg production, vaccinations, sales, and expenses.")

pages = [
    "Dashboard", "Poultry Batches", "Feed Inventory",
    "Egg Production", "Vaccination Schedule", "Sales & Expenses"
]
page = st.sidebar.selectbox("Navigation", pages)

def money(value):
    return f"₹{float(value or 0):,.2f}"

def show_table(rows):
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No records yet.")

if page == "Dashboard":
    summary = get_summary()
    cols = st.columns(4)
    cols[0].metric("Live Birds", f"{summary['live_birds']:,}")
    cols[1].metric("Eggs Recorded Today", f"{summary['eggs_today']:,}")
    cols[2].metric("Feed in Stock", f"{summary['feed_stock']:.1f} kg")
    cols[3].metric("Total Sales", money(summary["total_sales"]))

    batches = get_batches()
    st.subheader("Current Poultry Batches")
    if batches:
        st.dataframe(pd.DataFrame(batches), use_container_width=True, hide_index=True)
    else:
        st.info("Register your first batch in Poultry Batches.")

    left, right = st.columns(2)
    with left:
        st.subheader("Recent Egg Production")
        eggs = get_egg_records(limit=100)
        if eggs:
            df = pd.DataFrame(eggs)
            df["production_date"] = pd.to_datetime(df["production_date"])
            daily = df.groupby("production_date", as_index=False)["egg_count"].sum()
            st.plotly_chart(px.line(daily, x="production_date", y="egg_count", markers=True,
                                    title="Eggs recorded by date"), use_container_width=True)
        else:
            st.info("Record egg production to see a chart.")
    with right:
        st.subheader("Sales by Product")
        sales = get_sales()
        if sales:
            df = pd.DataFrame(sales)
            chart = df.groupby("product", as_index=False)["amount"].sum()
            st.plotly_chart(px.pie(chart, names="product", values="amount", title="Sales revenue"),
                            use_container_width=True)
        else:
            st.info("Record sales to see a chart.")

    sales_total = sum(float(x["amount"]) for x in get_sales())
    expenses_total = sum(float(x["amount"]) for x in get_expenses())
    c1, c2, c3 = st.columns(3)
    c1.metric("Recorded Revenue", money(sales_total))
    c2.metric("Recorded Expenses", money(expenses_total))
    c3.metric("Revenue − Expenses", money(sales_total - expenses_total))
    st.caption("This is a basic estimate based only on entries recorded in the system.")

elif page == "Poultry Batches":
    st.subheader("Register a Poultry Batch")
    with st.form("batch_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        batch_name = c1.text_input("Batch name", placeholder="e.g. Batch A")
        breed = c2.selectbox("Chicken type", ["Broiler", "Layer", "Country Chicken", "Other"])
        c3, c4 = st.columns(2)
        initial_birds = c3.number_input("Initial number of birds", min_value=1, value=100, step=1)
        arrival_date = c4.date_input("Arrival date", value=date.today())
        notes = st.text_input("Notes (optional)")
        submitted = st.form_submit_button("Save batch", type="primary")
        if submitted:
            if not batch_name.strip():
                st.error("Please enter a batch name.")
            else:
                add_batch(batch_name.strip(), breed, int(initial_birds), arrival_date.isoformat(), notes.strip())
                st.success("Poultry batch saved.")
                st.rerun()

    batches = get_batches()
    st.subheader("Record Bird Mortality")
    if batches:
        options = {f"{b['batch_name']} — {b['breed']} (live: {b['live_birds']})": b for b in batches}
        with st.form("mortality_form", clear_on_submit=True):
            selected = st.selectbox("Select batch", list(options.keys()))
            count = st.number_input("Number of birds lost", min_value=1, value=1, step=1)
            loss_date = st.date_input("Mortality date", value=date.today())
            reason = st.text_input("Reason / notes (optional)")
            if st.form_submit_button("Record mortality"):
                batch = options[selected]
                if count > batch["live_birds"]:
                    st.error(f"Only {batch['live_birds']} live birds remain in this batch.")
                else:
                    record_mortality(batch["id"], int(count), loss_date.isoformat(), reason.strip())
                    st.success("Mortality recorded.")
                    st.rerun()
    else:
        st.info("Add a batch before recording mortality.")

    st.subheader("All Poultry Batches")
    show_table(get_batches())
    st.subheader("Mortality History")
    show_table(get_mortality_records())

elif page == "Feed Inventory":
    st.subheader("Add Feed Purchase")
    with st.form("feed_purchase", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        feed_type = c1.text_input("Feed type", placeholder="e.g. Starter feed")
        quantity = c2.number_input("Quantity (kg)", min_value=0.1, value=25.0, step=1.0)
        cost = c3.number_input("Total cost (₹)", min_value=0.0, value=1000.0, step=50.0)
        purchase_date = st.date_input("Purchase date", value=date.today())
        if st.form_submit_button("Save purchase", type="primary"):
            if not feed_type.strip():
                st.error("Enter a feed type.")
            else:
                add_feed_purchase(feed_type.strip(), quantity, cost, purchase_date.isoformat())
                st.success("Feed purchase saved.")
                st.rerun()

    st.subheader("Record Feed Consumption")
    stock = get_feed_stock()
    if stock:
        feed_options = {f"{x['feed_type']} — {x['quantity_kg']:.1f} kg available": x for x in stock if x["quantity_kg"] > 0}
        if feed_options:
            with st.form("feed_usage", clear_on_submit=True):
                selected = st.selectbox("Feed type", list(feed_options.keys()))
                used = st.number_input("Quantity used (kg)", min_value=0.1, value=1.0, step=0.5)
                used_date = st.date_input("Usage date", value=date.today())
                notes = st.text_input("Notes (optional)")
                if st.form_submit_button("Record consumption"):
                    item = feed_options[selected]
                    if used > item["quantity_kg"]:
                        st.error(f"Only {item['quantity_kg']:.1f} kg is available.")
                    else:
                        record_feed_usage(item["feed_type"], used, used_date.isoformat(), notes.strip())
                        st.success("Feed consumption saved.")
                        st.rerun()
        else:
            st.info("No feed stock available to consume.")
    else:
        st.info("Add a feed purchase before recording consumption.")

    st.subheader("Available Feed Stock")
    show_table(get_feed_stock())

elif page == "Egg Production":
    st.subheader("Record Daily Egg Production")
    batches = get_batches()
    if batches:
        options = {f"{b['batch_name']} — {b['breed']}": b["id"] for b in batches}
        with st.form("egg_form", clear_on_submit=True):
            selected = st.selectbox("Poultry batch", list(options.keys()))
            production_date = st.date_input("Production date", value=date.today())
            egg_count = st.number_input("Eggs collected", min_value=0, value=0, step=1)
            broken = st.number_input("Broken / damaged eggs", min_value=0, value=0, step=1)
            notes = st.text_input("Notes (optional)")
            if st.form_submit_button("Save egg record", type="primary"):
                if broken > egg_count:
                    st.error("Broken eggs cannot exceed total eggs collected.")
                else:
                    record_eggs(options[selected], production_date.isoformat(), int(egg_count), int(broken), notes.strip())
                    st.success("Egg production saved.")
                    st.rerun()
    else:
        st.warning("Register a poultry batch first.")
    st.subheader("Egg Production History")
    show_table(get_egg_records())

elif page == "Vaccination Schedule":
    st.subheader("Schedule Vaccination")
    batches = get_batches()
    batch_options = {"All batches": None}
    batch_options.update({f"{b['batch_name']} — {b['breed']}": b["id"] for b in batches})
    with st.form("vaccination_form", clear_on_submit=True):
        selected = st.selectbox("Batch", list(batch_options.keys()))
        vaccine = st.text_input("Vaccine name")
        due_date = st.date_input("Due date", value=date.today() + timedelta(days=7))
        status = st.selectbox("Status", ["Scheduled", "Completed"])
        notes = st.text_input("Notes / dosage (optional)")
        if st.form_submit_button("Save vaccination", type="primary"):
            if not vaccine.strip():
                st.error("Enter a vaccine name.")
            else:
                add_vaccination(batch_options[selected], vaccine.strip(), due_date.isoformat(), status, notes.strip())
                st.success("Vaccination saved.")
                st.rerun()

    st.subheader("Vaccination Records")
    vaccinations = get_vaccinations()
    if vaccinations:
        df = pd.DataFrame(vaccinations)
        df["due_date"] = pd.to_datetime(df["due_date"]).dt.date
        today = date.today()
        df["Reminder"] = df.apply(
            lambda row: "Overdue" if row["status"] != "Completed" and row["due_date"] < today
            else ("Due today" if row["status"] != "Completed" and row["due_date"] == today else ""),
            axis=1
        )
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No vaccination records yet.")
    st.caption("Confirm vaccine choice and timing with a qualified poultry veterinarian.")

elif page == "Sales & Expenses":
    st.subheader("Record a Sale")
    with st.form("sale_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        product = c1.selectbox("Product", ["Eggs", "Live birds", "Manure", "Other"])
        quantity = c2.number_input("Quantity sold", min_value=0.1, value=10.0, step=1.0)
        c3, c4 = st.columns(2)
        unit = c3.text_input("Unit", value="pieces")
        amount = c4.number_input("Total sale amount (₹)", min_value=0.0, value=500.0, step=50.0)
        sale_date = st.date_input("Sale date", value=date.today())
        buyer = st.text_input("Buyer / customer (optional)")
        if st.form_submit_button("Save sale", type="primary"):
            record_sale(product, quantity, unit.strip(), amount, sale_date.isoformat(), buyer.strip())
            st.success("Sale saved.")
            st.rerun()

    st.subheader("Record an Expense")
    with st.form("expense_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        category = c1.selectbox("Expense category", ["Feed", "Medicine / vaccination", "Labor", "Utilities", "Transport", "Equipment", "Other"])
        expense_amount = c2.number_input("Amount (₹)", min_value=0.0, value=100.0, step=50.0)
        expense_date = st.date_input("Expense date", value=date.today(), key="expense_date")
        description = st.text_input("Description")
        if st.form_submit_button("Save expense"):
            if expense_amount <= 0:
                st.error("Enter an amount greater than zero.")
            else:
                add_expense(category, expense_amount, expense_date.isoformat(), description.strip())
                st.success("Expense saved.")
                st.rerun()

    sales = get_sales()
    expenses = get_expenses()
    sales_total = sum(float(x["amount"]) for x in sales)
    expenses_total = sum(float(x["amount"]) for x in expenses)
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Revenue", money(sales_total))
    c2.metric("Recorded Expenses", money(expenses_total))
    c3.metric("Revenue − Expenses", money(sales_total - expenses_total))
    st.caption("This estimate includes only entries recorded in this application; it is not a complete accounting statement.")
    st.subheader("Sales History")
    show_table(sales)
    st.subheader("Expense History")
    show_table(expenses)
