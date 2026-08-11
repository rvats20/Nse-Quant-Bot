import streamlit as st
from data_fetcher import fetch_option_chain
from lottery_calls import find_lottery_calls
from gex_engine import compute_gex,find_gamma_walls
from config import SPOT_PRICE

st.title("NSE Quant Bot Ultimate Dashboard")

df=fetch_option_chain()

st.subheader("Option Chain Snapshot")
st.dataframe(df.head(20))

lottery=find_lottery_calls(df,SPOT_PRICE)

st.subheader("High Risk Calls")
st.write(lottery)

gex=compute_gex(df)

st.subheader("Gamma Exposure Levels")
st.dataframe(gex.head())

walls=find_gamma_walls(gex)

st.subheader("Gamma Walls (Potential Pin Levels)")
st.dataframe(walls)
