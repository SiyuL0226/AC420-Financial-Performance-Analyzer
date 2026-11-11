import streamlit as st

st.set_page_config(
    page_title="Financial Performance Analyzer",
    layout="wide"
)

st.title("Financial Performance Analyzer")

ticker = st.text_input(
    "Enter a stock ticker:",
    value="MSFT"
).upper()

if st.button("Analyze Company"):
    st.write(f"Analyzing {ticker}")
