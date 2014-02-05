class ATRCalculator(object):
    def __init__(self, atr_period):
        self.atr_period = atr_period
        self.tr_list = []
        self.last_tick = None
        self.atr = None

    def __call__(self, tick):
        # if not self.last_tick:
        # => ValueError: 'The truth value of an array with more than one element is ambiguous. Use a.any() or a.all()'
        if not self.last_tick is None:
            HL = tick["High"] - tick["Low"]
            HCp = abs(tick["High"] - self.last_tick["Close"])
            LCp = abs(tick["Low"] - self.last_tick["Close"])
            tr = max(HL, HCp, LCp)
        else:
            tr = tick["High"] - tick["Low"]

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
    from pandas.io.data import DataReader

    # http://stockcharts.com/help/doku.php?id=chart_school:technical_indicators:average_true_range_a
    history = DataReader("QQQ", "yahoo", start="2010/4/1", end="2010/5/13")
    c = ATRCalculator(atr_period=14)
    history["ATR"] = history.apply(c, axis=1)
    print history["ATR"].loc["2010-4-21":]

