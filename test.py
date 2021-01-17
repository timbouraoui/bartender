import json
import os

file = open("pump_config.json", "r")
pump_list = json.load(file)
file.close()

for key, value in pump_list.items():
    print(key, value)