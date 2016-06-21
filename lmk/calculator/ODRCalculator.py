"""ODRCalculator

ODR => One Day Reversal
"""

class ODRCalculator(object):
    def __init__(self):
        self.last_tick = None

    def __call__(self, tick):
        odr = (self.last_tick is not None
               and tick["High"] > self.last_tick["High"]
               and tick["Close"] < self.last_tick["Low"]
               and tick["Volume"] > self.last_tick["Volume"])

        self.last_tick = tick.copy()

        return odr

