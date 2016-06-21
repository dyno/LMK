from pandas_datareader.data import DataReader

from ..utils import Singleton
from .DataSource import DataSource
from .Yahoo import Yahoo

@Singleton
class Google(DataSource):

    def retrieve_history(self, symbol, _start, _end):
        hist = DataReader(symbol, "google", _start, _end)
        hist["Adj Close"] = hist["Close"]

        return hist

    def get_symbol_name(self, symbol):
        return Yahoo().get_symbol_name(symbol)

    def get_quote_today(self, symbol):
        return Yahoo().get_quote_today(symbol)

