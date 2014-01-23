import sys
import logging

logger = None

def init():
    logging.basicConfig(level=logging.DEBUG, format="%(message)s")
    stdoutStreamHandler = logging.StreamHandler(stream=sys.stdout)

    global logger
    logger = logging.getLogger()
