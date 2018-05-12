from threading import Thread, Lock
import logging
import webview
from time import sleep
from server import run_server

try:
    from http.client import HTTPConnection
except ImportError:
    # Use httplib on Python 2
    from httplib import HTTPConnection

server_lock = Lock()

logger = logging.getLogger(__name__)


def url_ok(url, port):
    try:
        conn = HTTPConnection(url, port)
        conn.request("GET", "/check_if_app_is_running")
        r = conn.getresponse()
        return r.status == 200
    except:
        logger.exception("Server not started")
        return False

if __name__ == '__main__':
    logger.debug("Starting server")
    t = Thread(target=run_server)
    t.daemon = True
    t.start()
    logger.debug("Checking server")

    while url_ok("127.0.0.1", 5100) is False:
        sleep(1)

    logger.debug("Server started")
    webview.create_window("Student Record System",
                          "http://127.0.0.1:5100",
                          min_size=(1200, 700),
                          text_select=True)
