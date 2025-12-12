import logging
import sys

def configure_logging():
    fmt = "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format=fmt)
