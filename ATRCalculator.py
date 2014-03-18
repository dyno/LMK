import log

class ATRCalculator(object):
    def __init__(self, atr_period, fluct_limit=0.2):
        self.atr_period = atr_period
        self.tr_list = []
        self.last_tick = None
        self.atr = None
        self.fluct_limit = fluct_limit

    def __call__(self, tick):
        # if not self.last_tick:
        # => ValueError: 'The truth value of an array with more than one element is ambiguous. Use a.any() or a.all()'
        HL = tick["High"] - tick["Low"]
        if not self.last_tick is None:
            HCp = abs(tick["High"] - self.last_tick["Close"])
            LCp = abs(tick["Low"] - self.last_tick["Close"])
            tr = max(HL, HCp, LCp)

            # stock devidend
            if self.fluct_limit > 0:
                if tr / self.last_tick["Close"] > self.fluct_limit:
                    log.logger.debug("%s: %.2f(tr) / %.2f(close) = %.2f > self.fluct_limit",
                                     repr(tick), tr, self.last_tick["Close"], tr / self.last_tick["Close"])
                    self.tr_list = []
                    tr = HL
        else:
            tr = HL

        self.last_tick = tick.copy()

        if len(self.tr_list) < self.atr_period:
            if tr != 0.0:
                self.tr_list.append(tr)
                self.atr = sum(self.tr_list) / len(self.tr_list)
        else:
            #self.atr = (self.atr * (atr_period - 1) + self.tr) / atr_period
            self.atr += (tr - self.atr) / self.atr_period

        return self.atr

if __name__ == "__main__":
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

    stk = Stock("300027.SZ")
    stk.retrieve_history(start="2013/1/1", use_cache=False, no_volume=False)
    history = stk.history
    c = ATRCalculator(atr_period=14, fluct_limit=0.2)
    history["ATR"] = history.apply(c, axis=1)
    print history["ATR"]

