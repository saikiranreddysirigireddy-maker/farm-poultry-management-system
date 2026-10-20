# Farm Poultry Management System

A local web application for recording poultry farm operations, built with Python, SQLite, Streamlit, Pandas, and Plotly.

## Features

- Dashboard with live bird count, today's recorded egg count, feed stock, sales, and charts
- Poultry batch registration and mortality tracking
- Feed purchase, usage, and available-stock tracking
- Daily egg production and broken egg records
- Vaccination schedule with due and overdue indicators
- Sales and expenses, including a basic revenue-minus-expenses estimate

## Requirements

- Python 3.10 or newer recommended
- pip

## Run locally

Open a terminal in this folder and run:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open the local URL printed by Streamlit, usually `http://localhost:8501`.

The SQLite database (`poultry.db`) is created automatically and is intentionally excluded from Git by `.gitignore`, so local farm records are not published to GitHub.

## Notes

- This initial version is intended for local demonstration and does not include authentication or cloud synchronization.
- Vaccination plans should be confirmed with a qualified poultry veterinarian.
- Revenue minus expenses is a basic estimate based on entered records, not a complete accounting statement.
