"""Entrypoint"""
from json import load
import machine
import network
import time
import ugit
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

logger.info("\n\n-------------------- Started Bootloader ESP32 --------------------\n")

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

    logger.info("Connecting to network ...")
    r = 0
    while not sta_if.isconnected():
        try:
            sta_if.active(True)
            sta_if.connect(CFG["Network"]["SSID"], CFG["Network"]["PASS"])
        except:
            if r == 12:
                machine.reset()
            r = r + 1
            time.sleep(1)

    logger.info(f"Established connection to network : {sta_if.ifconfig()}.")
    return sta_if


# Pull out the sluggish.
enable_garbage_collection()
# Establish WIFI connection.
sta_if = connect_wifi()
# Updating the Device via Github.
# ugit.update()
# WebRepl
# import webrepl
# webrepl.start()

