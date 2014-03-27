#!/usr/bin/python

import sys

import pandas
from datetime import date, datetime

import log
from stock import Stock
from common import init_plot, show_plot
from LMKCalculator import LMKCalculator, LMKBacktestCalculator, plot_lmk
from LMKBandCalculator import LMKBandCalculator, LMKBandBacktestCalculator, plot_lmk_band
from InitialPivotalPointCalculator import InitialPivotalPointCalculator

# ------------------------------------------------------------------------------

def lmk_analysis(stk, atr_factor=2, plot=False, fluct_factor=2.0):
    history = stk.history

    c = InitialPivotalPointCalculator(atr_factor=atr_factor)
    history.apply(c, axis=1)

    c = LMKCalculator(c)
    lmk = history.apply(c, axis=1)
    history = pandas.merge(history, lmk, left_index=True, right_index=True, sort=False)
    last = history.ix[-1]
    log.logger.info("%s: close=%.2f, reaction_support=%.2f, rally_resistance=%.2f",
                    last.name.strftime("%Y-%m-%d"), last["Close"], last["reaction_support"], last["rally_resistance"])

    c = LMKBacktestCalculator()
    history.apply(c, axis=1)

    result = c.value_rate()

    if plot:
        plot_lmk(history, fluct_factor=fluct_factor)

    return result

def lmk_band_analysis(stk, atr_factor=2.0, plot_width=0, fluct_factor=1.0):
    history = stk.history

    c = InitialPivotalPointCalculator(atr_factor=atr_factor)
    history.apply(c, axis=1)

    c = LMKBandCalculator(c)
    lmk_band = history.apply(c, axis=1)
    history = pandas.merge(history, lmk_band, left_index=True, right_index=True, sort=False)
    last = history.ix[-1]
    log.logger.info("%s: close=%.2f, support=%.2f, resistance=%.2f, break=%.2f",
                    last.name.strftime("%Y-%m-%d"), last["Close"], last["support"], last["resistance"], (last["support"] + last["resistance"]) / 2.0)

    c = LMKBandBacktestCalculator()
    history.apply(c, axis=1)

    result = c.value_rate()

    if plot_width:
        plot_lmk_band(history, show_band=True, band_width=plot_width, fluct_factor=fluct_factor)

    return result

def main():
    for symbol in ["000001.SS", "300052.SZ", "300223.SZ",
                     "^GSPC", "AAPL", "GOOG", "VMW", "TSLA", "AMZN", "FB", "TWTR",
                     "BIDU", "QIHU", "EDU"]:
        for atr_factor in (1.0, 1.5, 2.0, 2.5, 3.0):
            for freq in ("D", "W-FRI", "W-MON"):
                continue # shortcut - commented
                no_volume = True if symbol in ("000001.SS", "^GSPC") else False
                stk = Stock(symbol)
                stk.retrieve_history(start="2013/1/1", end="2014/1/1", use_cache=False, no_volume=no_volume)
                stk.resample_history(freq=freq)

                result = lmk_analysis(stk, atr_factor=atr_factor)
                print "%s: atr_factor=%.1f, freq=%5s, lmk_result=%.2f" % (symbol, atr_factor, freq, result)
                result = lmk_band_analysis(stk, atr_factor=atr_factor)
                print "%s: atr_factor=%.1f, freq=%5s, lmk_band_result=%.2f" % (symbol, atr_factor, freq, result)


    symbol = "VMW"
    symbol = "TSLA"
    symbol = "300369.SZ"
    symbol = "000001.SS"
    symbol = "600547.SS"
    atr_factor=2.0
    freq="W-FRI" #"D"
    plot_width= 7 #1
    freq="D" #"D"
    plot_width = 1
#    result = lmk_band_analysis(symbol, start="2013/6/1", end=datetime.today(), no_volume=False,
#                               atr_factor=atr_factor, freq=freq, plot_width=plot_width)
#    print "%s: atr_factor=%.1f, freq=%5s, lmk_result=%.2f" % (symbol, atr_factor, freq, result)

    stk = Stock(symbol)
    stk.retrieve_history(start="2013/1/1", end="2014/3/26", use_cache=True, no_volume=False)
    stk.resample_history(freq=freq)

    result = [1,1]
    init_plot(width=19.0, height=3.0, title=symbol)
    result[0] = lmk_analysis(stk, atr_factor=atr_factor/2.0, plot=True, fluct_factor=1.0)
    #show_plot()
    init_plot(width=19.0, height=3.0, title=symbol)
    result[1] = lmk_band_analysis(stk, atr_factor=atr_factor, plot_width=plot_width, fluct_factor=1.0)
    #show_plot()

    print "%s: atr_factor=%.1f, freq=%-5s, [lmk/band]=[%s]" % (
           symbol, atr_factor, freq, "/".join(["%.2f" % r for r in result]))

if __name__ == "__main__":
    import logging
    from common import probe_proxy

    probe_proxy()
    log.init(logging.INFO)
    #log.init(logging.DEBUG)

    main()

# TODO:
# *. biweekly? dynamic frequency?

