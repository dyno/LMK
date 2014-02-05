import sys
import logging

logger = None

def init(loglevel=logging.DEBUG):
    logging.basicConfig(level=loglevel, format="%(message)s")
    stdoutStreamHandler = logging.StreamHandler(stream=sys.stdout)

    global logger
    logger = logging.getLogger()
    logger.setLevel(loglevel)
