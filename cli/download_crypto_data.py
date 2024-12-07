import argparse
import os

import pandas as pd
import yfinance as yf

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Description of your program")
    parser.add_argument("--dir", required=True)
    args = parser.parse_args()

    start = "2015-01-01"
    end = "2024-10-01"

    btc = yf.download(tickers="BTC-USD", start=start, end=end, interval="1d")
    btc = btc["Close"]
    btc["DateUTC"] = btc.index
    btc["DateUTC"] = btc["DateUTC"].dt.tz_localize(None)

    eth = yf.download(tickers="ETH-USD", start=start, end=end, interval="1d")
    eth = eth["Close"]
    eth["DateUTC"] = eth.index
    eth["DateUTC"] = eth["DateUTC"].dt.tz_localize(None)

    date_range = pd.date_range(start=start, end=end, freq="d", inclusive="left")
    date_range = pd.DataFrame({"DateUTC": date_range})

    btc = date_range.merge(btc, how="left", on="DateUTC")
    btc["BTC-USD"] = btc["BTC-USD"].ffill()

    eth = date_range.merge(eth, how="left", on="DateUTC")
    eth["ETH-USD"] = eth["ETH-USD"].ffill()

    btc.dropna().to_csv(os.path.join(args.dir, "btc_15_24.csv"), index=False)
    eth.dropna().to_csv(os.path.join(args.dir, "eth_15_24.csv"), index=False)
