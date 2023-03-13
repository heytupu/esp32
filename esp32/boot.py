"""Entrypoint"""
from json import load
import machine
import network
# import ugit 

print("\n-------------------- Started Bootloader ESP32 --------------------\n")

try:
    with open("configs/config.json", "r") as json_file:
        CFG = load(json_file)
except Exception as e:
    print("Failed to load config file.")

import ugit
print(dir(ugit))

def enable_garbage_collection() -> None:
    """Enabling the garbage collector."""
    import gc

    gc.collect()
    gc.threshold(gc.mem_free() // 4 + gc.mem_alloc())


def connect_wifi() -> None:
    """Establish wifi connection."""
    sta_if = network.WLAN(network.STA_IF)

    if not sta_if.isconnected():
        print("Connecting to network ...")
        sta_if.active(True)
        sta_if.connect(CFG["Network"]["SSID"], CFG["Network"]["PASS"])
        while not sta_if.isconnected():
            pass

    print("Established connection to network", sta_if.ifconfig())


enable_garbage_collection()
connect_wifi()
print("ugit")
ugit.update()
