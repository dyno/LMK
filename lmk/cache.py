import os
from os.path import join
from datetime import date

from pandas import HDFStore, DataFrame, Series
from pandas import concat
from numpy import datetime64

from .utils import Singleton, env

TABLE_RANGE = "_cache_range"
TABLE_NAME = "_symbol_name"

@Singleton
class Cache:
    def __init__(self, cache_dir=".cache"):
        os.makedirs(cache_dir, exist_ok=True) # mkdir -p ...
        self.fn = join(cache_dir, "lmk.hd5")
        with HDFStore(self.fn) as cache:
            if TABLE_RANGE in cache:
                self.range = cache.get(TABLE_RANGE)
            else:
                self.range = DataFrame(columns=["start", "end"], dtype="datetime64[ns]")

            if TABLE_NAME in cache:
                self.name = cache.get(TABLE_NAME)
            else:
                self.name = Series([])

    def _table_name(self, symbol):
        # HDF5 table name better to be a valid variable name.
        # e.g. 000001.SS => t000001_SS; TSLA => tTSLA
        return "t{}".format(symbol).replace(".", "_")

    def get(self, symbol, start, end):
        table = self._table_name(symbol)

        if symbol in self.range.index:
            # Timestamp -> date
            r = self.range.loc[symbol]
            _start, _end = r["start"].date(), r["end"].date()
            # cache hit - part of existing data.
            if _start <= start <= end <= _end:
                with HDFStore(self.fn) as cache:
                    h = cache.get(table)
                    h = h.loc[start:end]

                    return h

    def put(self, symbol, start, end, history):
        table = self._table_name(symbol)

        if symbol not in self.range.index:
            self.range.loc[symbol] = Series({"start": start, "end": end}).astype(datetime64)

            with HDFStore(self.fn) as cache:
                cache.put(table, history)
                cache.put(TABLE_RANGE, self.range)

        else:
            _start, _end = [ts.date() for ts in self.range.loc[symbol]]

            # 1. part of existing cache, nothing need to be done.
            if _start <= start <= end <= _end:
                return

            # 2. superset of current cache
            elif (start <= _start <= _end <= end):
                with HDFStore(self.fn) as cache:
                    self.range.loc[symbol] = Series({"start": start, "end": end}).astype(datetime64)

                    cache.put(table, history)
                    cache.put(TABLE_RANGE, self.range)

            # 3. there is overlap
            elif (start < _start < end) or (start < _end < end):
                with HDFStore(self.fn) as cache:
                    h = cache.get(table)
                    h = h.combine_first(history)
                    #h = concat([h, history]).drop_duplicates().sort_index()
                    self.range.loc[symbol] = Series({"start": min(start, _start),
                                                     "end": max(end, _end)}).astype(datetime64)

                    cache.put(table, h)
                    cache.put(TABLE_RANGE, self.range)

            # 4. no overlap, save the recent data.
            else:
                if _end < start: # new data is more recent.
                    self.range.loc[symbol] = Series({"start": start, "end": end}).astype(datetime64)

                    with HDFStore(self.fn) as cache:
                        cache.put(table, history)
                        cache.put(TABLE_RANGE, self.range)

    def flush_name(self):
        with HDFStore(self.fn) as cache:
            cache.put(TABLE_NAME, self.name)

