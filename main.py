#!/usr/bin/python

import sys

import log
from stock import Stock

# ------------------------------------------------------------------------------
def process_week_day(stock_name):
    stk = Stock(stock_name)
    stk.plot_init()

    stk.retrieve_history(use_cache=False, start="9/1/2013")

    stk.process_atr(atr_period=15)
    stk.process_livermore_market_key()
    stk.process_backtest()
    stk.plot_livermore_trend(line="--", alpha=.2)#, show_band=True, band_width=1)

    stk.resample_history(freq="W-FRI")
    stk.process_atr(atr_period=3)
    stk.process_livermore_market_key()
    stk.process_backtest()
    stk.plot_livermore_trend(line="-", alpha=1, show_band=True, band_width=7)

    stk.plot_show()

def main():
    #process_week_day("AMAP")
    process_week_day("300052.SZ")

if __name__ == "__main__":
    log.init()
    main()

# TODO:
# 1. mark 6 bands
# 2. weekly/daily comparation in one graph
# *. biweekly? dynamic frequency?
# 3. inotebook
# 4. pandas.io.data DataReader("" , "163", start, end)
# 5. refactor ...
# 6. "t.apply(lambda row: Series({"col1":row["Open"], "col2":row["Close"]}), axis=1)"

