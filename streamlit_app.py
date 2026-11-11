
import streamlit as st
import yfinance as yf

# Page settings
st.set_page_config(
    page_title="Financial Performance Analyzer",
    layout="wide"
)

# App title
st.title("Financial Performance Analyzer")

st.write(
    "Analyze the financial performance of public companies."
)

# User enters stock ticker
ticker = st.text_input(
    "Enter a stock ticker:",
    value="MSFT"
).strip().upper()

# Analyze button
if st.button("Analyze Company"):

    if not ticker:
        st.warning("Please enter a stock ticker.")

    else:
        with st.spinner("Loading financial data..."):

            try:
                # Connect to Yahoo Finance
                company = yf.Ticker(ticker)

                # Get annual financial statements
                income_statement = company.get_income_stmt(
                    freq="yearly"
                )

                balance_sheet = company.get_balance_sheet(
                    freq="yearly"
                )

                # Check if data exists
                if income_statement.empty or balance_sheet.empty:
                    st.error(
                        "Financial data is unavailable for this ticker."
                    )

                else:
                    st.success(
                        f"Financial data loaded for {ticker}"
                    )

                    # Display the financial statements
                    tab1, tab2 = st.tabs([
                        "Income Statement",
                        "Balance Sheet"
                    ])

                    with tab1:
                        st.subheader("Income Statement")
                        st.dataframe(
                            income_statement,
                            use_container_width=True
                        )

                    with tab2:
                        st.subheader("Balance Sheet")
                        st.dataframe(
                            balance_sheet,
                            use_container_width=True
                        )

            except Exception as e:
                st.error(
                    f"Unable to retrieve financial data: {e}"
                )
