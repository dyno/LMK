import csv
from urllib.error import HTTPError
from io import StringIO
from datetime import date

import requests
import numpy
from numpy import nan
from pandas import to_datetime
from pandas_datareader.data import DataReader

from ..utils import Singleton
from ..utils import env
from .DataSource import DataSource

@Singleton
class Yahoo(DataSource):
    def get_symbol_name(self, symbol):
        return symbol

    def retrieve_history(self, symbol, _start, _end):
        hist = DataReader(symbol, "yahoo", _start, _end)

        return hist

    # http://www.gummy-stuff.org/Yahoo-data.htm
    QUOTE_TODAY_URL = "http://download.finance.yahoo.com/d/quotes.csv?s=%s&f=sd1ohgl1vl1c"
    def get_quote_today(self, symbol):
        url = self.QUOTE_TODAY_URL % symbol
        env.logger.debug("url = '%s'", url)
        try:
            response = requests.get(url)
            reader = csv.reader(StringIO(response.text), delimiter=",", quotechar='"')
            for row in reader:
                if row[0] == symbol and row[1] != "N/A":
                    env.logger.info("%s => price: %s, updown: %s",
                                    row[0], row[5], row[8].replace(" - ", ", "))
                    rs = {
                        "Open"      : float(row[2]) if row[2] != "N/A" else nan,
                        "High"      : float(row[3]) if row[3] != "N/A" else nan,
                        "Low"       : float(row[4]) if row[4] != "N/A" else nan,
                        "Close"     : float(row[5]) if row[5] != "N/A" else nan,
                        "Volume"    : int(row[6]) if row[6] != "N/A" and int(row[6]) > 0 else 1, # index has no volume...
                        "Adj Close" : float(row[5]) if row[5] != "N/A" else nan,
                    }

                    dt, today = to_datetime(row[1]).date(), date.today()
                    if dt != today:
                        env.logger.warning("{} is NOT today {}.".format(dt, today))
                        return

                    if nan in rs.values():
                        env.logger.debug("rs has nan! => {}", rs)
                        # 2014-07-21, WUBA
                        if numpy.isnan(rs["Open"]): rs["Open"] = rs["Low"]

                    return rs
        except HTTPError as e:
            env.logger.debug("open '{}' result error.\n{}", url, e)


