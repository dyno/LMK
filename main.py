#!/usr/bin/python

import sys

import log
from stock import Stock

from lmk import LivermoreMarketKeyCalculator as LMKC
import pandas

# ------------------------------------------------------------------------------
def analysis(stock_name, no_volume=False, atr_factor=2):
    stk = Stock(stock_name)
    stk.plot_init()

    stk.retrieve_history(use_cache=False, start="6/1/2013", no_volume=no_volume)
    stk.process_atr(atr_period=14)

    #stk.process_livermore_market_key(atr_factor=atr_factor)
    #stk.process_backtest()
    #stk.plot_livermore_trend(line="--", alpha=.9, show_band=True, band_width=1)

    stk.resample_history(freq="W-FRI")
    stk.process_livermore_market_key(atr_factor=atr_factor)
    stk.process_backtest()
    stk.plot_livermore_trend(line="-", alpha=1, show_band=True, band_width=7)

    stk.plot_show()

def main():
    #analysis("000001.SS", no_volume=True, atr_factor=5)
    #analysis("AMAP")
    #analysis("300052.SZ")
    #analysis("300223.SZ")
    #analysis("TSLA", atr_factor=4)
    #analysis("DQ")
    #analysis("AKAM", atr_factor=3)
    #analysis("YHOO", atr_factor=6)

if __name__ == "__main__":
    log.init()
    main()

# TODO:
# *. biweekly? dynamic frequency?
# *. pandas.io.data DataReader("" , "163", start, end)

