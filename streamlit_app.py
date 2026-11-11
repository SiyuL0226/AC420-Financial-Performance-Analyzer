
import streamlit as st

# Set up the webpage
st.set_page_config(
    page_title="Financial Performance Analyzer",
    layout="wide"
)

# Display the title
st.title("Financial Performance Analyzer")

st.write("Analyze the financial performance of public companies.")

# Let the user enter a stock ticker
ticker = st.text_input(
    "Enter a stock ticker:",
    value="MSFT"
).strip().upper()

# Create the Analyze button
if st.button("Analyze Company"):
    if ticker:
        st.success(f"Analyzing {ticker}")
    else:
        st.warning("Please enter a stock ticker.")
