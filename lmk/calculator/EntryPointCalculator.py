"""EntryPointCalculator

Entry/Buy: price > btm + atr/2
Exit/Sell: price < top - atr/2
"""

BUY = 1
SELL = 2


class EntryPointCalculator(object):
    def __init__(self, trade_type=BUY, atr_factor=1.0):
        self.trade_type = trade_type
        self.atr_factor = atr_factor
        self.pivot = None
        self.wait_for_trade = False

    def __call__(self, tick):
        trade = False

        atr = tick["ATR"] * self.atr_factor

        if self.trade_type == BUY:
            if tick["Btm"]:
                self.pivot = tick["Close"]
                self.wait_for_trade = True

            if self.pivot and self.wait_for_trade and tick["Close"] >= self.pivot + atr / 2.0:
                self.wait_for_trade = False
                trade = True

        elif self.trade_type == SELL:
            if tick["Top"]:
                self.pivot = tick["Close"]
                self.wait_for_trade = True

            if self.pivot and self.wait_for_trade and tick["Close"] <= self.pivot - atr / 2.0:
                self.wait_for_trade = False
                trade = True

        return trade
