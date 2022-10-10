from multiprocessing.sharedctypes import Value
import plotly.io as pio
import plotly.graph_objects as go
pio.renderers.default='browser'
import streamlit as st
import schedule
import requests
import pandas as pd
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width',250)
import warnings
warnings.filterwarnings('ignore')
import json
import traceback
import time 
import ssl
import os
import numpy as np  # np mean, np random
import time

def gen_candlestick_chart(df: pd.DataFrame):
    layout = go.Layout(title = 'Token Price',xaxis = {'title': 'Timestamp'},yaxis = {'title': 'Price'}) 
    fig = go.Figure(
        layout=layout,
        data=[
            go.Candlestick(
                x = df['timestamp'],
                open = df['open'], 
                high = df['high'],
                low = df['low'],
                close = df['close'],
                name = 'Candlestick chart')])
    return fig

#blackmagic for SSL to skip cert check on API calls
ssl._create_default_https_context = ssl._create_unverified_context

st.set_page_config(layout='wide',page_title="Leyens_OS",page_icon="✅",)
root, dirs, files = next(os.walk(f'{os.getcwd()}\\tokenlogs\\'))
logpath = f'{os.getcwd()}\\tokenlogs\\'
#BUILDING WEBPAGE
st.sidebar.header("TRADER ONLEYEN")
token_choices = dirs
token_endpoint = st.sidebar.selectbox("Choose a token", token_choices)
system_choices = ["Current-Price","Graphs",'Config']
system_endpoint = st.sidebar.selectbox("Choose a View", system_choices)
    
with st.sidebar:
    st.write(f'Welcome Human.')
if (system_endpoint == "Current-Price"):
    st.title(f"LEYENS_OS - {system_endpoint}")
    #display Table
    # creating a single-element container.
    holder = st.empty()
    for i in range(200):
        with holder.container():
            pricing_table = st.container()
            with pricing_table.container():
                #pull in current pricing from CSV and show the last 10, this will refresh on the sleep interval
                current_pricing = pd.read_csv(f"{logpath}{token_endpoint}\\{token_endpoint}_price_ticker.csv").tail(10)
                st.markdown("### Current Price Data")
                st.dataframe(current_pricing)
                time.sleep(1)
                
if (system_endpoint == "Graphs"):
    st.title(f"LEYENS_OS - {system_endpoint}")
    #display Table
    # creating a single-element container.
    st.subheader("Generation can take a LONG time if you have large amounts of candle data.")
    holder = st.empty()
    with holder.container():
        candlesticks_5min = st.container()
        candlesticks_1min = st.container()
        with candlesticks_5min.container():
            try:
                min_df = pd.read_csv(f"{os.getcwd()}\\tokenlogs\\{token_endpoint}\\{token_endpoint}_5min_Candle_data.csv")
                fig = gen_candlestick_chart(min_df)
                st.markdown("### 5 Minute Graph")
                st.write(fig)
            except:
                st.write("Could not find tokenlogs folder + CSV data, verify folder exists.")
        with candlesticks_5min.container():
            try:
                #get candlestick data from csv and attempt to graph it
                min_df = pd.read_csv(f"{os.getcwd()}\\tokenlogs\\{token_endpoint}\\{token_endpoint}_1min_Candle_data.csv")
                fig = gen_candlestick_chart(min_df)
                st.markdown("### 1 Minute Graph")
                st.write(fig)
            except:
                st.write("Could not find tokenlogs folder + CSV data, verify folder exists.")
            
if (system_endpoint == "Config"):
    #onchange Function to update JSON
    def write_change(config):
        with open("ATS_config.json", "w") as jsonFile:
            json.dump(config, jsonFile,indent=2)
            
    st.title(f"LEYENS_OS - Config")
    st.text("*Hit Enter after updating to save.")
    #load config
    with open("ATS_config.json") as ATS_config:
        config = json.load(ATS_config)
    st.subheader("Base Config")
    #loop through fields in config json
    for field in list(config['base_config']):
        #if the fields change update them the base so we can write back to the json file
        if "True" in str(config['base_config'][field]):
            config['base_config'][field] = st.selectbox(f"{field}",('True', 'False'),index=0,on_change=write_change(config))
        elif "False" in str(config['base_config'][field]):
            config['base_config'][field] = st.selectbox(f"{field}",('True', 'False'),index=1,on_change=write_change(config))
        else:
            config['base_config'][field]= st.text_input(label=f"{field}",value=config['base_config'][field],key=field,on_change=write_change(config))
    st.subheader("Strat Config")
    #write changes back to json file
    for field in list(config['strat_config']):
        config['strat_config'][field] = st.text_input(label=f"{field}",value=config['strat_config'][field],key=field,on_change=write_change(config))
    st.subheader("Telegram Config")
    for field in list(config['telegram_config']):
        config['telegram_config'][field]= st.text_input(label=f"{field}",value=config['telegram_config'][field],key=field,on_change=write_change(config))
    st.subheader("Yahoo Finance Ticker")
    for field in list(config['yahoo_finance']):
        config['yahoo_finance'][field]= st.text_input(label=f"{field}",value=config['yahoo_finance'][field],key=field,on_change=write_change(config))