#!/usr/bin/python
# vim: set fileencoding=utf-8 :

import log

# ODR => One Day Reversal
class ODRCalculator(object):
    def __init__(self, price_threshhold=.01, volume_threshhold=0.1):
        self.price_threshhold = price_threshhold
        self.volume_threshhold = volume_threshhold
        self.last_tick = None

    def __call__(self, tick):
        result = False
        if not self.last_tick is None:
            if (tick["High"] > self.last_tick["High"] * (1 + self.price_threshhold)
                    and tick["Close"] < self.last_tick["Close"]
                    and tick["Volume"] > self.last_tick["Volume"] * (1 + self.volume_threshhold)
                    and (self.last_tick["Close"] != self.last_tick["High"]
                         and self.last_tick["Close"] != self.last_tick["Low"])):
                log.logger.debug("ODR: %s", tick.name)
                result = True

        self.last_tick = tick.copy()

        return result

if __name__ == "__main__":
    from matplotlib import pyplot as plt
    from numpy import ma

    from common import probe_proxy
    from stock import Stock

    probe_proxy()
    log.init()

    # http://stockcharts.com/help/doku.php?id=chart_school:technical_indicators:average_true_range_a
#    stk = Stock("QQQ")
#    stk.retrieve_history(start="2010/4/1", use_cache=False, no_volume=True)
#    history = stk.history
#    c = ATRCalculator(atr_period=14)
#    history["ATR"] = history.apply(c, axis=1)
#    print history["ATR"].loc["2010-4-21":]

    stk = Stock("300191.SZ") #潜能恒信
    stk = Stock("002594.SZ") #比亚迪
    stk = Stock("600332.SS") #白云山

    #stk.retrieve_history(start="2013/1/1", use_cache=False, no_volume=False)
    stk.retrieve_history(start="2013/1/1", use_cache=True, no_volume=False)
    history = stk.history
    c = ODRCalculator(price_threshhold=0.02)
    history["ODR"] = history.apply(c, axis=1)

    plt.plot(history.index, history["Close"], "g.", alpha=.5)
    plt.plot(history.index, history["Close"], "b-")

    mask = ma.make_mask(history.index)
    mask = ma.masked_where(history["ODR"] == True, mask)
    chosen = ma.masked_where(~mask.mask, history["Close"])

    if chosen.any():
         plt.plot(history.index, chosen, "ro")

    plt.show()
