import unittest
from tempfile import TemporaryDirectory

from pandas_datareader.data import DataReader
from pandas import to_datetime
from numpy import dtype

from lmk.utils import env
from lmk.cache import Cache


def date(s):
    return to_datetime(s).date()


DS = "google"


class CacheTestCase(unittest.TestCase):
    """Tests for `lmk.cache`."""

    def setUp(self):
        # env.logger.setLevel(logging.WARN)
        self.symbol = "TSLA"
        self.start = "2015-04-01"
        self.end = "2015-06-30"

        self.h = DataReader(self.symbol, DS, self.start, self.end)

    def test_cache(self):
        with TemporaryDirectory(prefix="lmk.") as tmpdir:
            cache = Cache(tmpdir)
            self.assertTrue(list(cache.range.columns) == ["start", "end"])
            self.assertEqual(cache.range.dtypes.loc["start"], dtype("<M8[ns]"))

            def cache_range():
                r = cache.range.loc[self.symbol]
                return r["start"].date(), r["end"].date()

            # initial put
            cache.put(self.symbol, date(self.start), date(self.end), self.h)
            self.assertEqual(cache.range.dtypes.loc["end"], dtype("<M8[ns]"))
            self.assertEqual(cache_range(), (date(self.start), date(self.end)))

            # no data cached for the symbol.
            start, end = "2015-01-01", "2015-01-31"
            h = cache.get("NONEXIST", date(start), date(end))
            self.assertTrue(h is None)

            # on the left, no overlap
            start, end = "2015-01-01", "2015-01-31"
            h = cache.get(self.symbol, date(start), date(end))
            self.assertTrue(h is None)
            self.assertEqual(cache_range(), (date(self.start), date(self.end)))

            h1 = DataReader(self.symbol, DS, start, end)
            cache.put(self.symbol, date(start), date(end), h1)
            self.assertEqual(cache_range(), (date(self.start), date(self.end)))

            h = cache.get(self.symbol, date(start), date(end))
            self.assertTrue(h is None)  # only the most recent range is saved.

            # on the right, no overlap
            start, end = "2016-01-01", "2016-05-31"
            h = cache.get(self.symbol, date(start), date(end))
            self.assertTrue(h is None)
            h1 = DataReader(self.symbol, DS, start, end)
            cache.put(self.symbol, date(start), date(end), h1)
            self.assertEqual(cache_range(), (date(start), date(end)))
            h = cache.get(self.symbol, date(start), date(end))
            self.assertTrue(h is not None)  # only the most recent range is saved.

            # overlap on the left
            start, end = "2015-12-01", "2016-03-31"
            h = cache.get(self.symbol, date(start), date(end))
            self.assertTrue(h is None)
            h1 = DataReader(self.symbol, DS, start, end)
            cache.put(self.symbol, date(start), date(end), h1)
            self.assertEqual(cache_range(), (date(start), date("2016-05-31")))
            h = cache.get(self.symbol, date(start), date(end))
            self.assertTrue(h is not None)  # cache extended

            # overlap on the right
            start, end = "2016-04-01", "2016-06-30"
            h = cache.get(self.symbol, date(start), date(end))
            self.assertTrue(h is None)
            h1 = DataReader(self.symbol, DS, start, end)
            cache.put(self.symbol, date(start), date(end), h1)
            self.assertEqual(cache_range(), (date("2015-12-01"), date("2016-06-30")))
            h = cache.get(self.symbol, date(start), date(end))
            self.assertTrue(h is not None)  # cache extended

            # hit - part
            start, end = "2016-01-01", "2016-05-31"
            h = cache.get(self.symbol, date(start), date(end))
            self.assertTrue(h is not None)

            # hit - full
            start, end = "2015-12-01", "2016-06-30"
            h = cache.get(self.symbol, date(start), date(end))
            self.assertTrue(h is not None)


if __name__ == "__main__":
    unittest.main()
