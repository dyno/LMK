# vim: set fileencoding=utf-8 :

import unittest
import logging

from lmk.utils import env
from lmk.market.China import China
from lmk.market.US import US

class MarketTestCase(unittest.TestCase):
    """Tests for `market`."""

    def setUp(self):
        #env.logger.setLevel(logging.WARN)
        pass

    def test_Market_China(self):
        m = China()

        m.now = "2016-06-17 12:00"
        self.assertTrue(m.open)
        self.assertFalse(m.closed)

        m.now = "2016-06-09 12:00" # 端午节
        self.assertFalse(m.open)
        self.assertTrue(m.closed)

    def test_Market_US(self):
        m = US()

        m.now = "2016-06-17 12:00"
        self.assertTrue(m.open)
        self.assertFalse(m.closed)

        m.now = "2016-05-30 12:00" # Memorial Day
        self.assertFalse(m.open)
        self.assertTrue(m.closed)


if __name__ == '__main__':
    unittest.main()

