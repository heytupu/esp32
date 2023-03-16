"""Entrypoint"""
from json import load
import machine
import network
import ugit
import logging

# try:
#     import logging
# except ImportError:
#     print("Import error for logging?")
#     class Logger:
#         DEBUG = 10
#         def isEnabledFor(self, _):
#             return False
#         def debug(self, msg, *args):
#             pass
#         def info(self, msg, *args):
#             pass
#         def getLogger(self, name):
#             return Logger()
#     logging = Logger()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

logger.info("\n-------------------- Started Bootloader ESP32 --------------------\n")

try:
    with open("configs/config.json", "r") as json_file:
        CFG = load(json_file)
except Exception as e:
    logger.error("Failed to load config file.")


def enable_garbage_collection() -> None:
    """Enabling the garbage collector."""
    import gc

    gc.collect()
    gc.threshold(gc.mem_free() // 4 + gc.mem_alloc())


def connect_wifi() -> None:
    """Establish wifi connection."""
    sta_if = network.WLAN(network.STA_IF)

    if not sta_if.isconnected():
        logger.info("Connecting to network ...")
        sta_if.active(True)
        sta_if.connect(CFG["Network"]["SSID"], CFG["Network"]["PASS"])
        while not sta_if.isconnected():
            pass

    logger.info(f"Established connection to network : {sta_if.ifconfig()}.")


enable_garbage_collection()
connect_wifi()
# Updating the Device via Github.
# ugit.update()
