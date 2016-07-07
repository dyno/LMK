import unittest
import logging
from operator import gt, lt

# XXX: workaround matplotlib problem running in pyenv.
import matplotlib
matplotlib.use("Agg")

from lmk.utils import env
from lmk.ticker import Ticker, ensure_columns_exist
from lmk.calculator.PivotCalculator import PivotCalculator
from lmk.calculator.ATRCalculator import ATRCalculator
from lmk.calculator.ODRCalculator import ODRCalculator
from lmk.calculator.EntryPointCalculator import EntryPointCalculator, BUY, SELL
from lmk.calculator.LMKBandCalculator import (LMKBandCalculatorHeuristic,
    TREND_UP, TREND_DN, BAND_UPWARD, BAND_DNWARD)

# XXX: http://stackoverflow.com/questions/4095319/unittest-tests-order

class CalculatorTestCase(unittest.TestCase):
    """Tests for `lmk.calculator.*`."""

    def setUp(self):
        #env.logger.setLevel(logging.WARN)
        self.ticker = Ticker("TSLA")
        self.ticker.retrieve_history("2015-01-01", "2016-05-31")

    def test_history_sanity(self):
        close = "{:.2f}".format(self.ticker.history.ix["2016-05-31"]["Close"])
        self.assertEqual(close, "223.23")

    def test_PivotCalculator(self):
        # history[Close]
        h = self.ticker.history
        if "Top" in h:
            self.assertTrue("Btm" in h)
            return

        window_size = 5
        self.assertTrue(len(h) > window_size)

        c = PivotCalculator(window_size=window_size, cmp=gt)
        h["Close"].apply(c)
        h["Top"] = c.result
        self.assertEqual(len(h["Top"]), len(h))
        self.assertTrue(h.ix["2015-07-20"]["Top"])

        c = PivotCalculator(window_size=window_size, cmp=lt)
        h["Close"].apply(c)
        h["Btm"] = c.result
        self.assertEqual(len(h["Btm"]), len(h))
        self.assertTrue(h.ix["2016-02-10"]["Btm"])

    def test_ATRCalculator(self):
        # history[Open, High, Low, Close]
        h = self.ticker.history

        c = ATRCalculator(window_size=20)
        h["ATR"] = h.apply(c, axis=1)
        h.fillna(method="backfill", axis=0, inplace=True)

        atr = "{:.2f}".format(h.ix["2015-01-02"]["ATR"])
        self.assertEqual(atr, "9.99")

        atr = "{:.2f}".format(h.ix["2016-05-31"]["ATR"])
        self.assertEqual(atr, "7.84")

    def _test_EntryPointCalculator(self):
        # history[Close, Top, Btm, ATR]
        h = self.ticker.history

        c = ATRCalculator(window_size=20)
        h["ATR"] = h.apply(c, axis=1)
        c = EntryPointCalculator(trade_type=BUY)
        h["Buy"] = h.apply(c, axis=1)
        self.assertTrue(h["Buy"]["2016-02-11"])

        c = EntryPointCalculator(trade_type=SELL)
        h["Sell"] = h.apply(c, axis=1)
        self.assertTrue(h["Sell"]["2015-01-05"])

    def test_EntryPointCalculator(self):
        self.test_PivotCalculator()
        self.test_ATRCalculator()
        self._test_EntryPointCalculator()

    def test_ODRCalculator(self):
        # history[Open, High, Low, Close, Volume]
        h = self.ticker.history

        c = ODRCalculator()
        h["ODR"] = h.apply(c, axis=1)
        self.assertEqual(len(h[h["ODR"] == True]), 4)
        self.assertTrue(h["ODR"]["2016-01-08"])

    def test_LMKBandCalculator(self):
        h = self.ticker.history
        ensure_columns_exist(h, ["Top", "Btm"])

        start_pivot = h[h["Top"] | h["Btm"]].ix[0]
        self.assertEqual(start_pivot["Top"], True)

        c = LMKBandCalculatorHeuristic(start_pivot, atr_factor=1.0)
        df = h.apply(c, axis=1)
        h["Trend"], h["WM"], h["Band"] = df["Trend"], df["WM"], df["Band"]
        self.assertEqual(h["Trend"]["2015-01-22"], TREND_DN)
        self.assertEqual("{:.2f}".format(h["WM"]["2015-05-15"]), "248.84")
        self.assertEqual(h["Band"]["2015-05-29"], BAND_UPWARD)

if __name__ == '__main__':
    unittest.main()
