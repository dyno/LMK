import unittest
import logging
from operator import gt, lt

from lmk.utils import env
from lmk.ticker import Ticker
from lmk.calculator.PivotCalculator import PivotCalculator
from lmk.calculator.ATRCalculator import ATRCalculator
from lmk.calculator.ODRCalculator import ODRCalculator
from lmk.calculator.EntryPointCalculator import EntryPointCalculator, BUY, SELL


# XXX: http://stackoverflow.com/questions/4095319/unittest-tests-order

class CalculatorTestCase(unittest.TestCase):
    """Tests for `lmk.datasource.NetEase`."""

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
        if "ATR" in h:
            return

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

    def _test_LMKBandCalculator(self):
        pass


if __name__ == '__main__':
    unittest.main()
