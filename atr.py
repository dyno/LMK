#--------------------------------------------------------------------------------
# http://stockcharts.com/help/doku.php?id=chart_school:technical_indicators:average_true_range_a
class ATRCalculator(object):
    def __init__(self, atr_period):
        self.atr_period = atr_period
        self.tr_list = []
        self.last_tick = None
        self.atr = None

    def __call__(self, tick):
        # if not self.last_tick: # => ValueError: 'The truth value of an array with more than one element is ambiguous. Use a.any() or a.all()'
        if not self.last_tick is None:
            HL = tick["High"] - tick["Low"]
            HCp = abs(tick["High"] - self.last_tick["Close"])
            LCp = abs(tick["Low"] - self.last_tick["Close"])
            tr = max(HL, HCp, LCp)
        else:
            tr = tick["High"] - tick["Low"]

        self.last_tick = tick

        if len(self.tr_list) < self.atr_period:
            self.tr_list.append(tr)
            self.atr = sum(self.tr_list) / len(self.tr_list)
        else:
            #self.atr = (self.atr * (atr_period - 1) + self.tr) / atr_period
            self.atr += (tr - self.atr) / self.atr_period

        return self.atr

