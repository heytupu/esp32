#!/usr/bin/python3 
import machine 

print(str(int.from_bytes(machine.unique_id(), "little")))
