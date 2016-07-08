import unittest
from tempfile import TemporaryDirectory

from pandas_datareader.data import DataReader
from pandas import to_datetime
from numpy import dtype

from lmk.utils import env
from lmk.cache import Cache

def date(s):
    return to_datetime(s).date()

class CacheTestCase(unittest.TestCase):
    """Tests for `lmk.cache`."""

    def setUp(self):
        #env.logger.setLevel(logging.WARN)
        self.symbol = "TSLA"
        self._start = "2015-02-01"
        self.start = date(self._start)
        self._end = "2016-02-01"
        self.end = date(self._end)

        self.h = DataReader(self.symbol, "yahoo", self._start, self._end)

    def test_cache(self):
        with TemporaryDirectory(prefix="lmk.") as tmpdir:
            cache = Cache(tmpdir)
            self.assertTrue(list(cache.range.columns) == ["start", "end"])
            self.assertEqual(cache.range.dtypes.loc["start"], dtype('<M8[ns]'))

            # put
            cache.put(self.symbol, self.start, self.end, self.h)
            self.assertEqual(cache.range.dtypes.loc["end"], dtype('<M8[ns]'))

            # get
            # on the left, no overlap
            h = cache.get(self.symbol, date("2015-01-01"), date("2015-01-31"))
            self.assertTrue(h is None)
           # on the right, no overlap
            h = cache.get(self.symbol, date("2016-03-01"), date("2015-03-31"))
            self.assertTrue(h is None)
            # overlap on the left
            h = cache.get(self.symbol, date("2015-01-01"), date("2015-03-31"))
            self.assertTrue(h is None)
            # overlap on the right
            h = cache.get(self.symbol, date("2016-01-01"), date("2016-03-31"))
            self.assertTrue(h is None)
            # hit
            h = cache.get(self.symbol, date("2015-02-01"), date("2016-02-01"))
            self.assertTrue(h is not None)
            # hit
            h = cache.get(self.symbol, date("2015-03-01"), date("2015-05-01"))
            self.assertTrue(h is not None)


if __name__ == '__main__':
    unittest.main()
