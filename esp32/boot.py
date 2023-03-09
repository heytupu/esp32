"""Entrypoint"""
from json import load
import machine
import network

print("\n-------------------- Started Bootloader ESP32 --------------------\n")
print("JOOOOOOOOO hope it works")

try:
    with open("configs/config.json", "r") as json_file:
        CFG = load(json_file)
except Exception as e:
    print("Failed to load config file.")


def enable_garbage_collection() -> None:
    """Enabling the garbage collector."""
    import gc

    gc.collect()
    gc.threshold(gc.mem_free() // 4 + gc.mem_alloc())


enable_garbage_collection()
