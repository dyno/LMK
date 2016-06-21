import sys
import logging
from datetime import date, datetime
from os.path import join, exists
from os import makedirs

from pytz import timezone

from .config import CACHE_DIR


# http://python-3-patterns-idioms-test.readthedocs.io/en/latest/Singleton.html
class Singleton:
    def __init__(self, klass):
        self.klass = klass
        self.instance = None

    def __call__(self, *args, **kwds):
        if self.instance is None:
            self.instance = self.klass(*args, **kwds)

        return self.instance


@Singleton
class Environment(object):
    def __init__(self):
        self.tz = timezone("America/Los_Angeles")
        self._now = None
        self.__init_log(loglevel=logging.DEBUG)

        if not exists(CACHE_DIR):
            makedirs(CACHE_DIR)

    def __init_log(self, loglevel=logging.DEBUG):
#        logging.basicConfig(level=loglevel,
#            format="%(asctime)s|%(levelname)5s|%(filename)s:%(lineno)s#%(funcName)s()#%(message)s")
#        stdoutStreamHandler = logging.StreamHandler(stream=sys.stdout)

        self.logger = logging.getLogger("lmk")
        self.logger.setLevel(loglevel)

        handler = logging.StreamHandler()
        handler.setLevel(loglevel)
        formatter = logging.Formatter("%(levelname)5s|%(filename)s:%(lineno)s#%(funcName)s()# %(message)s")
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    @property
    def _today(self):
        return date.today().strftime("%Y-%m-%d")

    @property
    def today(self):
        return date.today()

    @property
    def now(self):
        return self._now if self._now else datetime.now(tz=self.tz)

    @now.setter
    def now(self, dt=None):
        self._now = datetime.strptime(dt) if dt else None
        if self._now:
            self._now.replace(tzinfo=self.tz)


## global ##
env = Environment()

