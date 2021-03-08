"""ATRCalculator

ATR: Average True Range.
http://stockcharts.com/school/doku.php?id=chart_school:technical_indicators:average_true_range_atr
"""


class ATRCalculator(object):
    def __init__(self, window_size=10):
        self.window_size = window_size
        self.tr_list = []
        self.last_tick = None
        self.atr = None

    def __call__(self, tick):
        HL = tick["High"] - tick["Low"]
        # if not self.last_tick:
        # => ValueError: 'The truth value of an array with more than one element is ambiguous. Use a.any() or a.all()'
        if self.last_tick is not None:
            HCp = abs(tick["High"] - self.last_tick["Close"])  # Cp => previous Close
            LCp = abs(tick["Low"] - self.last_tick["Close"])
            tr = max(HL, HCp, LCp)
        else:
            tr = HL

        # assert tr != 0.0, "TR should not be zero!"
        # The above assertion is not True. e.g. extremely low volume like BPHX @ 2014-06-03
        if len(self.tr_list) < self.window_size:
            self.tr_list.append(tr)
            self.atr = sum(self.tr_list) / len(self.tr_list)
        else:
            # self.atr = (self.atr * (window_size - 1) + self.tr) / window_size
            self.atr += (tr - self.atr) / self.window_size

        # assert self.atr != 0.0, "ATR should not be zero! last=%s, tick=%s" % (repr(self.last_tick), repr(tick))
        # The above assert is not True, e.g. RRST @ 2014-01-02
        self.last_tick = tick.copy()

        return self.atr
