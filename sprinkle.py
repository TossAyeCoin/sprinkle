import schedule
import requests
import pandas as pd
import pandas_ta as ta
#from main import InputToken_address
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
import warnings
warnings.filterwarnings('ignore')
import random
import numpy as np
from datetime import datetime
import time
from decimal import Decimal
from web3 import Web3
import threading
import logging
from os.path import exists
import traceback
import json
import yfinance as yf
import os
import csv 

#RUNNER: nohup python3 -u sprinkle.py -d15 -w512 &
#first Load from Config
with open("ATS_config.json") as ATS_config:
    config = json.load(ATS_config)
#######################################################
#########              SETUP POSITION           #######
#######################################################
#setup Position
buy_counter = 0
#stop Loss in Percent
stop_loss_percent = config['base_config']['stop_loss_percent']
stop_loss_price = 0
#Take Gain Percentage
gain_percent = config['base_config']['gain_percent']
buy_amount = config['base_config']['buy_amount']
take_profit_price = 0 
buy_price = 0
current_price = 0
#Buy Amount in BNB 
gain_percent = config['base_config']['gain_percent']
defer_counter = 0
defer_percent = config['base_config']['defer_percent']
bot_profit = 0
supertrendFlip = False
macdCross = False
approveCounter = 0
neg_trend_sell = False
enable_neg_trend_sell = config['base_config']['enable_neg_trend_sell']
slippage = config['base_config']['slippage']
halt_trading = config['base_config']['halt_trading']
limit_buy = config['base_config']['limit_buy']
limit_price = config['base_config']['limit_price']
pivot_price = 0
waitTime = config['base_config']['waitTime']
#Token2Trade
InputToken_address = Web3.toChecksumAddress(config['base_config']['InputToken_address'])
#Wallet Details
address = Web3.toChecksumAddress(config['base_config']['address'])
private_key = config['base_config']['private_key']
#setting Up Strat Data
sell_now = config['base_config']['sell_now']
buy_now = config['base_config']['buy_now']
in_position = config['base_config']['in_position']
#strat configs
supertrend_p1 = config['strat_config']['supertrend_p1']
atr1 = config['strat_config']['atr1']
supertrend_p2 = config['strat_config']['supertrend_p2']
atr2 = config['strat_config']['atr2']
supertrend_p3 = config['strat_config']['supertrend_p3']
atr3 = config['strat_config']['atr3']
macd_fast = config['strat_config']['macd_fast']
macd_slow = config['strat_config']['macd_slow']
macd_signal = config['strat_config']['macd_signal']
srsi_p = config['strat_config']['srsi_p']
srsi_k = config['strat_config']['srsi_k']
srsi_d = config['strat_config']['srsi_d']
adx_length = config['strat_config']['adx_length']
#telegram Configs
telegram_token = config['telegram_config']['token']
telegram_name = config['telegram_config']['channel_name']
#yahoo finance ticker, needed to pull in longer term API data
yfticker = config['yahoo_finance']['yfticker']

#Reload Config. Allows for program Changes while running
def loadConfig(filename):
    global stop_loss_percent,gain_percent,buy_amount,InputToken_address,address,private_key,sell_now,buy_now,enable_neg_trend_sell,base_coin,supertrend_p1,atr1,supertrend_p2,atr2,supertrend_p3,atr3,macd_fast,macd_slow,macd_signal,srsi_p,srsi_k,srsi_d,adx_length,slippage,halt_trading,limit_buy,limit_price,waitTime,telegram_name,telegram_token,yfticker,in_position
    try:
        with open(filename) as ATS_config:
            config = json.load(ATS_config)
        #Reload Variables
        #Base Config
        stop_loss_percent = config['base_config']['stop_loss_percent']
        gain_percent = config['base_config']['gain_percent']
        buy_amount = config['base_config']['buy_amount']
        InputToken_address = Web3.toChecksumAddress(config['base_config']['InputToken_address'])
        address = Web3.toChecksumAddress(config['base_config']['address'])
        private_key = config['base_config']['private_key']
        sell_now = config['base_config']['sell_now']
        buy_now = config['base_config']['buy_now']
        base_coin = config['base_config']['base_coin']
        enable_neg_trend_sell = config['base_config']['enable_neg_trend_sell']
        slippage = config['base_config']['slippage']
        halt_trading = config['base_config']['halt_trading']
        limit_buy = config['base_config']['limit_buy']
        limit_price = config['base_config']['limit_price']
        waitTime = config['base_config']['waitTime']
        in_position = config['base_config']['in_position']
        #Strat Config
        supertrend_p1 = config['strat_config']['supertrend_p1']
        atr1 = config['strat_config']['atr1']
        supertrend_p2 = config['strat_config']['supertrend_p2']
        atr2 = config['strat_config']['atr2']
        supertrend_p3 = config['strat_config']['supertrend_p3']
        atr3 = config['strat_config']['atr3']
        macd_fast = config['strat_config']['macd_fast']
        macd_slow = config['strat_config']['macd_slow']
        macd_signal = config['strat_config']['macd_signal']
        srsi_p = config['strat_config']['srsi_p']
        srsi_k = config['strat_config']['srsi_k']
        srsi_d = config['strat_config']['srsi_d']
        adx_length = config['strat_config']['adx_length']
        telegram_token = config['telegram_config']['token']
        telegram_name = config['telegram_config']['channel_name']
        yfticker = config['yahoo_finance']['yfticker']
    except Exception as exc:
        print("Failed To Reload Config!")
        print(traceback.format_exc())
        print(exc)

################################################
######              TELEGRAM SETUP          ####
################################################
#will send message on trade execution to telegram channel.
#setup using botfather to get telegram token
def sendMessage(text):
    token = telegram_token
    channel_name = telegram_name
    telAPIurl = "https://api.telegram.org/bot{}/sendMessage".format(token)
    channel_url = telAPIurl + "?chat_id={}&text={}".format(channel_name,text)
    while True:
        try:
            request = requests.post(channel_url)
            if(request.status_code == 200):
                break
            else:
                continue
        except:
            continue

'''
###############################
Strategies
#################################
'''

#calculate True Range
def tr(data):
    data['previous_close'] = data['close'].shift(1)
    data['high-low'] = abs(data['high'] - data['low'])
    data['high-pc'] = abs(data['high'] - data['previous_close'])
    data['low-pc'] = abs(data['low'] - data['previous_close'])
    tr = data[['high-low', 'high-pc', 'low-pc']].max(axis=1)
    return tr

#Calculate Average True Range
def atr(data, period):
    data['tr'] = tr(data)
    atr = data['tr'].rolling(period).mean()
    return atr

#calculate SuperTrend
def supertrend(df, period=30, atr_multiplier=2):
    hl2 = (df['high'] + df['low']) / 2
    df['atr'] = atr(df, period)
    df['upperband'] = hl2 + (atr_multiplier * df['atr'])
    df['lowerband'] = hl2 - (atr_multiplier * df['atr'])
    df['in_uptrend'] = True
    for current in range(1, len(df.index)):
        previous = current - 1

        if df['close'][current] > df['upperband'][previous]:
            df['in_uptrend'][current] = True
        elif df['close'][current] < df['lowerband'][previous]:
            df['in_uptrend'][current] = False
        else:
            df['in_uptrend'][current] = df['in_uptrend'][previous]

            if df['in_uptrend'][current] and df['lowerband'][current] < df['lowerband'][previous]:
                df['lowerband'][current] = df['lowerband'][previous]

            if not df['in_uptrend'][current] and df['upperband'][current] > df['upperband'][previous]:
                df['upperband'][current] = df['upperband'][previous]
        
    return df 

#calculate Triple SuperTrend
def triplesupertrend(df, period1=25, period2 =30, period3 = 35, atr_multiplier1=1, atr_multiplier2=2, atr_multiplier3 = 3):
    hl2 = (df['high'] + df['low']) / 2
    df['atr1'] = atr(df, period1)
    df['atr2'] = atr(df, period2)
    df['atr3'] = atr(df, period3)
    df['upperband1'] = hl2 + (atr_multiplier1 * df['atr1'])
    df['lowerband1'] = hl2 - (atr_multiplier1 * df['atr1'])
    df['in_uptrend1'] = True
    df['upperband2'] = hl2 + (atr_multiplier2 * df['atr2'])
    df['lowerband2'] = hl2 - (atr_multiplier2 * df['atr2'])
    df['in_uptrend2'] = True
    df['upperband3'] = hl2 + (atr_multiplier3 * df['atr3'])
    df['lowerband3'] = hl2 - (atr_multiplier3 * df['atr3'])
    df['in_uptrend3'] = True
    for current in range(1, len(df.index)):
        previous = current - 1
#trend1
        if df['close'][current] > df['upperband1'][previous]:
            df['in_uptrend1'][current] = True
        elif df['close'][current] < df['lowerband1'][previous]:
            df['in_uptrend1'][current] = False
        else:
            df['in_uptrend1'][current] = df['in_uptrend1'][previous]

            if df['in_uptrend1'][current] and df['lowerband1'][current] < df['lowerband1'][previous]:
                df['lowerband1'][current] = df['lowerband1'][previous]

            if not df['in_uptrend1'][current] and df['upperband1'][current] > df['upperband1'][previous]:
                df['upperband1'][current] = df['upperband1'][previous]
#trend2
        if df['close'][current] > df['upperband2'][previous]:
            df['in_uptrend2'][current] = True
        elif df['close'][current] < df['lowerband2'][previous]:
            df['in_uptrend2'][current] = False
        else:
            df['in_uptrend2'][current] = df['in_uptrend2'][previous]

            if df['in_uptrend2'][current] and df['lowerband2'][current] < df['lowerband2'][previous]:
                df['lowerband2'][current] = df['lowerband2'][previous]

            if not df['in_uptrend2'][current] and df['upperband2'][current] > df['upperband2'][previous]:
                df['upperband2'][current] = df['upperband2'][previous]
#Trend3 
        if df['close'][current] > df['upperband3'][previous]:
            df['in_uptrend3'][current] = True
        elif df['close'][current] < df['lowerband3'][previous]:
            df['in_uptrend3'][current] = False
        else:
            df['in_uptrend3'][current] = df['in_uptrend3'][previous]

            if df['in_uptrend3'][current] and df['lowerband3'][current] < df['lowerband3'][previous]:
                df['lowerband3'][current] = df['lowerband3'][previous]

            if not df['in_uptrend3'][current] and df['upperband3'][current] > df['upperband3'][previous]:
                df['upperband3'][current] = df['upperband3'][previous]
        
    return df 

#calculate Pivot Points
#will need at least 1 day's worth of closing pricing Need to get from API instead of scraping
def PivotPoint(high,low,close):
    Pivot = (high + low + close)/3
    R1 = 2*Pivot - low
    S1= 2*Pivot - high
    R2 = Pivot + (high - low)
    S2 = Pivot - (high - low)
    R3 = Pivot + 2*(high - low)
    S3 = Pivot - 2*(high - low)
    return Pivot,S3,S2,S1,R1,R2,R3

# calculate Stoch RSI
# https://www.tradingview.com/wiki/Stochastic_RSI_(STOCH_RSI) 
def StochRSI(series, period=20, smoothK=3, smoothD=3):
    # Calculate RSI 
    delta = series.diff().dropna()
    ups = delta * 0
    downs = ups.copy()
    ups[delta > 0] = delta[delta > 0]
    downs[delta < 0] = -delta[delta < 0]
    #first value is sum of avg gains
    ups[ups.index[period-1]] = np.mean( ups[:period] ) 
    ups = ups.drop(ups.index[:(period-1)])
    #first value is sum of avg losses
    downs[downs.index[period-1]] = np.mean( downs[:period] ) 
    downs = downs.drop(downs.index[:(period-1)])
    rs = ups.ewm(com=period-1,min_periods=0,adjust=False,ignore_na=False).mean() / \
         downs.ewm(com=period-1,min_periods=0,adjust=False,ignore_na=False).mean() 
    rsi = 100 - 100 / (1 + rs)
    # Calculate StochRSI 
    stochrsi  = (rsi - rsi.rolling(period).min()) / (rsi.rolling(period).max() - rsi.rolling(period).min())
    stochrsi_K = stochrsi.rolling(smoothK).mean()
    stochrsi_D = stochrsi_K.rolling(smoothD).mean()

    return stochrsi, stochrsi_K, stochrsi_D

def pivotGrid(last_second_price,df):
    last_row_index = len(df.index) - 1
    pivotmid = (df['Pivot'][last_row_index]+df['R1'][last_row_index])/2
    pivotlowmid = (df['Pivot'][last_row_index]+pivotmid)/2
    pivothighmid = (df['R1'][last_row_index]+pivotmid)/2
    if(last_second_price > df['Pivot'][last_row_index] and last_second_price < pivotlowmid):
        pivot_price = df["Pivot"][last_row_index]
    elif(last_second_price > pivotlowmid and last_second_price < pivotmid):
        pivot_price = pivotlowmid
    elif(last_second_price > pivotmid and last_second_price < pivothighmid):
        pivot_price = pivotmid
    elif(last_second_price > pivothighmid and last_second_price < df['R1'][last_row_index]):
        pivot_price = pivothighmid
    else:
        pivotmid = (df['R1'][last_row_index]+df['R2'][last_row_index])/2
        pivotlowmid = (df['R1'][last_row_index]+pivotmid)/2
        pivothighmid = (df['R2'][last_row_index]+pivotmid)/2
        if(last_second_price > df['R1'][last_row_index] and last_second_price < pivotlowmid):
                pivot_price = df["R1"][last_row_index]
        elif(last_second_price > pivotlowmid and last_second_price < pivotmid):
            pivot_price = pivotlowmid
        elif(last_second_price > pivotmid and last_second_price < pivothighmid):
            pivot_price = pivotmid
        elif(last_second_price > pivothighmid and last_second_price < df['R2'][last_row_index]):
            pivot_price = pivothighmid
        else:
            pivotmid = (df['R2'][last_row_index]+df['R3'][last_row_index])/2
            pivotlowmid = (df['R2'][last_row_index]+pivotmid)/2
            pivothighmid = (df['R3'][last_row_index]+pivotmid)/2
            if(last_second_price > df['R2'][last_row_index] and last_second_price < pivotlowmid):
                    pivot_price = df["R2"][last_row_index]
            elif(last_second_price > pivotlowmid and last_second_price < pivotmid):
                pivot_price = pivotlowmid
            elif(last_second_price > pivotmid and last_second_price < pivothighmid):
                pivot_price = pivotmid
            elif(last_second_price > pivothighmid and last_second_price < df['R3'][last_row_index]):
                pivot_price = pivothighmid
            elif(last_second_price > df['R3'][last_row_index]):
                pivot_price = df['R3'][last_row_index]
            else:
                pivotmid = (df['Pivot'][last_row_index]+df['S1'][last_row_index])/2
                pivotlowmid = (df['S1'][last_row_index]+pivotmid)/2
                pivothighmid = (df['Pivot'][last_row_index]+pivotmid)/2
                if(last_second_price < df['Pivot'][last_row_index] and  last_second_price > pivothighmid):
                    pivot_price = df["Pivot"][last_row_index]
                elif(last_second_price < pivothighmid and last_second_price > pivotmid):
                    pivot_price = pivothighmid
                elif(last_second_price < pivotmid and last_second_price > pivotlowmid):
                    pivot_price = pivotmid
                elif(last_second_price < pivotlowmid and last_second_price > df['S2'][last_row_index]):
                    pivot_price = pivotlowmid
                else:
                    pivotmid = (df['S1'][last_row_index]+df['S2'][last_row_index])/2
                    pivotlowmid = (df['S2'][last_row_index]+pivotmid)/2
                    pivothighmid = (df['S1'][last_row_index]+pivotmid)/2
                    if(last_second_price < df['S1'][last_row_index] and  last_second_price > pivothighmid):
                        pivot_price = df["S1"][last_row_index]
                    elif(last_second_price < pivothighmid and last_second_price > pivotmid):
                        pivot_price = pivothighmid
                    elif(last_second_price < pivotmid and last_second_price > pivotlowmid):
                        pivot_price = pivotmid
                    elif(last_second_price < pivotlowmid and last_second_price > df['S3'][last_row_index]):
                        pivot_price = pivotlowmid
                    else:
                        pivotmid = (df['S2'][last_row_index]+df['S3'][last_row_index])/2
                        pivotlowmid = (df['S3'][last_row_index]+pivotmid)/2
                        pivothighmid = (df['S2'][last_row_index]+pivotmid)/2
                        if(last_second_price < df['S2'][last_row_index] and  last_second_price > pivothighmid):
                            pivot_price = df["S2"][last_row_index]
                        elif(last_second_price < pivothighmid and last_second_price > pivotmid):
                            pivot_price = pivothighmid
                        elif(last_second_price < pivotmid and last_second_price > pivotlowmid):
                            pivot_price = pivotmid
                        elif(last_second_price < pivotlowmid and last_second_price > df['S3'][last_row_index]):
                            pivot_price = pivotlowmid
                        elif(last_second_price < df['S3'][last_row_index]):
                            pivot_price = df['S3'][last_row_index]
    return pivot_price


####################
## CHECK SIGNALS  ##
####################
def check_buy_sell_signals(df):
    global in_position,stop_loss_percent,stop_loss_price,gain_percent,enable_neg_trend_sell,take_profit_price,buy_price,InputToken_address,address,private_key,defer_counter,bot_profit,supertrendFlip,macdCross,approveCounter,buy_counter,defer_percent,neg_trend_sell,waitCount,waitTime
    try:
        loadConfig('ATS_config.json')
        print("checking for buy and sell signals")
        #print(df.tail(5))
        last_row_index = len(df.index) - 1
        previous_row_index = last_row_index - 1
        third_row_index = last_row_index - 2
        fourth_row_index = last_row_index - 3
        fifth_row_index = last_row_index - 4
        last_second_price_index = len(sec_price.index) - 1
        last_second_price = sec_price['price'][last_second_price_index]
        
        #Sets limit Above in event price is close to pivot, will catch upswing
        #gets daily pivots and sets mid point of pivot band as limit price
        # Splitting pivots gave a lot of buy points, may not be great for short scrapes
        ##############################################################
        ####### ENABLE FOR DYNAMIC PIVOT PRICING ##################
        # pivot_price = pivotGrid(last_second_price,df)
        # #update Config with new Limit To wait for drops
        # with open("ATS_config.json", "r") as jsonFile:
        #     data = json.load(jsonFile)
        # data['base_config']['limit_price'] = pivot_price
        # with open("ATS_config.json", "w") as jsonFile:
        #     json.dump(data, jsonFile,indent=2)
        # print(f"Pivot Price Limit: {pivot_price}")
        ###############################################################
        #checks for Trading halt will pause trading
        if halt_trading:
            print(f"Trade Halt Stats: {halt_trading}")
            raise Exception("Trading Is Halted!")
        ############################################################
        #if negative Supertrend wait x amount of checks
        if neg_trend_sell and (waitCount <= waitTime):
            waitCount += 1
            print(f"Negative SuperTrend Purgatory. Wait Counter: {waitCount} /  {waitTime}")
            raise Exception("Waiting After Negative Supertrend!")
        #exit Negative Supertrend
        neg_trend_sell = False
        ################################################################
        #check for flip both green - red and red - green
        if ((df['in_uptrend1'][last_row_index] or df['in_uptrend2'][last_row_index]) and (not df['in_uptrend1'][previous_row_index] or not df['in_uptrend2'][previous_row_index]) or (not df['in_uptrend1'][last_row_index] or not df['in_uptrend2'][last_row_index]) and (df['in_uptrend1'][previous_row_index] or df['in_uptrend2'][previous_row_index])):
            supertrendFlip = True
        print(f"SuperTrendFlip is {supertrendFlip}")
        #check for MACD Cross Over
        if (((df['signal'][last_row_index] >= df['macd'][last_row_index]) and (df['signal'][previous_row_index] <= df['macd'][previous_row_index])) or ((df['signal'][last_row_index] <= df['macd'][last_row_index]) and (df['signal'][previous_row_index] >= df['macd'][previous_row_index]))):
            macdCross = True
        print(f"macdCross is {macdCross}")
    
        #Define strategy logic
        # Buy: Signal is below MACDAS and MACDAS has crossed, or confirmed triple super trend, not oversold, and ADX showing strength
        # No Buy: No Funds, Limit Buying is active and below limit,
        # Sell: Sell when negative supertrend detected and flipped
        # No Sell: Defer sell if price will not allow for net gain. (Factors in gas and dex fees.)
        if (((df['signal'][last_row_index] <= df['macd'][last_row_index]) and (macdCross==True)) or ((df['in_uptrend3'][last_row_index] and df['in_uptrend2'][last_row_index] and df['in_uptrend1'][last_row_index]) and df['SRSI_K'][last_row_index] < 80) and (df['adx'][last_row_index] > 19.25)):
            print("In Uptrend")
            print(f"MCAD Signal: {((df['signal'][last_row_index] <= df['macd'][last_row_index]) and (macdCross==True))}")
            print(f"SuperTrend Signal: {((df['in_uptrend3'][last_row_index] and df['in_uptrend2'][last_row_index] and df['in_uptrend1'][last_row_index]) and df['SRSI_K'][last_row_index] < 80)}")
            print(f"ADX Signal: {(df['adx'][last_row_index] > 19.25)}")
            if not in_position:
                txRetryCounter = 0
                #check for wallet balance
                if(not checkWalletBalance(address, base_coin)):
                    print("Insufficient Buy_Amount in Wallet!")
                    raise Exception("Limit Price Not Met, Waiting for Limit.")
                #checks for Limit Buy price fails if not at price
                #implement some auto limit set based on pivot points eventually
                elif((limit_buy == True) and (last_second_price > limit_price)):
                    print(f"Limit Check Failed! Limit Price: {limit_price} | Current Price: {last_second_price}",file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                    raise Exception("Limit Price Not Met, Waiting for Limit.")
                #checks for negative supertrend sell. Normally Negative supertrend takes are accompanied by larger dips. 
                # Was useful in the event of a sell on supertrend change, if other indicators flashed green, stayed out of trades while negative supertrend was in effect. 
                # elif neg_trend_sell:
                #     print(f"Negative Trend Sell Recent. Waiting for bottom out or limit")
                #     raise Exception("Negative Supertrend in effect!")
                else:
                    for txRetryCounter in range(2):
                        #Buy Coins
                        try:
                            buy_coin(address,private_key,InputToken_address,buy_amount)
                            #update Config with position state
                            with open("ATS_config.json", "r") as jsonFile:
                                data = json.load(jsonFile)
                            data['base_config']['in_position'] = True
                            with open("ATS_config.json", "w") as jsonFile:
                                json.dump(data, jsonFile,indent=2)
                            in_position = True
                            buy_counter += 1
                            buy_price = last_second_price
                            stop_loss_price = (buy_price) - (buy_price * stop_loss_percent)
                            take_profit_price = (buy_price * gain_percent)
                            supertrendFlip = False
                            macdCross = False
                            trade_rows = [datetime.now().isoformat(),"buy", buy_price, stop_loss_price, take_profit_price,""]
                            with open(f'{logpath}//trades.csv', 'a', encoding='UTF8', newline='') as f:
                                writer = csv.writer(f)
                                writer.writerow(trade_rows)
                            print(f"Timestamp: {datetime.now().isoformat()}", file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                            print(f"Buy for: {buy_price}", file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                            print(f"Stop Loss: {stop_loss_price}", file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                            print(f"Take Profit: {take_profit_price}", file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                            print(f"Current Bot Profit: {bot_profit}" , file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                            trade_rows = [datetime.now().isoformat(),"buy",buy_price, stop_loss_price, take_profit_price,""]
                            with open(f'{logpath}//trades.csv', 'a', encoding='UTF8', newline='') as f:
                                writer = csv.writer(f)
                                writer.writerow(trade_rows)
                        except Exception as exc:
                            print(traceback.format_exc(), file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                            print(exc, file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                            print(f"BUY ERROR STRAT | Try Count: {txRetryCounter}| Timestamp: {datetime.now().isoformat()} | BUY_PRICE: {buy_price}", file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))                        
                            txRetryCounter += 1
                            time.sleep(15)
                            continue
                        break
                    #Send Telegram Message
                    message = (f"Buy Alert! \n\
Timestamp: {datetime.now().isoformat()} \n\
Buy for: {buy_price}\n\
Stop Loss: {stop_loss_price} \n\
Take Profit: {take_profit_price}\n\
Current Bot Profit: {bot_profit}\n\
")
                    sendMessage(message)
            else:
                print(f"Already in position, nothing to do {last_second_price}", file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
        #Sell Logic
        if ((not df['in_uptrend2'][last_row_index]) and supertrendFlip == True and enable_neg_trend_sell == True):
            if in_position  and buy_counter > 0:
                print("SuperTrend downtrend, try to sell...")
                #defer sell if no profit can be made
                deferPrice = (buy_price * defer_percent)
                if (last_second_price < deferPrice):
                    defer_counter += 1
                    print(f"Sell Deferred, Not enough profit | Price: {last_second_price} ")
                    print(f"Defer Sell for: {last_second_price}" , file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                else:                    
                    neg_trend_sell = True
                    waitCount = 0
                    txRetryCounter = 0
                    for txRetryCounter in range(2):
                        #Sell Coin
                        try:
                            sell_coin(address,private_key,InputToken_address)
                            #update Config with position state
                            with open("ATS_config.json", "r") as jsonFile:
                                data = json.load(jsonFile)
                            data['base_config']['in_position'] = False
                            with open("ATS_config.json", "w") as jsonFile:
                                json.dump(data, jsonFile,indent=2)
                            in_position = False
                            supertrendFlip = False
                            macdCross = False
                            defer_counter = 0
                            approveCounter = 1
                            bot_profit = (bot_profit + ((last_second_price - buy_price)*(web3.fromWei(minimumOut,'ether'))) - ((buy_price*.003)*(web3.fromWei(minimumOut,'ether'))))
                            trade_rows = [datetime.now().isoformat(),"sell",current_price, "", "",bot_profit]
                            with open(f'{logpath}//trades.csv', 'a', encoding='UTF8', newline='') as f:
                                writer = csv.writer(f)
                                writer.writerow(trade_rows)
                            print(f"Timestamp: {datetime.now().isoformat()}", file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                            print(f"Sell for: {last_second_price}" , file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                            print(f"Current Bot Profit: {bot_profit}" , file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                        except Exception as exc:
                            print(traceback.format_exc(), file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                            print(exc, file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                            print(f"SELL ERROR STRAT| Try Count: {txRetryCounter} | Timestamp: {datetime.now().isoformat()} | SELL_PRICE: {last_second_price}", file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                            time.sleep(15)
                            txRetryCounter += 1
                            continue
                        break
                    #Send Telegram Message
                    message = (f"Sell Alert! \n\
Timestamp: {datetime.now().isoformat()} \n\
Sell Type: Negative SuperTrend Trigger\n\
Sell for: {last_second_price}\n\
Current Bot Profit: {bot_profit} \n\
")
                    sendMessage(message)
            else:
                print(f"Not in position, nothing to sell {last_second_price}", file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
            '''
            #Not super useful with stop loss implemented, leaving as option for sell. 
            #sell out if deferred too many times Will sell for loss but open other trade opertunity 
            if (defer_counter >= 50):
                in_position = False
                defer_counter = 0
                bot_profit = bot_profit + (last_second_price - buy_price)
                #Sell Coin
                try:
                    sell_coin(address,private_key,InputToken_address)
                except:
                    print(f"SELL ERROR | Timestamp: {datetime.now().isoformat()} | SELL_PRICE: {last_second_price}", file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                
                print(f"Timestamp: {datetime.now().isoformat()}", file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                print(f"Deferred Sale for: {last_second_price}" , file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                print(f"Loss on Deferral: {buy_price - last_second_price}" , file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                print(f"Current Bot Profit: {bot_profit}" , file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
            '''
    except Exception as exc:
        print(traceback.format_exc())
        print(exc)
        print(f"{datetime.now().isoformat()} | Failed to check for pricing, retrying on next run. Most likely not enough candles built yet.")


#########################################
##         RUN PRICE CHECK            ###
#########################################
#runs on defined schedule in main. Base this on the timescale you are trading on or you will have a lot of wasted compute
def run_bot():
    global min1_price,min5_price,supertrend_p1,atr1,supertrend_p2,atr2,supertrend_p3,atr3,macd_fast,macd_slow,macd_signal,srsi_p,srsi_k,srsi_d,candle_data,yfticker
    print(f"Fetching new bars for {datetime.now().isoformat()}")
    min5_df = pd.DataFrame(min5_price)
    #Print Config
    print(f"sell_now {sell_now} \n\
buy_now {buy_now}\n\
supertrend_p1 {supertrend_p1}\n\
atr1 {atr1} \n\
supertrend_p2 {supertrend_p2}\n\
atr2 {atr2}\n\
supertrend_p3 {supertrend_p3}\n\
atr3 {atr3}\n\
macd_fast {macd_fast}\n\
macd_slow {macd_slow}\n\
macd_signal {macd_signal}\n\
srsi_p {srsi_p}\n\
srsi_k {srsi_k}\n\
srsi_d {srsi_d}\n")
       
    #SuperTrend Strat
    try:
        candle_data = triplesupertrend(min5_df, period1=supertrend_p1 ,period2=supertrend_p2 ,period3=supertrend_p3, atr_multiplier1=atr1, atr_multiplier2=atr2, atr_multiplier3 = atr3)
        #print(min5_df)
    except:
        print("Failed to calculate triplesupertrend.")
    #Use MACDAS thank you Tradingview
    try:
        candle_data.ta.macd(close='close', fast=macd_fast, slow=macd_slow, signal=macd_signal, append=True,asmode='True')
        candle_data.rename(columns = {f'MACDAS_{macd_fast}_{macd_slow}_{macd_signal}':'macd', f'MACDASh_{macd_fast}_{macd_slow}_{macd_signal}':'hist',f'MACDASs_{macd_fast}_{macd_slow}_{macd_signal}':'signal'}, inplace = True)
    except:
        print("Error Calculating MACD, Wait for More Data to Populate...")

    #Use ADX
    try:
        candle_data.ta.adx(high = min5_df['high'], low =min5_df['low'],close = min5_df['close'],length=adx_length,lensig=14,append=True)
        candle_data.rename(columns = {f'ADX_{adx_length}':'adx', f'DMP_{adx_length}':'dmp',f'DMN_{adx_length}':'dmn'}, inplace = True)
    except:
        print("Error Calculating ADX, Wait for More Data to Populate...")
    #Use Squeeze
    try:
        candle_data.ta.squeeze(high = min5_df['high'], low =min5_df['low'],close = min5_df['close'],lazybear=True,append=True)
        candle_data.rename(columns = {'SQZ_20_2.0_20_1.5_LB':'SQZ'}, inplace = True)
    except:
        print("Error Calculating Squeeze Data, Wait for More Data to Populate...")
    try:
    #stochRSI Strat
        candle_data['RSI'],candle_data['SRSI_K'],candle_data['SRSI_D'] = StochRSI(candle_data['close'], period=srsi_p, smoothK=srsi_k, smoothD=srsi_d)
    except:
        print("Error Calculating SRSI, Wait for More Data to Populate...")
    #calculate the Days Pivot Points 
    try:    
        tickerFetch = yf.Ticker(yfticker)
        hist  = tickerFetch.history(period="5d",interval="1d")
        last_day = hist.tail(1).copy()
        candle_data['Pivot'],candle_data['S3'],candle_data['S2'],candle_data['S1'],candle_data['R1'],candle_data['R2'],candle_data['R3'] = PivotPoint(last_day["High"][0],last_day["Low"][0],last_day["Close"][0])
    except:
        print("Error Calculating Pivot Points, Wait for More Data to Populate...")
    #Check for Buy/Sell
    try:
        print(candle_data.tail(7))
        check_buy_sell_signals(candle_data)
    except Exception as exc:
        print(traceback.format_exc())
        print(exc)
        print("Failed to check for Signals. Probably not enough candle data.")

#######################################################
########        Check Wallet Balance                ###
#######################################################
#needed incase buy_amount less than what is avalible in wallet.

def checkWalletBalance(address, base_coin):
    global web3, router_pancakev2, panabi,buy_amount
    #base_coin = web3.toChecksumAddress("0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c")  #WBNB Address
    #base_coin = web3.toChecksumAddress("0x1AF3F329e8BE154074D8769D1FFa4eE058B1DBc3")  #DAI Address
    loadConfig('ATS_config.json')
    base_coin = web3.toChecksumAddress(base_coin)    #BUSD Contract
    sellAbi = '[{"inputs":[{"internalType":"string","name":"_NAME","type":"string"},{"internalType":"string","name":"_SYMBOL","type":"string"},{"internalType":"uint256","name":"_DECIMALS","type":"uint256"},{"internalType":"uint256","name":"_supply","type":"uint256"},{"internalType":"uint256","name":"_txFee","type":"uint256"},{"internalType":"uint256","name":"_lpFee","type":"uint256"},{"internalType":"uint256","name":"_MAXAMOUNT","type":"uint256"},{"internalType":"uint256","name":"SELLMAXAMOUNT","type":"uint256"},{"internalType":"address","name":"routerAddress","type":"address"},{"internalType":"address","name":"tokenOwner","type":"address"}],"stateMutability":"nonpayable","type":"constructor"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"owner","type":"address"},{"indexed":true,"internalType":"address","name":"spender","type":"address"},{"indexed":false,"internalType":"uint256","name":"value","type":"uint256"}],"name":"Approval","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint256","name":"minTokensBeforeSwap","type":"uint256"}],"name":"MinTokensBeforeSwapUpdated","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"previousOwner","type":"address"},{"indexed":true,"internalType":"address","name":"newOwner","type":"address"}],"name":"OwnershipTransferred","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint256","name":"tokensSwapped","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"ethReceived","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"tokensIntoLiqudity","type":"uint256"}],"name":"SwapAndLiquify","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"bool","name":"enabled","type":"bool"}],"name":"SwapAndLiquifyEnabledUpdated","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"from","type":"address"},{"indexed":true,"internalType":"address","name":"to","type":"address"},{"indexed":false,"internalType":"uint256","name":"value","type":"uint256"}],"name":"Transfer","type":"event"},{"inputs":[],"name":"_liquidityFee","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"_maxTxAmount","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"_owner","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"_taxFee","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"address","name":"spender","type":"address"}],"name":"allowance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"claimTokens","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"decimals","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"subtractedValue","type":"uint256"}],"name":"decreaseAllowance","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"tAmount","type":"uint256"}],"name":"deliver","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"excludeFromFee","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"excludeFromReward","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"geUnlockTime","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"includeInFee","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"includeInReward","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"addedValue","type":"uint256"}],"name":"increaseAllowance","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"isExcludedFromFee","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"isExcludedFromReward","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"time","type":"uint256"}],"name":"lock","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"name","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"numTokensSellToAddToLiquidity","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"owner","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"tAmount","type":"uint256"},{"internalType":"bool","name":"deductTransferFee","type":"bool"}],"name":"reflectionFromToken","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"renounceOwnership","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"liquidityFee","type":"uint256"}],"name":"setLiquidityFeePercent","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"maxTxPercent","type":"uint256"}],"name":"setMaxTxPercent","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"swapNumber","type":"uint256"}],"name":"setNumTokensSellToAddToLiquidity","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"bool","name":"_enabled","type":"bool"}],"name":"setSwapAndLiquifyEnabled","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"taxFee","type":"uint256"}],"name":"setTaxFeePercent","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"swapAndLiquifyEnabled","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"symbol","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"rAmount","type":"uint256"}],"name":"tokenFromReflection","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"totalFees","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"totalSupply","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"transfer","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"sender","type":"address"},{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"transferFrom","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"newOwner","type":"address"}],"name":"transferOwnership","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"uniswapV2Pair","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"uniswapV2Router","outputs":[{"internalType":"contract IUniswapV2Router02","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"unlock","outputs":[],"stateMutability":"nonpayable","type":"function"},{"stateMutability":"payable","type":"receive"}]'
    #Create token Instance for Token
    sellTokenContract = web3.eth.contract(base_coin, abi=sellAbi)
    #Get Token Balance
    balance = sellTokenContract.functions.balanceOf(address).call()
    symbol = sellTokenContract.functions.symbol().call()
    ether_balance = int(web3.fromWei(balance,'ether'))
    print("Balance: " + str(ether_balance) + " " + symbol)
    if(ether_balance < buy_amount):
        print("Insufficient Funds for buy_amount specified!")
        return False
    else:
        return True

#######################################
##          BUYING COIN             ###
#######################################
def buy_coin(address, private_key, InputToken_address,buy_amount):
    global web3, router_pancakev2, panabi, buy_counter, slippage,minimumOut
    print(web3.isConnected())
    #pancakeswap router abi 
    balance = web3.eth.get_balance(address)
    print(balance)
    readabletoken = web3.fromWei(balance,'ether')
    print(readabletoken)
    tokenToBuy = web3.toChecksumAddress(InputToken_address)
    #base_coin = web3.toChecksumAddress("0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c")  #wbnb contract
    #base_coin = web3.toChecksumAddress("0x1AF3F329e8BE154074D8769D1FFa4eE058B1DBc3")    #dai Contract
    base_coin = web3.toChecksumAddress('0xe9e7cea3dedca5984780bafc599bd69add087d56')    #BUSD Contract
    #Setup the PancakeSwap contract
    contract = web3.eth.contract(address=router_pancakev2, abi=panabi)
    #get Min Swap Price, Individual Coin Price + slippage, precalculate slippage to know what output will be
    minimumOut = int(((contract.functions.getAmountsOut(web3.toWei(buy_amount,'ether'),[base_coin,InputToken_address]).call())[1])*slippage)
    pancakeswap2_txn = contract.functions.swapExactTokensForTokens(
    web3.toWei(buy_amount,'ether'), #Amount in 
    minimumOut,# Min Amount Out possible
    #add or remove gas depending on what you need
    [base_coin,tokenToBuy],
    address,
    (int(time.time()) + 100000)
    ).buildTransaction({
    'from': address,
    'gas': 1050000,
    'gasPrice': web3.toWei('15','gwei'),
    'nonce': web3.eth.get_transaction_count(address),
    })
    signed_txn = web3.eth.account.sign_transaction(pancakeswap2_txn, private_key=private_key)
    tx_token = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
    print(f"BUY TX: {web3.toHex(tx_token)}")
    buy_counter += 1

#######################################
##          SELLING COIN            ###
#######################################
def sell_coin(address, private_key, InputToken_address):
    global web3, router_pancakev2, panabi,approveCounter,config,slippage,minimumOut
    #base_coin = web3.toChecksumAddress("0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c")  #WBNB Address
    #base_coin = web3.toChecksumAddress("0x1AF3F329e8BE154074D8769D1FFa4eE058B1DBc3")  #DAI Address
    base_coin = web3.toChecksumAddress('0xe9e7cea3dedca5984780bafc599bd69add087d56')    #BUSD Contract
    contract_id = web3.toChecksumAddress(InputToken_address)
    #Setup the PancakeSwap contract
    contract = web3.eth.contract(address=router_pancakev2, abi=panabi)
    #Abi for Token to sell - all we need from here is the balanceOf & approve function can replace with shortABI
    sellAbi = '[{"inputs":[{"internalType":"string","name":"_NAME","type":"string"},{"internalType":"string","name":"_SYMBOL","type":"string"},{"internalType":"uint256","name":"_DECIMALS","type":"uint256"},{"internalType":"uint256","name":"_supply","type":"uint256"},{"internalType":"uint256","name":"_txFee","type":"uint256"},{"internalType":"uint256","name":"_lpFee","type":"uint256"},{"internalType":"uint256","name":"_MAXAMOUNT","type":"uint256"},{"internalType":"uint256","name":"SELLMAXAMOUNT","type":"uint256"},{"internalType":"address","name":"routerAddress","type":"address"},{"internalType":"address","name":"tokenOwner","type":"address"}],"stateMutability":"nonpayable","type":"constructor"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"owner","type":"address"},{"indexed":true,"internalType":"address","name":"spender","type":"address"},{"indexed":false,"internalType":"uint256","name":"value","type":"uint256"}],"name":"Approval","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint256","name":"minTokensBeforeSwap","type":"uint256"}],"name":"MinTokensBeforeSwapUpdated","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"previousOwner","type":"address"},{"indexed":true,"internalType":"address","name":"newOwner","type":"address"}],"name":"OwnershipTransferred","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint256","name":"tokensSwapped","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"ethReceived","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"tokensIntoLiqudity","type":"uint256"}],"name":"SwapAndLiquify","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"bool","name":"enabled","type":"bool"}],"name":"SwapAndLiquifyEnabledUpdated","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"from","type":"address"},{"indexed":true,"internalType":"address","name":"to","type":"address"},{"indexed":false,"internalType":"uint256","name":"value","type":"uint256"}],"name":"Transfer","type":"event"},{"inputs":[],"name":"_liquidityFee","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"_maxTxAmount","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"_owner","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"_taxFee","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"address","name":"spender","type":"address"}],"name":"allowance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"claimTokens","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"decimals","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"subtractedValue","type":"uint256"}],"name":"decreaseAllowance","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"tAmount","type":"uint256"}],"name":"deliver","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"excludeFromFee","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"excludeFromReward","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"geUnlockTime","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"includeInFee","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"includeInReward","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"addedValue","type":"uint256"}],"name":"increaseAllowance","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"isExcludedFromFee","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"isExcludedFromReward","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"time","type":"uint256"}],"name":"lock","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"name","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"numTokensSellToAddToLiquidity","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"owner","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"tAmount","type":"uint256"},{"internalType":"bool","name":"deductTransferFee","type":"bool"}],"name":"reflectionFromToken","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"renounceOwnership","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"liquidityFee","type":"uint256"}],"name":"setLiquidityFeePercent","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"maxTxPercent","type":"uint256"}],"name":"setMaxTxPercent","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"swapNumber","type":"uint256"}],"name":"setNumTokensSellToAddToLiquidity","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"bool","name":"_enabled","type":"bool"}],"name":"setSwapAndLiquifyEnabled","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"taxFee","type":"uint256"}],"name":"setTaxFeePercent","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"swapAndLiquifyEnabled","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"symbol","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"rAmount","type":"uint256"}],"name":"tokenFromReflection","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"totalFees","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"totalSupply","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"transfer","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"sender","type":"address"},{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"transferFrom","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"newOwner","type":"address"}],"name":"transferOwnership","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"uniswapV2Pair","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"uniswapV2Router","outputs":[{"internalType":"contract IUniswapV2Router02","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"unlock","outputs":[],"stateMutability":"nonpayable","type":"function"},{"stateMutability":"payable","type":"receive"}]'
    #Create token Instance for Token
    sellTokenContract = web3.eth.contract(contract_id, abi=sellAbi)
    #Get Token Balance
    balance = sellTokenContract.functions.balanceOf(address).call()
    symbol = sellTokenContract.functions.symbol().call()
    ether_balance = (web3.fromWei(balance,'ether'))
    print("Balance: " + str(ether_balance) + " " + symbol)
    #approve tx before sending. Does not have to be done every time, but logic is needed.
    approve = sellTokenContract.functions.approve(router_pancakev2, balance).buildTransaction({
                'from': address,
                'gasPrice': web3.toWei('10','gwei'),
                'nonce': web3.eth.get_transaction_count(address),
                })
    signed_txn = web3.eth.account.sign_transaction(approve, private_key=private_key)
    tx_token = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
    print("Approved: " + web3.toHex(tx_token))
    #Wait after approve seconds before sending transaction, higher gas can make this quicker. 7 Secs seems to be the right amount for the current setup
    time.sleep(7)
    print(f"Swapping {balance} {symbol} for USD")
    tokenToSell = web3.toChecksumAddress(InputToken_address)
    #slippage 
    # ~0.3% good for large Liquidity pools
    # 1% for low liquidity pools
    # Do not trade "tax tokens"
    #get output with slippage pre-calculated
    minimumOut = int(((contract.functions.getAmountsOut(balance,[tokenToSell,base_coin]).call())[1])*slippage)
    #Swaping Base token (USD) for Token
    pancakeswap2_txn = contract.functions.swapExactTokensForTokens(
        balance, #Amount in 
        minimumOut,# Min Amount Out possible
        [tokenToSell,base_coin],
        address,
        (int(time.time()) + 100000)
        ).buildTransaction({
        'from': address,
        'gas': 1050000,
        'gasPrice': web3.toWei('15','gwei'),
        'nonce': web3.eth.get_transaction_count(address),
        })
    signed_txn = web3.eth.account.sign_transaction(pancakeswap2_txn, private_key=private_key)
    tx_token = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
    print(f"Sold {symbol}: " + web3.toHex(tx_token))

##########################################################
#####             PRICING DATA              ##############
##########################################################

total_data = pd.DataFrame()
sec_price = pd.DataFrame()
min5_price = pd.DataFrame()
min1_price = pd.DataFrame()
Counter = 0
clear_df = False
firstWait = True

#ABI
panabi = '[{"inputs":[{"internalType":"address","name":"_factory","type":"address"},{"internalType":"address","name":"_WETH","type":"address"}],"stateMutability":"nonpayable","type":"constructor"},{"inputs":[],"name":"WETH","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"tokenA","type":"address"},{"internalType":"address","name":"tokenB","type":"address"},{"internalType":"uint256","name":"amountADesired","type":"uint256"},{"internalType":"uint256","name":"amountBDesired","type":"uint256"},{"internalType":"uint256","name":"amountAMin","type":"uint256"},{"internalType":"uint256","name":"amountBMin","type":"uint256"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"addLiquidity","outputs":[{"internalType":"uint256","name":"amountA","type":"uint256"},{"internalType":"uint256","name":"amountB","type":"uint256"},{"internalType":"uint256","name":"liquidity","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"token","type":"address"},{"internalType":"uint256","name":"amountTokenDesired","type":"uint256"},{"internalType":"uint256","name":"amountTokenMin","type":"uint256"},{"internalType":"uint256","name":"amountETHMin","type":"uint256"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"addLiquidityETH","outputs":[{"internalType":"uint256","name":"amountToken","type":"uint256"},{"internalType":"uint256","name":"amountETH","type":"uint256"},{"internalType":"uint256","name":"liquidity","type":"uint256"}],"stateMutability":"payable","type":"function"},{"inputs":[],"name":"factory","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"},{"internalType":"uint256","name":"reserveIn","type":"uint256"},{"internalType":"uint256","name":"reserveOut","type":"uint256"}],"name":"getAmountIn","outputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"}],"stateMutability":"pure","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"reserveIn","type":"uint256"},{"internalType":"uint256","name":"reserveOut","type":"uint256"}],"name":"getAmountOut","outputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"}],"stateMutability":"pure","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"}],"name":"getAmountsIn","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"}],"name":"getAmountsOut","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountA","type":"uint256"},{"internalType":"uint256","name":"reserveA","type":"uint256"},{"internalType":"uint256","name":"reserveB","type":"uint256"}],"name":"quote","outputs":[{"internalType":"uint256","name":"amountB","type":"uint256"}],"stateMutability":"pure","type":"function"},{"inputs":[{"internalType":"address","name":"tokenA","type":"address"},{"internalType":"address","name":"tokenB","type":"address"},{"internalType":"uint256","name":"liquidity","type":"uint256"},{"internalType":"uint256","name":"amountAMin","type":"uint256"},{"internalType":"uint256","name":"amountBMin","type":"uint256"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"removeLiquidity","outputs":[{"internalType":"uint256","name":"amountA","type":"uint256"},{"internalType":"uint256","name":"amountB","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"token","type":"address"},{"internalType":"uint256","name":"liquidity","type":"uint256"},{"internalType":"uint256","name":"amountTokenMin","type":"uint256"},{"internalType":"uint256","name":"amountETHMin","type":"uint256"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"removeLiquidityETH","outputs":[{"internalType":"uint256","name":"amountToken","type":"uint256"},{"internalType":"uint256","name":"amountETH","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"token","type":"address"},{"internalType":"uint256","name":"liquidity","type":"uint256"},{"internalType":"uint256","name":"amountTokenMin","type":"uint256"},{"internalType":"uint256","name":"amountETHMin","type":"uint256"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"removeLiquidityETHSupportingFeeOnTransferTokens","outputs":[{"internalType":"uint256","name":"amountETH","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"token","type":"address"},{"internalType":"uint256","name":"liquidity","type":"uint256"},{"internalType":"uint256","name":"amountTokenMin","type":"uint256"},{"internalType":"uint256","name":"amountETHMin","type":"uint256"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"},{"internalType":"bool","name":"approveMax","type":"bool"},{"internalType":"uint8","name":"v","type":"uint8"},{"internalType":"bytes32","name":"r","type":"bytes32"},{"internalType":"bytes32","name":"s","type":"bytes32"}],"name":"removeLiquidityETHWithPermit","outputs":[{"internalType":"uint256","name":"amountToken","type":"uint256"},{"internalType":"uint256","name":"amountETH","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"token","type":"address"},{"internalType":"uint256","name":"liquidity","type":"uint256"},{"internalType":"uint256","name":"amountTokenMin","type":"uint256"},{"internalType":"uint256","name":"amountETHMin","type":"uint256"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"},{"internalType":"bool","name":"approveMax","type":"bool"},{"internalType":"uint8","name":"v","type":"uint8"},{"internalType":"bytes32","name":"r","type":"bytes32"},{"internalType":"bytes32","name":"s","type":"bytes32"}],"name":"removeLiquidityETHWithPermitSupportingFeeOnTransferTokens","outputs":[{"internalType":"uint256","name":"amountETH","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"tokenA","type":"address"},{"internalType":"address","name":"tokenB","type":"address"},{"internalType":"uint256","name":"liquidity","type":"uint256"},{"internalType":"uint256","name":"amountAMin","type":"uint256"},{"internalType":"uint256","name":"amountBMin","type":"uint256"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"},{"internalType":"bool","name":"approveMax","type":"bool"},{"internalType":"uint8","name":"v","type":"uint8"},{"internalType":"bytes32","name":"r","type":"bytes32"},{"internalType":"bytes32","name":"s","type":"bytes32"}],"name":"removeLiquidityWithPermit","outputs":[{"internalType":"uint256","name":"amountA","type":"uint256"},{"internalType":"uint256","name":"amountB","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapETHForExactTokens","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"payable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactETHForTokens","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"payable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactETHForTokensSupportingFeeOnTransferTokens","outputs":[],"stateMutability":"payable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForETH","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForETHSupportingFeeOnTransferTokens","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForTokens","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForTokensSupportingFeeOnTransferTokens","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"},{"internalType":"uint256","name":"amountInMax","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapTokensForExactETH","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"},{"internalType":"uint256","name":"amountInMax","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapTokensForExactTokens","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"},{"stateMutability":"payable","type":"receive"}]'

#Calling PCS v2 Factory 
version = 2        # specify version
provider_bsc = 'https://bsc-dataseed.binance.org/'
factory_pancakev2 = '0xca143ce32fe78f1f7019d7d551a6402fc5350c73'
router_pancakev2 = '0x10ED43C718714eb63d5aA57B78B54704E256024E'
#By default trades from BNB address, Change to whatever pair you want to trade.
wbnb_address = '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c'
#dai_address = '0x1AF3F329e8BE154074D8769D1FFa4eE058B1DBc3'
busd_address= '0xe9e7cea3dedca5984780bafc599bd69add087d56'
busd_address = Web3.toChecksumAddress(busd_address)
InputToken_address = Web3.toChecksumAddress(InputToken_address)
web3 = Web3(Web3.HTTPProvider(provider_bsc))
dai_route = ['0x1AF3F329e8BE154074D8769D1FFa4eE058B1DBc3', '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c', '0x2170Ed0880ac9A755fd29B2688956BD959F933F8']
busd_route = ['0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56', '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c', '0x2170Ed0880ac9A755fd29B2688956BD959F933F8']
#####################################
##  COLLECT CANDLE DATA            ## 
#####################################
def getPrice() :
    global sec_price, current_price,take_profit_price,stop_loss_price,address,private_key,InputToken_address,in_position,supertrendFlip,macdCross,bot_profit,buy_price,approveCounter,stop_loss_percent,gain_percent,buy_amount,sell_now,buy_now,supertrend_p1,atr1,supertrend_p2,atr2,supertrend_p3,atr3,macd_fast,macd_slow,macd_signal,srsi_p,srsi_k,srsi_d,buy_counter,candle_data,firstWait
    while True:
        try:
            loadConfig("ATS_config.json")
            base_coin = web3.toChecksumAddress(busd_address)    #BUSD Contract
            InputToken_address = Web3.toChecksumAddress(InputToken_address)
            #Setup the PancakeSwap contract
            contract = web3.eth.contract(address=router_pancakev2, abi=panabi)
            current_price = (contract.functions.getAmountsOut(1,[InputToken_address,base_coin]).call())[1]
            current_price = float(web3.fromWei(current_price,'gwei'))  
#######################################################################################
            #Check for manual sell, if set to true, will immediatly sell. 
            if(sell_now):
                if (in_position):
                    #sellcoin
                    txRetryCounter = 0 
                    for txRetryCounter in range(2):
                        try:
                            sell_coin(address,private_key,InputToken_address)
                            #update Config with position state
                            with open("ATS_config.json", "r") as jsonFile:
                                data = json.load(jsonFile)
                            data['base_config']['in_position'] = False
                            with open("ATS_config.json", "w") as jsonFile:
                                json.dump(data, jsonFile,indent=2)
                            in_position = False
                            macdCross = False
                            supertrendFlip = False
                            bot_profit = (bot_profit + ((current_price - buy_price)*(web3.fromWei(minimumOut,'ether'))) - ((current_price*.01)*(web3.fromWei(minimumOut,'ether'))))
                            trade_rows = [datetime.now().isoformat(),"sell",current_price, "", "",bot_profit]
                            with open(f'{logpath}//trades.csv', 'a', encoding='UTF8', newline='') as f:
                                writer = csv.writer(f)
                                writer.writerow(trade_rows)
                            print(f"Manual Sell_now Triggered: {current_price} | Timestamp: {datetime.now().isoformat()}" , file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                        except Exception as exc:
                            print(traceback.format_exc(), file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                            print(exc, file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                            print(f"SELL ERROR SELL NOW| Try Count: {txRetryCounter} | Timestamp: {datetime.now().isoformat()} | SELL_PRICE: {current_price}", file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                            txRetryCounter += 1
                            time.sleep(15)
                            continue
                        break
                    #Send Telegram Message
                    message = (f"Sell Alert! \n\
Timestamp: {datetime.now().isoformat()} \n\
Sell Type: Manual Sell\n\
Sell for: {current_price}\n\
Current Bot Profit: {bot_profit} \n\
")
                    sendMessage(message)
                else:
                    print("Not in Position, Cannot Sell!")
#######################################################################################
            #Check for manual buy, will buy if set to true in config
            if (buy_now):
                if (not in_position):
                    #check for wallet balance
                    if(not checkWalletBalance(address, base_coin)):
                        print("Insufficient Buy_Amount in Wallet!")
                    else:
                        txRetryCounter = 0 
                        for txRetryCounter in range(2):
                            try:
                                buy_coin(address,private_key,InputToken_address,buy_amount)
                                #update Config with position state
                                with open("ATS_config.json", "r") as jsonFile:
                                    data = json.load(jsonFile)
                                data['base_config']['in_position'] = True
                                with open("ATS_config.json", "w") as jsonFile:
                                    json.dump(data, jsonFile,indent=2)
                                in_position = True
                                buy_price = current_price
                                stop_loss_price = (buy_price) - (buy_price * stop_loss_percent)
                                take_profit_price = (buy_price * gain_percent)
                                supertrendFlip = False
                                macdCross = False
                                trade_rows = [datetime.now().isoformat(),"buy", buy_price, stop_loss_price, take_profit_price,""]
                                with open(f'{logpath}//trades.csv', 'a', encoding='UTF8', newline='') as f:
                                    writer = csv.writer(f)
                                    writer.writerow(trade_rows)
                                print(f"Timestamp: {datetime.now().isoformat()}", file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                                print(f"Buy for: {buy_price}", file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                                print(f"Stop Loss: {stop_loss_price}", file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                                print(f"Take Profit: {take_profit_price}", file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                                print(f"Current Bot Profit: {bot_profit}" , file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                            except Exception as exc:
                                print(traceback.format_exc(), file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                                print(exc, file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                                print(f"BUY ERROR BUY_NOW | Try Count: {txRetryCounter}| Timestamp: {datetime.now().isoformat()} | BUY_PRICE: {buy_price}", file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))                        
                                txRetryCounter += 1
                                time.sleep(15)
                                continue
                            break
                        #Send Telegram Message
                        message = (f"Buy Alert! \n\
Timestamp: {datetime.now().isoformat()} \n\
Buy for: {buy_price}\n\
Stop Loss: {stop_loss_price} \n\
Take Profit: {take_profit_price}\n\
Current Bot Profit: {bot_profit}\n\
")
                        sendMessage(message)
                else:
                    print("Already in Position Cannot Buy!")
#######################################################################################
            #Check for Limit Price, checks limit price set in config will buy if price ticks to limit price
            try:
                if (not in_position and not halt_trading):
                    #last_row_index = len(candle_data.index) - 1
                    if (current_price <= limit_price and limit_buy == True):
                        #check for wallet balance
                        if(not checkWalletBalance(address, base_coin)):
                            print("Insufficient Buy_Amount in Wallet!")
                        else:
                            txRetryCounter = 0 
                            for txRetryCounter in range(2):
                                try:
                                    buy_coin(address,private_key,InputToken_address,buy_amount)
                                    #update Config with position state
                                    with open("ATS_config.json", "r") as jsonFile:
                                        data = json.load(jsonFile)
                                    data['base_config']['in_position'] = True
                                    with open("ATS_config.json", "w") as jsonFile:
                                        json.dump(data, jsonFile,indent=2)
                                    in_position = True
                                    buy_price = current_price
                                    stop_loss_price = (buy_price) - (buy_price * stop_loss_percent)
                                    take_profit_price = (buy_price * gain_percent)
                                    supertrendFlip = False
                                    macdCross = False
                                    print(f"Timestamp: {datetime.now().isoformat()}", file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                                    print(f"Limit Buy for: {buy_price}", file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                                    print(f"Stop Loss: {stop_loss_price}", file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                                    print(f"Take Profit: {take_profit_price}", file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                                    print(f"Current Bot Profit: {bot_profit}" , file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                                except Exception as exc:
                                    print(traceback.format_exc(), file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                                    print(exc, file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                                    print(f"BUY ERROR BUY_NOW | Try Count: {txRetryCounter}| Timestamp: {datetime.now().isoformat()} | BUY_PRICE: {buy_price}", file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))                        
                                    txRetryCounter += 1
                                    time.sleep(15)
                                    continue
                                break
                            #Send Telegram Message
                            message = (f"Buy Alert - Limit Price! \n\
Timestamp: {datetime.now().isoformat()} \n\
Buy for: {buy_price}\n\
Stop Loss: {stop_loss_price} \n\
Take Profit: {take_profit_price}\n\
Current Bot Profit: {bot_profit}\n\
")
                            sendMessage(message)
            except Exception as exc:
                print("")
#######################################################################################
            #Check Stop Loss And Sell if triggered
            if (current_price <= stop_loss_price):
                if in_position and buy_counter > 0 and not halt_trading:
                    #sellcoin
                    txRetryCounter = 0 
                    for txRetryCounter in range(2):
                        try:
                            sell_coin(address,private_key,InputToken_address)
                            #update Config with position state
                            with open("ATS_config.json", "r") as jsonFile:
                                data = json.load(jsonFile)
                            data['base_config']['in_position'] = False
                            with open("ATS_config.json", "w") as jsonFile:
                                json.dump(data, jsonFile,indent=2)
                            in_position = False
                            supertrendFlip = False
                            macdCross = False
                            approveCounter = 1
                            print(f"Stop Loss Triggered: {current_price} | Timestamp: {datetime.now().isoformat()} ", file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                            bot_profit = (bot_profit + ((current_price - buy_price)*(web3.fromWei(minimumOut,'ether'))) - ((current_price*.01)*(web3.fromWei(minimumOut,'ether'))))
                            trade_rows = [datetime.now().isoformat(),"sell",current_price, "", "",bot_profit]
                            with open(f'{logpath}//trades.csv', 'a', encoding='UTF8', newline='') as f:
                                writer = csv.writer(f)
                                writer.writerow(trade_rows)
                        except Exception as exc:
                            print(traceback.format_exc(), file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                            print(exc, file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                            print(f"SELL ERROR STOP LOSS | Try Count: {txRetryCounter} | Timestamp: {datetime.now().isoformat()} | SELL_PRICE: {current_price}", file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                            time.sleep(15)
                            txRetryCounter += 1
                            continue
                        break
                    #Send Telegram Message
                    message = (f"Sell Alert! \n\
Timestamp: {datetime.now().isoformat()} \n\
Sell Type: STOP LOSS\n\
Sell for: {current_price}\n\
Current Bot Profit: {bot_profit} \n\
")
                    sendMessage(message)

#######################################################################################
            #Check for Take Profit Price and sell if triggered
            if (current_price >= take_profit_price):
                if in_position and not halt_trading:
                    #sellcoin
                    txRetryCounter = 0 
                    for txRetryCounter in range(2):
                        try:
                            sell_coin(address,private_key,InputToken_address)
                            #update Config with position state
                            with open("ATS_config.json", "r") as jsonFile:
                                data = json.load(jsonFile)
                            data['base_config']['in_position'] = False
                            with open("ATS_config.json", "w") as jsonFile:
                                json.dump(data, jsonFile,indent=2)
                            in_position = False
                            macdCross = False
                            supertrendFlip = False
                            approveCounter = 1
                            print(f"Gain Percent Triggered: {current_price} | Timestamp: {datetime.now().isoformat()}" , file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                            bot_profit = (bot_profit + ((current_price - buy_price)*(web3.fromWei(minimumOut,'ether'))) - ((current_price*.01)*(web3.fromWei(minimumOut,'ether'))))
                            trade_rows = [datetime.now().isoformat(),"sell",current_price, "", "",bot_profit]
                            with open(f'{logpath}//trades.csv', 'a', encoding='UTF8', newline='') as f:
                                writer = csv.writer(f)
                                writer.writerow(trade_rows)
                        except Exception as exc:
                            print(traceback.format_exc(), file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                            print(exc, file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                            print(f"SELL ERROR TAKE PROFIT | Try Count: {txRetryCounter} | Timestamp: {datetime.now().isoformat()} | SELL_PRICE: {current_price}", file=open(f'{logpath}{InputToken_address}_5MIN_BSC_output.txt', 'a'))
                            txRetryCounter += 1
                            time.sleep(15)
                            continue
                        break
                    #Send Telegram Message
                    message = (f"Sell Alert! \n\
Timestamp: {datetime.now().isoformat()} \n\
Sell Type: Gain Percent Trigger\n\
Sell for: {current_price}\n\
Current Bot Profit: {bot_profit} \n\
")
                    sendMessage(message)                    
#######################################################################################
            #Create new Data Frame
            now = datetime.now().isoformat()
            sec_df = pd.DataFrame()
            #append pricing data to data frame and output to csv for saving
            sec_df['timestamp'] = pd.to_datetime([now], errors='coerce') 
            sec_df['price'] = pd.to_numeric(current_price)
            sec_df = sec_df.set_index('timestamp')
            sec_price = sec_price.append(sec_df)
            print(f"{current_price} | TimeStamp: {now}")
            sec_df.to_csv(f'{logpath}{InputToken_address}_price_ticker.csv', mode='a', index=True, header=False)
            #GET PRICE INTERVAL IN SECONDS. 1 = 1 Second. 0.5 = 1/2 Second
            time.sleep(.5)
        except Exception as exc:
            print(traceback.format_exc())
            print(exc)
            print(f"GET PRICE ERROR! | Timestamp: {datetime.now().isoformat()}", file=open(f'{logpath}{InputToken_address}_5MIN_BSC_ERROR_output.txt', 'a'))

##################################
##      BUILD CANDLES           ##
##################################
def calculateOHLC_5min() : 
    global sec_price, min5_price
    while True:
        try:
            time.sleep(300)
            min5_price = sec_price['price'].resample('300s').ohlc()
        except:
            print(f"Failed to resample 5Min Price | Timestamp: {datetime.now().isoformat()}", file=open(f'{logpath}{InputToken_address}_5MIN_BSC_ERROR_output.txt', 'a'))
        min5_price.to_csv(f'{logpath}{InputToken_address}_5min_Candle_data.csv', mode='a', index=True, header=False)
        
def calculateOHLC_1min() : 
    global sec_price, min1_price
    time.sleep(120)
    while True:
        try:
            time.sleep(60)
            min1_price = sec_price['price'].resample('60s').ohlc()
            min1_price.to_csv(f'{logpath}{InputToken_address}_1min_Candle_data.csv', mode='a', index=True, header=False)
        except:
            print(f"Failed to resample 1Min Price | Timestamp: {datetime.now().isoformat()}", file=open(f'{logpath}{InputToken_address}_5MIN_BSC_ERROR_output.txt', 'a'))

if __name__ == "__main__":
    date_format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=date_format, level=logging.INFO,
                        datefmt="%H:%M:%S")
    print(threading.active_count())
    print(threading.enumerate())
    #################################################################
    #Logging SETUP 
    #check Log path
    if not os.path.exists(f'{os.getcwd()}//tokenlogs//'):
        print(f'Creating Log Path | {os.getcwd()}//tokenlogs')
        os.mkdir(f'{os.getcwd()}//tokenlogs')
    #check for token path
    if not os.path.exists(f'{os.getcwd()}//tokenlogs//{InputToken_address}'):
        print(f'Creating Token Log Path | {os.getcwd()}//tokenlogs//{InputToken_address}//')
        os.mkdir(f'{os.getcwd()}//tokenlogs//{InputToken_address}//')

    logpath = f'{os.getcwd()}//tokenlogs//{InputToken_address}//'
    #clean up large pricing files
    pricefile = f'{logpath}{InputToken_address}_price_ticker.csv'
    try:
        if os.path.getsize(pricefile) > 500000000:
            os.remove(pricefile)
    except:
        print("Generating Price File...")
    try:
        if os.path.getsize(f'{logpath}{InputToken_address}_1min_Candle_data.csv') > 500000000:
            os.remove(f'{logpath}{InputToken_address}_1min_Candle_data.csv')
    except:
        print("Generating Candle Data...")
    try:
        if os.path.getsize(f'{logpath}{InputToken_address}_5min_Candle_data.csv') > 500000000:
            os.remove(f'{logpath}{InputToken_address}_5min_Candle_data.csv')
    except:
        print("Generating Candle Data...")

    #######################################################################
    #Create CSVs
    if not os.path.exists(f'{logpath}//trades.csv'):
        print(f'Creating Trades CSV | {logpath}//trades.csv')
        header = ['Timestamp','buy/sell', 'current_price', 'stop_loss_price', 'take_profit_price','bot_profit']
        with open(f'{logpath}//trades.csv', 'w', encoding='UTF8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)
    if not os.path.exists(f'{logpath}//{InputToken_address}_price_ticker.csv'):
        print(f'Creating price CSV | {logpath}//{InputToken_address}_price_ticker.csv')
        header = ['timestamp','current_price']
        with open(f'{logpath}//{InputToken_address}_price_ticker.csv', 'w', encoding='UTF8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)
    if not os.path.exists(f'{logpath}{InputToken_address}_5min_Candle_data.csv'):
        print(f'Creating 5MIN OHLC CSV | {logpath}{InputToken_address}_5min_Candle_data.csv')
        header = ['timestamp','open', 'high', 'low', 'close']
        with open(f'{logpath}{InputToken_address}_5min_Candle_data.csv', 'w', encoding='UTF8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)
    if not os.path.exists(f'{logpath}{InputToken_address}_1min_Candle_data.csv'):
        print(f'Creating 1MIN OHLC CSV | {logpath}{InputToken_address}_1min_Candle_data.csv')
        header = ['timestamp','open', 'high', 'low', 'close']
        with open(f'{logpath}{InputToken_address}_1min_Candle_data.csv', 'w', encoding='UTF8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)
    #######################################################################
    #Start Price Data Thread
    getPrice_thread = threading.Thread(target=getPrice,)
    getPrice_thread.daemon = True
    getPrice_thread.start()
    
    #Start calculateOHLC 5MIN Thread
    calculateOHLC_5min_thread = threading.Thread(target=calculateOHLC_5min,)
    calculateOHLC_5min_thread.daemon = True
    calculateOHLC_5min_thread.start()
    
    #Start calculateOHLC 1MIN Thread
    calculateOHLC_1min_thread = threading.Thread(target=calculateOHLC_1min,)
    calculateOHLC_1min_thread.daemon = True
    calculateOHLC_1min_thread.start()
    
    #Wait for Candles to generate otherwise trends will error out without a big enough period.
    # 1200 Seconds for 1min 
    # 5400 Seconds for 5min 
    if(firstWait == True):
        time.sleep(5400)
        firstWait = False
    
    # Run the price checks every X seconds
    # Sync this to the candle stick OHLC time
    schedule.every(330).seconds.do(run_bot)
    while True:
        schedule.run_pending()
        time.sleep(3)

