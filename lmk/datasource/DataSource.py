class DataSource(object):
    def get_symbol_name(self, symbol):
        raise NotImplementedError()

    def retrieve_history(self, symbol, _start, _end):
        raise NotImplementedError()

    def get_quote_today(self, symbol):
        raise NotImplementedError()
