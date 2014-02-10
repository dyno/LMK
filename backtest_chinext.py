#!/usr/bin/env python

import sys
import logging
from datetime import date
from os.path import exists, join

import pandas
from LMKCalculator import LMKCalculator, LMKBacktestCalculator, plot_lmk
from LMKBandCalculator import LMKBandCalculator, LMKBandBacktestCalculator, plot_lmk_band
from InitialPivotalPointCalculator import InitialPivotalPointCalculator
from ATRCalculator import ATRCalculator

import chinext
from stock import Stock
from common import init_plot, show_plot

db = chinext.get_chinext_db()

def try_wrapper(f):
    def wrapper(*argv, **kargs):
        try:
            f(*argv, **kargs)
        except Exception, e:
            print e
    return wrapper

#@try_wrapper
def process_stock(symbol):
    atr_factor = 2.0
    symbol_ex = "%s.SZ" % symbol

    print "processing", symbol_ex

    stk = Stock(symbol_ex)
    start = db[symbol][2]
    end = date.today()
    stk.retrieve_history(start=start, end=end, use_cache=True, no_volume=False)

    history = stk.history

    c = ATRCalculator(atr_period=20)
    history["ATR"] = history.apply(c, axis=1)
    history.fillna(method="backfill", axis=0, inplace=True)

    #stk.resample_history(freq=freq)
    #history = stk.history

    # LMKBand
    c = InitialPivotalPointCalculator(atr_factor=atr_factor)
    history.apply(c, axis=1)

    c = LMKBandCalculator(c)
    lmk_band = history.apply(c, axis=1)
    history = pandas.merge(history, lmk_band, left_index=True, right_index=True, sort=False)

    c = LMKBandBacktestCalculator()
    history.apply(c, axis=1)

    result = c.value_rate()

    init_plot()
    plot_lmk_band(history, show_band=True, band_width=1)

    name = db[symbol][1]
    filename=join("chinext/cache", "%s_%s.png" % (symbol, name))
    show_plot(filename)

    open(join("chinext/result", "%02.2f_%s.%s.txt" % (result, symbol, name)), "w").close()



def process_stock_wrapper(symbol):
    done = join("chinext/done", "%s.done" % symbol)
    error = join("chinext/done", "%s.error" % symbol)
    if exists(done) or exists(error): return

    try:
        process_stock(symbol)
        open(done, "w").close()
    except Exception, e:
        print e
        open(error, "w").close()


if __name__ == "__main__":
    import os
    from multiprocessing import Pool

    from common import probe_proxy
    import log
    log.init()
    probe_proxy()

    #symbol = "300357"
    #process_stock_wrapper(symbol)
    #sys.exit(0)

    max_process=4
    pool = Pool(processes=max_process)
    pool.map(process_stock_wrapper, db.keys())


