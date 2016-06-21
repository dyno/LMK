# vim: set fileencoding=utf-8 :

import unittest
import logging

from lmk.datasource.NetEase import NetEase
from lmk.datasource.Yahoo import Yahoo
from lmk.datasource.Google import Google
from lmk.utils import env


class NetEaseTestCase(unittest.TestCase):
    """Tests for `lmk.datasource.NetEase`."""

    def setUp(self):
        #env.logger.setLevel(logging.WARN)
        self.ds = NetEase()

    def test_retrieve_history(self):
        symbol = "601318.SS" # 中国平安
        h = self.ds.retrieve_history(symbol, "2015-01-01", "2015-12-31")
        self.assertEqual(h.ix["2015-12-31"]["Open"], 35.79)

        symbol = "000002.SZ" # 万科A
        h = self.ds.retrieve_history(symbol, "2015-01-01", "2015-12-31")
        self.assertEqual(h.ix["2015-01-05"]["Open"], 14.39)

    def test_get_symbol_name(self):
        symbol = "000001.SZ" # 平安银行
        name = self.ds.get_symbol_name(symbol)
        self.assertEqual(name, "平安银行")

    def test_get_quote_today(self):
        symbol = "000001.SZ" # 平安银行
        r = self.ds.get_quote_today(symbol)
        self.assertTrue(r is None or "Open" in r)

   # ------------------------------------------------------------------
    def test_get_split_history(self):
        symbol = "000001.SZ" # 平安银行
        l = self.ds.get_split_history(symbol)
        self.assertEqual([e for e in l if e[3] == '2015-04-13'][0],
                         ['0', '2', '1.74', '2015-04-13'])

    def test_adjust_close_price(self):
        symbol = "000001.SZ" # 平安银行

        h = self.ds.retrieve_history(symbol, "2015-01-01", "2015-12-31")
        self.assertEqual(h.ix["2015-12-31"]["Close"], 11.99)

        oh = h.copy() # original history
        sh = self.ds.get_split_history(symbol)
        self.ds.adjust_close_price(h, sh) # inplace
        # price in history has already been adjusted.
        self.assertTrue(all(h.ix["2015-12-31"] == oh.ix["2015-12-31"]))


class YahooTestCase(unittest.TestCase):
    """Tests for `lmk.datasource.Yahoo`."""

    def setUp(self):
        #env.logger.setLevel(logging.WARN)
        self.ds = Yahoo()

    def test_retrieve_history(self):
        h = self.ds.retrieve_history("TSLA", "2015-01-01", "2015-12-31")
        self.assertEqual("{:.2f}".format(h.ix["2015-12-31"]["Close"]), "240.01")

    def test_get_symbol_name(self):
        self.assertEqual(self.ds.get_symbol_name("TSLA"), "TSLA")

    def test_get_quote_today(self):
        r = self.ds.get_quote_today("TSLA")
        self.assertTrue(r is None or "Open" in r)


class GoogleTestCase(unittest.TestCase):
    """Tests for `lmk.datasource.Google`."""

    def setUp(self):
        #env.logger.setLevel(logging.WARN)
        self.ds = Google()

    def test_retrieve_history(self):
        h = self.ds.retrieve_history("TSLA", "2015-01-01", "2015-12-31")
        self.assertEqual("{:.2f}".format(h.ix["2015-12-31"]["Close"]), "240.01")

    def test_get_symbol_name(self):
        self.assertEqual(self.ds.get_symbol_name("TSLA"), "TSLA")

    def test_get_quote_today(self):
        r = self.ds.get_quote_today("TSLA")
        self.assertTrue(r is None or "Open" in r)


if __name__ == '__main__':
    unittest.main()
