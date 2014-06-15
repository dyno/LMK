#!/usr/bin/python
# vim: set fileencoding=utf-8 :

import log
from constants import *

class BuyPointCalculator(object):
    def __init__(self):
        self.wait_for_rise = False
        self.last_support_pivot = 0

    def __call__(self, tick):
        if tick["recorded"] == True and tick["band"] in (BAND_DNWARD, BAND_NAT_REACT):
            self.last_support_pivot = tick["Close"]
            self.wait_for_rise = True

        if self.wait_for_rise:
            if tick["Close"] > self.last_support_pivot + .5 * tick["ATR"]:
                self.wait_for_rise = False
                return True

        return False

if __name__ == "__main__":
    from matplotlib import pyplot as plt
    from numpy import ma
    import pandas

    from common import probe_proxy
    from stock import Stock

    probe_proxy()
    log.init()

    from InitialPivotalPointCalculator import InitialPivotalPointCalculator
    from LMKCalculator import LMKCalculator

    stk = Stock("TSLA")
    stk.retrieve_history(start="2014/1/1", use_cache=True, no_volume=False)
    history = stk.history

    c = InitialPivotalPointCalculator(atr_factor=2.0)
    history.apply(c, axis=1)

    c = LMKCalculator(c)
    lmk = history.apply(c, axis=1)
    history = pandas.merge(history, lmk, left_index=True, right_index=True, sort=False)

    c = BuyPointCalculator()
    history["Buy"] = history.apply(c, axis=1)

    plt.plot(history.index, history["Close"], "g.", alpha=.5)
    plt.plot(history.index, history["Close"], "b-")

    mask = ma.make_mask(history.index)
    mask = ma.masked_where(history["Buy"] == True, mask)
    chosen = ma.masked_where(~mask.mask, history["Close"])

    if chosen.any():
         plt.plot(history.index, chosen, "go")

    plt.show()

