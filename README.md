# Sprinkle DeFi Limit Trading + Dashboard
Sprinkle was designed to be run on BSC against Pancakeswap, mainly due to free+reliable RPC calls and cheap gas on BSC. 

Sprinkle can be used for any EVM compatible chain as well, just replace the RPC,ABI,and web3 functions with whatever dex you want to use.

This system is designed to automatically trade based on a defined strategy or just do limit orders, I have found that it works best when you have a solid long term strategy setup.

Sprinkle can trigger on DIY indicators due candle generation during run. If longer term data is needed, yfinance works quite well as a general aggregate of pricing for top 100 instruments. 

# Why Build Sprinkle?
I wanted to trade limit order outside of CEX and also not pay the fees to execute limit orders on Defi platforms. Running a cheap server was much cheaper than the extra limit order fees.

Also, to learn about python, web3, and finance frameworks. This code probably isn't structured "the best", but it works for what I need.
If someone is so inclined to restructure it, full send gator.    

# Hardware Requirements    
You can run this on a potato. It is designed for TA strategy not for MEV. It can be used for sub minute scraping, but I'm not smart enough to make money with that. 

My recommendation would be to rent a Hetzner cloud server for $8 a month and just run it 24/7. 

# Software Requirements
* Python 3.9+ 
* If on Windows, will need visual studio tool 2017+ for the package requirements
* BSC Wallet address + pvkey  
* Telegram if you want to post updates to a channel. (Recommended to get alerts on your phone for buys/sells)

# How to Run? 
1. Install requirements

    ```pip install schedule requests pandas pandas_ta numpy web3 yfinance streamlit```

2. Add your details to the config file. 
3. Run the python script
* First run will wait 5400 seconds to first buy check (unless Limit price is hit). This is to build pricing dataframe up before running indicators.Run it straight to console first to make sure it's pulling data correctly. Then you can use the following on Linux to run in background.  

```nohup python3 -u BlockChainPull_5min.py -d15 -w512 & > logme.txt```

4. If you want to run the dashboard (it's not complete yet.) run the following command.
    streamlit run dashboard.py


# Notable Items
* The decision to use BUSD instead of BNB is so that you are always using a stable base when calculating price. I would highly recommend using some stable coin to move back and forth.
* When updating the config file for a manual Buy/Sell. It will not reset the value in the config file (haven't dug into why yet). Make sure you set them back to false after the tx goes through. 
* You can edit the config file live while the script is running to do whatever you want. halt trading might be your best friend ;) 
* Sprinkle runs 4 threads:
1. Main Runner thread (where indicators are calculated and analyzed)
2. Second Price Thread, gets the price every second and builds out Dataframe for analysis
3. 1min price thread, calculated OHLC values every 1 min in a dataframe
4. 5min price thread, calculated OHLC values every 5 min in a dataframe
* Current strats utilize the 5 Minute thread mainly, but 1 minute can be useful for early trend confirmations. 
* Before starting to trade check your token route, some have direct routes from BUSD, but a lot will route to BNB first. Checking this will save you a headache. 
